import re
import json
import asyncio
import importlib.util
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from bot_config import load_config, resolve_path

from fbchat_muqit import (
    Client,
    Message,
    EventType,
    FriendRequestState,
    ThreadType,
)

# ─────────────────────────────
# CONFIG
# ─────────────────────────────

BASE_DIR = Path(__file__).parent
CONFIG = load_config()
ADMIN_IDS = {str(admin["id"]) for admin in CONFIG.get("admins", [])}
BOT_CONFIG = CONFIG.get("bot", {})
BANGLADESH_TZ = timezone(timedelta(hours=BOT_CONFIG.get("timezone_hours", 6)))

# ─────────────────────────────
# CLIENT
# ─────────────────────────────

client = Client(
    cookies_file_path=str(resolve_path(CONFIG.get("facebook", {}).get("cookies_file", "cookies.json")))
)
pending_requests = []
cookie_refresh_task = None

# ─────────────────────────────
# HELPERS
# ─────────────────────────────

def is_admin(user_id) -> bool:
    return str(user_id) in ADMIN_IDS


def load_module(name: str, path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Module not found: {path}")

    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def save_current_cookies(reason: str = "periodic"):
    """Persist refreshed cookies from the active logged-in session."""
    try:
        if not getattr(client, "_state", None):
            return

        snapshot = client._state.dump_session_snapshot()
        cookies = snapshot.get("cookies") or []
        if not cookies:
            client.logger.warning("Cookie save skipped: no cookies in active session.")
            return

        cookies_path = resolve_path(CONFIG.get("facebook", {}).get("cookies_file", "cookies.json"))
        tmp_path = cookies_path.with_suffix(cookies_path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(cookies, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, cookies_path)
        client.logger.info("Saved refreshed cookies to %s (%s)", cookies_path, reason)
    except Exception as exc:
        client.logger.warning("Cookie save failed: %s", exc)


async def cookie_refresh_loop():
    interval = int(CONFIG.get("facebook", {}).get("cookie_refresh_interval_seconds", 10800))
    while True:
        await asyncio.sleep(interval)
        await save_current_cookies()


# ─────────────────────────────
# LOAD MODULES
# ─────────────────────────────

try:
    ai_mod = load_module("ai", BASE_DIR / "commands" / "roleplay" / "ai.py")
    help_mod = load_module("help", BASE_DIR / "commands" / "help.py")
    join_mod = load_module("join", BASE_DIR / "plugins" / "join.py")
    welcome_mod = load_module("welcome", BASE_DIR / "plugins" / "welcome.py")
    telegram_forwarder_mod = load_module(
        "telegram_forwarder",
        BASE_DIR / "plugins" / "telegram_forwarder.py",
    )

    admin_dir = BASE_DIR / "commands" / "admin"
    notify_mod = load_module("notify", admin_dir / "notified.py")
    maintain_mod = load_module("maintain", admin_dir / "maintain.py")
    delete_mod = load_module("delete", admin_dir / "delete.py")
    remove_mod = load_module("remove", admin_dir / "remove.py")
    info_mod = load_module("info", admin_dir / "info.py")
    out_mod = load_module("out", admin_dir / "out.py")
    stop_mod = load_module("stop", admin_dir / "stop.py")

    group_dir = BASE_DIR / "commands" / "group_control"
    group_storage_mod = load_module("group_storage", group_dir / "storage.py")
    ban_mod = load_module("group_ban", group_dir / "ban.py")
    unban_mod = load_module("group_unban", group_dir / "unban.py")
    settings_mod = load_module("group_settings", group_dir / "settings.py")

    anime_mod = load_module("anime", BASE_DIR / "commands" / "anime.py")

except Exception as e:
    print(f"MODULE LOAD ERROR: {e}")
    raise


# ─────────────────────────────
# HANDLERS
# ─────────────────────────────

handle_anu = ai_mod.handle_anu
handle_help = help_mod.handle_help
handle_participant_joined = join_mod.handle_participant_joined
handle_new_participant = welcome_mod.handle_new_participant
configure_telegram_forwarder = telegram_forwarder_mod.configure
start_telegram_forwarder = telegram_forwarder_mod.start
stop_telegram_forwarder = telegram_forwarder_mod.stop
restart_telegram_forwarder = telegram_forwarder_mod.restart
telegram_forwarder_status = telegram_forwarder_mod.status_text
telegram_forwarder_add_source = telegram_forwarder_mod.add_source
telegram_forwarder_remove_source = telegram_forwarder_mod.remove_source
telegram_forwarder_set_source_enabled = telegram_forwarder_mod.set_source_enabled
telegram_forwarder_is_running = telegram_forwarder_mod.is_running
notify_admin_group_join = notify_mod.notify_admin_group_join

handle_maintain = maintain_mod.handle_maintain
maintain_state = maintain_mod.state

handle_delete = delete_mod.handle_delet
handle_remove = remove_mod.handle_remove
handle_user = info_mod.handle_user
handle_out = out_mod.handle_out
handle_stop = stop_mod.handle_stop

load_group = group_storage_mod.load_group
handle_ban = ban_mod.handle_ban
handle_unban = unban_mod.handle_unban
handle_settings = settings_mod.handle_settings
enforce_banned_user = ban_mod.enforce_banned_user

handle_anime = anime_mod.handle_anime
handle_aniget = anime_mod.handle_aniget


def reload_bot_modules():
    global ai_mod, help_mod, join_mod, welcome_mod, telegram_forwarder_mod
    global notify_mod, maintain_mod, delete_mod, remove_mod, info_mod, out_mod, stop_mod
    global group_storage_mod, ban_mod, unban_mod, settings_mod, anime_mod
    global handle_anu, handle_help, handle_participant_joined, handle_new_participant
    global configure_telegram_forwarder, start_telegram_forwarder, stop_telegram_forwarder
    global restart_telegram_forwarder, telegram_forwarder_status
    global telegram_forwarder_add_source, telegram_forwarder_remove_source
    global telegram_forwarder_set_source_enabled, telegram_forwarder_is_running
    global notify_admin_group_join
    global handle_maintain, maintain_state, handle_delete, handle_remove
    global handle_user, handle_out, handle_stop, load_group, handle_ban
    global handle_unban, handle_settings, enforce_banned_user
    global handle_anime, handle_aniget

    ai_mod = load_module("ai", BASE_DIR / "commands" / "roleplay" / "ai.py")
    help_mod = load_module("help", BASE_DIR / "commands" / "help.py")
    join_mod = load_module("join", BASE_DIR / "plugins" / "join.py")
    welcome_mod = load_module("welcome", BASE_DIR / "plugins" / "welcome.py")
    telegram_forwarder_mod = load_module(
        "telegram_forwarder",
        BASE_DIR / "plugins" / "telegram_forwarder.py",
    )

    admin_dir = BASE_DIR / "commands" / "admin"
    notify_mod = load_module("notify", admin_dir / "notified.py")
    maintain_mod = load_module("maintain", admin_dir / "maintain.py")
    delete_mod = load_module("delete", admin_dir / "delete.py")
    remove_mod = load_module("remove", admin_dir / "remove.py")
    info_mod = load_module("info", admin_dir / "info.py")
    out_mod = load_module("out", admin_dir / "out.py")
    stop_mod = load_module("stop", admin_dir / "stop.py")

    group_dir = BASE_DIR / "commands" / "group_control"
    group_storage_mod = load_module("group_storage", group_dir / "storage.py")
    ban_mod = load_module("group_ban", group_dir / "ban.py")
    unban_mod = load_module("group_unban", group_dir / "unban.py")
    settings_mod = load_module("group_settings", group_dir / "settings.py")
    anime_mod = load_module("anime", BASE_DIR / "commands" / "anime.py")

    handle_anu = ai_mod.handle_anu
    handle_help = help_mod.handle_help
    handle_participant_joined = join_mod.handle_participant_joined
    handle_new_participant = welcome_mod.handle_new_participant
    configure_telegram_forwarder = telegram_forwarder_mod.configure
    start_telegram_forwarder = telegram_forwarder_mod.start
    stop_telegram_forwarder = telegram_forwarder_mod.stop
    restart_telegram_forwarder = telegram_forwarder_mod.restart
    telegram_forwarder_status = telegram_forwarder_mod.status_text
    telegram_forwarder_add_source = telegram_forwarder_mod.add_source
    telegram_forwarder_remove_source = telegram_forwarder_mod.remove_source
    telegram_forwarder_set_source_enabled = telegram_forwarder_mod.set_source_enabled
    telegram_forwarder_is_running = telegram_forwarder_mod.is_running
    notify_admin_group_join = notify_mod.notify_admin_group_join

    handle_maintain = maintain_mod.handle_maintain
    maintain_state = maintain_mod.state
    handle_delete = delete_mod.handle_delet
    handle_remove = remove_mod.handle_remove
    handle_user = info_mod.handle_user
    handle_out = out_mod.handle_out
    handle_stop = stop_mod.handle_stop

    load_group = group_storage_mod.load_group
    handle_ban = ban_mod.handle_ban
    handle_unban = unban_mod.handle_unban
    handle_settings = settings_mod.handle_settings
    enforce_banned_user = ban_mod.enforce_banned_user
    handle_anime = anime_mod.handle_anime
    handle_aniget = anime_mod.handle_aniget


def is_group_thread(message: Message) -> bool:
    return getattr(message, "thread_type", None) == ThreadType.GROUP


# ─────────────────────────────
# FRIEND REQUESTS
# ─────────────────────────────

async def fetch_existing_requests():
    try:
        async with client._state._session.get(
            "https://www.facebook.com/friends/requests/",
            headers={"Accept": "text/html,application/xhtml+xml"}
        ) as response:
            html = await response.text()

        matches = re.findall(r'"friend_requester_id"\s*:\s*"(\d+)"', html)

        for uid_str in set(matches):
            uid = int(uid_str)
            if uid not in pending_requests:
                pending_requests.append(uid)

        client.logger.info(f"Loaded {len(pending_requests)} friend request(s).")

    except Exception as e:
        client.logger.warning(f"Friend request fetch failed: {e}")


async def notify_admins_startup():
    tg_auto_start = bool(load_config().get("telegram", {}).get("forwarder_auto_start", False))
    text = (
        "✅ Bot started successfully.\n"
        f"👤 Messenger login: {getattr(client, 'name', None) or getattr(client, 'user_name', None) or 'Anu Sultana'}\n"
        "🟢 Messenger listener: online\n"
        f"📡 Telegram auto-start: {'on' if tg_auto_start else 'off'}\n\n"
        f"{telegram_forwarder_status()}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await client.send_message(text, str(admin_id))
        except Exception as exc:
            client.logger.warning("Startup notify failed for admin %s: %s", admin_id, exc)


# ─────────────────────────────
# EVENTS
# ─────────────────────────────

@client.event(EventType.LISTENING)
async def on_ready():
    global cookie_refresh_task

    print("BOT IS ONLINE")
    configure_telegram_forwarder(client, list(ADMIN_IDS))
    await save_current_cookies("startup")
    await notify_admins_startup()

    if cookie_refresh_task is None or cookie_refresh_task.done():
        cookie_refresh_task = asyncio.create_task(cookie_refresh_loop())

    await fetch_existing_requests()


# ─────────────────────────────
# COMMAND HANDLER
# ─────────────────────────────

async def handle_command(message: Message, cmd: str):

    sender_is_admin = is_admin(message.sender_id)

    if maintain_state["active"] and not sender_is_admin:
        await client.send_message(
            "🔧 Bot is under maintenance.",
            message.thread_id
        )
        return

    if cmd == "/help":
        await handle_help(client, message)

    elif cmd == "/ping":
        await client.send_message("Pong! 🏓", message.thread_id)

    elif cmd == "/time":
        now = datetime.now(BANGLADESH_TZ)
        time_str = now.strftime("%I:%M:%S %p")
        date_str = now.strftime("%A, %d %B %Y")

        await client.send_message(
            f"🕐 Bangladesh Time:\n{time_str}\n{date_str}",
            message.thread_id
        )

    elif cmd.startswith("/anu"):
        parts = cmd.split(maxsplit=1)
        if len(parts) < 2:
            await client.send_message("হ্যালো! কিছু বলো 😊", message.thread_id)
            return

        text = parts[1]
        asyncio.create_task(handle_anu(client, message, text))

    elif cmd == "/see_req":
        if not sender_is_admin:
            await client.send_message("❌ Admin only command.", message.thread_id)
            return

        if not pending_requests:
            await client.send_message("No pending friend requests.", message.thread_id)
            return

        users = await client.fetch_user_info(*[str(uid) for uid in pending_requests])

        lines = ["📋 Pending Requests:"]
        for i, uid in enumerate(pending_requests, start=1):
            user = users.get(str(uid))
            name = user.name if user else f"User {uid}"
            lines.append(f"{i}. {name} ({uid})")

        await client.send_message("\n".join(lines), message.thread_id)

    elif cmd.startswith("/maintain"):
        await handle_maintain(client, message, list(ADMIN_IDS))

    elif cmd == "/delet":
        await handle_delete(client, message, list(ADMIN_IDS))

    elif cmd.startswith("/remove"):
        if not is_group_thread(message):
            await client.send_message("❌ /remove only works in groups.", message.thread_id)
            return
        await handle_remove(client, message, list(ADMIN_IDS))

    elif cmd.startswith("/info"):
        await handle_user(client, message, list(ADMIN_IDS))

    elif cmd == "/out":
        if not is_group_thread(message):
            await client.send_message("❌ /out only works in groups.", message.thread_id)
            return
        await handle_out(client, message, list(ADMIN_IDS))

    elif cmd == "/stop":
        await handle_stop(client, message, list(ADMIN_IDS))

    elif cmd == "/reload":
        if not sender_is_admin:
            await client.send_message("❌ Admin only command.", message.thread_id)
            return
        tg_was_running = telegram_forwarder_is_running()
        if tg_was_running:
            await stop_telegram_forwarder()
        try:
            reload_bot_modules()
        except Exception as exc:
            await client.send_message(f"❌ Reload failed: {exc}", message.thread_id)
            client.logger.exception("Admin reload failed")
            return
        configure_telegram_forwarder(client, list(ADMIN_IDS))
        if tg_was_running:
            await restart_telegram_forwarder()
        await client.send_message("✅ Commands and plugins reloaded.", message.thread_id)

    elif cmd == "/tgstatus":
        if not sender_is_admin:
            await client.send_message("❌ Admin only command.", message.thread_id)
            return
        await client.send_message(telegram_forwarder_status(), message.thread_id)

    elif cmd == "/tgstop":
        if not sender_is_admin:
            await client.send_message("❌ Admin only command.", message.thread_id)
            return
        stopped = await stop_telegram_forwarder()
        status = "stopped" if stopped else "already stopped"
        await client.send_message(f"🛑 Telegram forwarder is {status}.", message.thread_id)

    elif cmd == "/tgstart":
        if not sender_is_admin:
            await client.send_message("❌ Admin only command.", message.thread_id)
            return
        started = await restart_telegram_forwarder()
        if started:
            await client.send_message("▶️ Telegram forwarder is starting.", message.thread_id)
        else:
            await client.send_message(
                "❌ Telegram forwarder cannot start yet. Messenger startup context is missing.",
                message.thread_id,
            )

    elif cmd.startswith("/tgadd"):
        if not sender_is_admin:
            await client.send_message("❌ Admin only command.", message.thread_id)
            return

        parts = cmd.split(maxsplit=2)
        if len(parts) < 2:
            await client.send_message(
                "Usage:\n"
                "/tgadd <telegram_source> <messenger_thread_id>\n"
                "Or: /tgadd <telegram_source> to use the default Messenger target.",
                message.thread_id,
            )
            return

        try:
            target = parts[2] if len(parts) > 2 else None
            source, target_thread, changed, state = telegram_forwarder_add_source(parts[1], target)
        except ValueError as exc:
            await client.send_message(f"❌ {exc}", message.thread_id)
            return

        restarted = False
        if changed and telegram_forwarder_is_running():
            restarted = await restart_telegram_forwarder()

        suffix = "\n🔄 Forwarder restarted with new sources." if restarted else ""
        await client.send_message(
            f"✅ Telegram route {state}.\n"
            f"📡 Source: {source}\n"
            f"💬 Messenger target: {target_thread}"
            f"{suffix}",
            message.thread_id,
        )

    elif cmd.startswith("/tgremove"):
        if not sender_is_admin:
            await client.send_message("❌ Admin only command.", message.thread_id)
            return

        parts = cmd.split(maxsplit=1)
        if len(parts) < 2:
            await client.send_message("Usage: /tgremove -1001234567890", message.thread_id)
            return

        try:
            source, removed = telegram_forwarder_remove_source(parts[1])
        except ValueError as exc:
            await client.send_message(f"❌ {exc}", message.thread_id)
            return

        restarted = False
        if removed and telegram_forwarder_is_running():
            restarted = await restart_telegram_forwarder()

        state = "removed" if removed else "was not in the list"
        suffix = "\n🔄 Forwarder restarted with new sources." if restarted else ""
        await client.send_message(f"✅ Telegram source {source} {state}.{suffix}", message.thread_id)

    elif cmd.startswith("/tgon") or cmd.startswith("/tgoff"):
        if not sender_is_admin:
            await client.send_message("❌ Admin only command.", message.thread_id)
            return

        parts = cmd.split(maxsplit=1)
        if len(parts) < 2:
            await client.send_message(
                "Usage:\n/tgon <telegram_source>\n/tgoff <telegram_source>",
                message.thread_id,
            )
            return

        enabled = parts[0] == "/tgon"
        try:
            source, target_thread, changed = telegram_forwarder_set_source_enabled(
                parts[1],
                enabled,
            )
        except ValueError as exc:
            await client.send_message(f"❌ {exc}", message.thread_id)
            return

        if target_thread is None:
            await client.send_message(
                f"❌ Telegram route {source} was not found. Add it with /tgadd first.",
                message.thread_id,
            )
            return

        restarted = False
        if changed and telegram_forwarder_is_running():
            restarted = await restart_telegram_forwarder()

        state = "ON" if enabled else "OFF"
        suffix = "\n🔄 Forwarder restarted with updated route status." if restarted else ""
        await client.send_message(
            f"✅ Telegram route is now {state}.\n"
            f"📡 Source: {source}\n"
            f"💬 Messenger target: {target_thread}"
            f"{suffix}",
            message.thread_id,
        )

    elif cmd.startswith("/ban"):
        if not is_group_thread(message):
            await client.send_message("❌ /ban only works in groups.", message.thread_id)
            return
        parts = cmd.split()
        args = parts[1:] if len(parts) > 1 else []
        await handle_ban(client, message, args, list(ADMIN_IDS))

    elif cmd.startswith("/unban"):
        if not is_group_thread(message):
            await client.send_message("❌ /unban only works in groups.", message.thread_id)
            return
        parts = cmd.split()
        args = parts[1:] if len(parts) > 1 else []
        await handle_unban(client, message, args, list(ADMIN_IDS))

    elif cmd.startswith("/settings") or cmd.startswith("/setting"):
        if not is_group_thread(message):
            await client.send_message(
                "❌ /settings only works in groups.",
                message.thread_id,
            )
            return
        parts = cmd.split()
        args = parts[1:] if len(parts) > 1 else []
        await handle_settings(client, message, args, list(ADMIN_IDS))

    elif cmd.startswith("/anime") and not cmd.startswith("/aniget"):
        asyncio.create_task(handle_anime(client, message))

    elif cmd.startswith("/aniget"):
        asyncio.create_task(handle_aniget(client, message))


# ─────────────────────────────
# MESSAGE EVENT
# ─────────────────────────────

@client.event
async def on_message(message: Message):

    try:
        if message.sender_id == client.uid:
            return

        if is_group_thread(message) and not is_admin(message.sender_id):
            group = load_group(message.thread_id)
            if str(message.sender_id) in group.get("banned", []):
                await enforce_banned_user(client, message)
                return

        if not message.text:
            return

        cmd = message.text.strip()

        await handle_command(message, cmd)

        replied = getattr(message, "replied_to_message", None)

        if (
            replied
            and getattr(replied, "sender_id", None)
            and str(replied.sender_id) == str(client.uid)
        ):
            asyncio.create_task(handle_anu(client, message, cmd))

    except Exception as e:
        print(f"ON_MESSAGE ERROR: {e}")


# ─────────────────────────────
# GROUP JOIN EVENT
# ─────────────────────────────

@client.event(EventType.PARTICIPANT_JOINED)
async def on_participant_joined(event):
    try:
        await handle_participant_joined(client, event)
        await handle_new_participant(client, event)
        await notify_admin_group_join(client, event, list(ADMIN_IDS))
    except Exception as e:
        print(f"GROUP JOIN ERROR: {e}")


# ─────────────────────────────
# FRIEND REQUEST EVENT
# ─────────────────────────────

@client.event(EventType.FRIEND_REQUEST_CHANGE)
async def on_friend_request(state: FriendRequestState):

    try:
        if state.action == "send":
            if state.user_id not in pending_requests:
                pending_requests.append(state.user_id)

        elif state.action in ("confirm", "reject"):
            if state.user_id in pending_requests:
                pending_requests.remove(state.user_id)

    except Exception as e:
        print(f"FRIEND REQUEST ERROR: {e}")


# ─────────────────────────────
# START BOT
# ─────────────────────────────

print("Starting bot...")
client.run()
