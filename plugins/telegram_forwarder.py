import asyncio
import json
import logging
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from bot_config import CONFIG_PATH, load_config, resolve_path

try:
    from telethon import TelegramClient, events
except ModuleNotFoundError:
    TelegramClient = None
    events = None


_task = None
_telegram_client = None
_messenger_client = None
_admin_ids = []
_last_status = "stopped"
_last_error = None


def telegram_config():
    return load_config().get("telegram", {})


def session_file():
    return str(resolve_path(telegram_config().get("session_file", "telegram_session")))


def session_paths():
    base = Path(session_file())
    paths = [base]
    if base.suffix != ".session":
        paths.append(Path(f"{base}.session"))
    return paths


def has_session_file():
    return any(path.exists() for path in session_paths())


def thread_id():
    return str(telegram_config().get("messenger_target_thread_id", ""))


def normalize_target(raw_target):
    target = str(raw_target).strip()
    if not target:
        raise ValueError("messenger thread id is empty")
    return target


def media_dir():
    return resolve_path(telegram_config().get("media_dir", "runtime/telegram_media"))


def log_path():
    path = resolve_path(
        load_config().get("paths", {}).get("forwarder_log", "runtime/forwarder_debug.log")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def normalize_source(raw_source):
    source = str(raw_source).strip()
    if not source:
        raise ValueError("source id/username is empty")
    if source.lstrip("-").isdigit():
        return int(source)
    return source


def source_key(source):
    return str(normalize_source(source)).lower()


def load_routes():
    try:
        telegram = telegram_config()
        routes = []
        seen = set()

        for route in telegram.get("routes", []):
            source = normalize_source(route.get("source"))
            target = normalize_target(route.get("target_thread_id"))
            enabled = bool(route.get("enabled", True))
            key = source_key(source)
            if key in seen:
                continue
            routes.append({
                "source": source,
                "target_thread_id": target,
                "enabled": enabled,
            })
            seen.add(key)

        default_target = thread_id()
        for source in telegram.get("sources", []):
            source = normalize_source(source)
            key = source_key(source)
            if key not in seen and default_target:
                routes.append({
                    "source": source,
                    "target_thread_id": default_target,
                    "enabled": True,
                })
                seen.add(key)

        return routes
    except Exception as exc:
        log_file(f"ROUTE CONFIG ERROR: {exc}")
        return []


def save_routes(routes):
    clean_routes = []
    seen = set()
    for route in routes:
        source = normalize_source(route.get("source"))
        target = normalize_target(route.get("target_thread_id"))
        enabled = bool(route.get("enabled", True))
        key = source_key(source)
        if key in seen:
            continue
        clean_routes.append({
            "source": source,
            "target_thread_id": target,
            "enabled": enabled,
        })
        seen.add(key)

    config = load_config()
    telegram = config.setdefault("telegram", {})
    telegram["routes"] = clean_routes
    telegram["sources"] = [route["source"] for route in clean_routes]
    CONFIG_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )


def get_sources():
    return [route["source"] for route in load_routes() if route.get("enabled", True)]


def source_label():
    return ", ".join(str(chat) for chat in get_sources()) or "not set"


def route_label():
    routes = load_routes()
    if not routes:
        return "not set"
    return "\n".join(
        f"  • {'ON' if route.get('enabled', True) else 'OFF'} | "
        f"{route['source']} -> {route['target_thread_id']}"
        for route in routes
    )


def add_source(raw_source, raw_target=None):
    source = normalize_source(raw_source)
    target = normalize_target(raw_target or thread_id())
    routes = load_routes()
    key = source_key(source)

    for route in routes:
        if source_key(route["source"]) == key:
            changed = route["target_thread_id"] != target or not route.get("enabled", True)
            route["source"] = source
            route["target_thread_id"] = target
            route["enabled"] = True
            save_routes(routes)
            return source, target, changed, "updated" if changed else "already exists"

    routes.append({"source": source, "target_thread_id": target, "enabled": True})
    save_routes(routes)
    return source, target, True, "added"


def remove_source(raw_source):
    source = normalize_source(raw_source)
    routes = load_routes()
    updated = [
        route for route in routes
        if source_key(route["source"]) != source_key(source)
    ]
    if len(updated) == len(routes):
        return source, False
    save_routes(updated)
    return source, True


def set_source_enabled(raw_source, enabled: bool):
    source = normalize_source(raw_source)
    routes = load_routes()
    key = source_key(source)

    for route in routes:
        if source_key(route["source"]) == key:
            changed = route.get("enabled", True) != enabled
            route["enabled"] = enabled
            save_routes(routes)
            return source, route["target_thread_id"], changed

    return source, None, False


def event_route_target(event, chat=None):
    keys = {source_key(event.chat_id)}
    if chat is not None:
        for value in (
            getattr(chat, "id", None),
            getattr(chat, "username", None),
            getattr(chat, "title", None),
        ):
            if value:
                keys.add(source_key(value))

    for route in load_routes():
        if not route.get("enabled", True):
            continue
        if source_key(route["source"]) in keys:
            return route["target_thread_id"]

    return thread_id()


def log_file(message: str):
    with open(log_path(), "a", encoding="utf-8") as f:
        f.write(message + "\n")


def format_sender_name(sender):
    first = getattr(sender, "first_name", None)
    last = getattr(sender, "last_name", None)
    title = getattr(sender, "title", None)
    username = getattr(sender, "username", None)

    name = " ".join(part for part in (first, last) if part)
    return title or name or username or "Telegram"


async def notify_admins(messenger_client, admin_ids, text: str):
    for admin_id in admin_ids or []:
        try:
            await messenger_client.send_message(text, str(admin_id))
        except Exception as exc:
            logging.warning("Failed to notify admin %s: %s", admin_id, exc)
            log_file(f"ADMIN NOTIFY ERROR ({admin_id}): {exc}")


async def send_to_messenger(messenger_client, target_thread_id: str, text: str, media_paths=None):
    media_paths = [str(path) for path in (media_paths or []) if path]
    if text:
        await messenger_client.send_message(text, target_thread_id)
    if media_paths:
        await messenger_client.send_files_from_path(target_thread_id, media_paths)


async def cleanup_files(paths):
    for path in paths:
        try:
            os.remove(path)
        except OSError:
            pass


async def run_telegram_login_helper(messenger_client, admin_ids, reason: str):
    """Run the interactive Telegram login script in the server console."""
    global _last_status, _last_error

    login_script = BASE_DIR / "plugins" / "telegram.py"
    if not login_script.exists():
        msg = f"Telegram login script not found: {login_script}"
        _last_status = "error"
        _last_error = msg
        await notify_admins(messenger_client, admin_ids, f"❌ {msg}")
        return False

    _last_status = "login_required"
    _last_error = reason
    await notify_admins(
        messenger_client,
        admin_ids,
        "🔐 Telegram login is required.\n"
        f"Reason: {reason}\n"
        "I started plugins/telegram.py in the server console.\n"
        "Enter the Telegram OTP/2FA there, then I will retry forwarding automatically.",
    )
    log_file(f"Starting Telegram login helper: {reason}")

    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(login_script),
        cwd=str(BASE_DIR),
    )
    code = await process.wait()

    if code != 0:
        msg = f"Telegram login helper exited with code {code}."
        _last_status = "error"
        _last_error = msg
        log_file(msg)
        await notify_admins(messenger_client, admin_ids, f"❌ {msg}")
        return False

    log_file("Telegram login helper finished successfully.")
    await notify_admins(
        messenger_client,
        admin_ids,
        "✅ Telegram login finished. Retrying Telegram forwarder now...",
    )
    return True


async def forward_telegram_messages(messenger_client, admin_ids=None):
    global _telegram_client, _last_status, _last_error

    _last_status = "starting"
    _last_error = None

    await notify_admins(
        messenger_client,
        admin_ids,
        "✅ Messenger listener is alive.\n🔄 Telegram forwarder is starting...",
    )

    if TelegramClient is None or events is None:
        msg = "Telegram forwarder disabled: install telethon first."
        logging.error(msg)
        log_file(msg)
        _last_status = "error"
        _last_error = msg
        await notify_admins(messenger_client, admin_ids, f"❌ {msg}")
        return

    for attempt in range(2):
        tg = telegram_config()
        _telegram_client = TelegramClient(
            session_file(),
            int(tg.get("api_id")),
            str(tg.get("api_hash")),
        )
        try:
            await _telegram_client.connect()

            if not await _telegram_client.is_user_authorized():
                reason = (
                    "Telegram session file was not found."
                    if not has_session_file()
                    else "Telegram session is not authorized."
                )
                logging.error(reason)
                log_file(reason)
                await _telegram_client.disconnect()
                if attempt == 0 and await run_telegram_login_helper(
                    messenger_client,
                    admin_ids,
                    reason,
                ):
                    continue
                _last_status = "error"
                _last_error = reason
                await notify_admins(messenger_client, admin_ids, f"❌ {reason}")
                return

            me = await _telegram_client.get_me()
            break
        except Exception as exc:
            msg = f"Telegram login failed: {type(exc).__name__}: {exc}"
            logging.exception("Telegram forwarder login failed")
            log_file(msg)
            if _telegram_client and _telegram_client.is_connected():
                await _telegram_client.disconnect()
            if attempt == 0 and await run_telegram_login_helper(
                messenger_client,
                admin_ids,
                msg,
            ):
                continue
            _last_status = "error"
            _last_error = msg
            await notify_admins(messenger_client, admin_ids, f"❌ {msg}")
            return

    telegram_name = format_sender_name(me)
    logging.info("Telegram forwarder logged in as %s", telegram_name)
    log_file(f"Telegram forwarder logged in as {telegram_name}")

    routes = load_routes()
    routes = [route for route in routes if route.get("enabled", True)]
    sources = [route["source"] for route in routes]
    if not sources:
        msg = (
            f"✅ Telegram logged in as {telegram_name}.\n"
            "✅ Telegram forwarder code is working.\n"
            "⚠️ Forwarding is paused: add or enable a route with /tgadd or /tgon."
        )
        logging.warning("Telegram forwarder paused: no enabled Telegram sources set.")
        log_file("Telegram forwarder paused: enabled route list is empty.")
        _last_status = "paused"
        await notify_admins(messenger_client, admin_ids, msg)
        await _telegram_client.disconnect()
        return

    media_dir().mkdir(parents=True, exist_ok=True)
    _last_status = "running"
    await notify_admins(
        messenger_client,
        admin_ids,
        f"✅ Telegram logged in as {telegram_name}.\n"
        f"✅ Telegram forwarder is active.\n"
        f"📡 Routes:\n{route_label()}",
    )

    @_telegram_client.on(events.NewMessage(chats=sources, incoming=True))
    async def on_telegram_message(event):
        text = event.raw_text
        media_paths = []
        if not text and not event.message.media:
            return

        sender = await event.get_sender()
        chat = await event.get_chat()
        target_thread_id = event_route_target(event, chat)
        sender_name = format_sender_name(sender)
        chat_name = format_sender_name(chat)
        forwarded = f"Telegram | {chat_name} | {sender_name}"
        if text:
            forwarded += f"\n{text}"

        try:
            if event.message.media:
                downloaded = await event.download_media(file=str(media_dir()))
                if downloaded:
                    media_paths.append(downloaded)

            await send_to_messenger(messenger_client, target_thread_id, forwarded, media_paths)
            log_file(
                f"FORWARDED to {target_thread_id}: {chat_name} | {sender_name}: "
                f"{(text or '[media]')[:120]}"
            )
        except Exception as exc:
            logging.exception("Telegram forward failed")
            log_file(f"FORWARD ERROR: {exc}")
        finally:
            await cleanup_files(media_paths)

    try:
        await _telegram_client.run_until_disconnected()
    except asyncio.CancelledError:
        _last_status = "stopped"
        raise
    except Exception as exc:
        _last_status = "error"
        _last_error = str(exc)
        logging.exception("Telegram forwarder stopped with error")
        log_file(f"FORWARDER ERROR: {exc}")
    finally:
        if _telegram_client and _telegram_client.is_connected():
            await _telegram_client.disconnect()
        if _last_status == "running":
            _last_status = "stopped"


def configure(messenger_client, admin_ids=None):
    """Remember Messenger context without starting Telegram forwarding."""
    global _messenger_client, _admin_ids

    _messenger_client = messenger_client
    _admin_ids = list(admin_ids or [])


def start(messenger_client, admin_ids=None):
    """Start Telegram -> Messenger forwarding without blocking the bot."""
    global _task

    configure(messenger_client, admin_ids)

    if _task and not _task.done():
        return _task

    loop = asyncio.get_running_loop()
    _task = loop.create_task(forward_telegram_messages(messenger_client, admin_ids))
    return _task


async def stop():
    global _task, _last_status

    if _task is None or _task.done():
        _last_status = "stopped"
        return False

    _task.cancel()
    try:
        await _task
    except asyncio.CancelledError:
        pass

    _last_status = "stopped"
    return True


async def restart():
    await stop()
    if _messenger_client is None:
        return False
    start(_messenger_client, _admin_ids)
    return True


def is_running():
    return _task is not None and not _task.done()


def status_text():
    task_state = "not created"
    if _task is not None:
        task_state = "running" if not _task.done() else "done"

    lines = [
        "📡 Telegram Forwarder Status",
        f"State: {_last_status}",
        f"Task: {task_state}",
        f"Default messenger target: {thread_id() or 'not set'}",
        f"Routes:\n{route_label()}",
    ]
    if _last_error:
        lines.append(f"Last error: {_last_error}")
    return "\n".join(lines)
