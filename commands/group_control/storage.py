import json
from pathlib import Path
from bot_config import load_config, resolve_path

DATA_DIR = resolve_path(load_config().get("paths", {}).get("group_data", "runtime/group_data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _file(thread_id: str):
    return DATA_DIR / f"{thread_id}.json"


def default_group() -> dict:
    return {
        "banned": [],
        "settings": {},
    }


def load_group(thread_id: str) -> dict:
    path = _file(thread_id)

    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    else:
        data = {}

    base = default_group()
    base["banned"] = [str(uid) for uid in data.get("banned", [])]
    base["settings"] = dict(data.get("settings", {}))
    return base


def save_group(thread_id: str, data: dict):
    path = _file(thread_id)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


async def fetch_group_admin_ids(client, thread_id: str) -> set[str]:
    try:
        threads = await client.fetch_thread_info([str(thread_id)])
    except Exception as exc:
        client.logger.warning("Could not fetch group admins for %s: %s", thread_id, exc)
        return set()

    if not threads:
        return set()

    return {str(admin_id) for admin_id in getattr(threads[0], "thread_admins", ())}


async def is_group_admin(client, thread_id: str, user_id: str) -> bool:
    return str(user_id) in await fetch_group_admin_ids(client, thread_id)


async def can_use_group_control(client, message, bot_admin_ids: list[str]) -> bool:
    sender_id = str(message.sender_id)
    if sender_id in {str(admin_id) for admin_id in bot_admin_ids}:
        return True
    return await is_group_admin(client, message.thread_id, sender_id)


async def is_protected_user(client, thread_id: str, user_id: str, bot_admin_ids: list[str]) -> bool:
    protected_ids = {str(admin_id) for admin_id in bot_admin_ids}
    protected_ids.add(str(client.uid))
    protected_ids.update(await fetch_group_admin_ids(client, thread_id))
    return str(user_id) in protected_ids


def resolve_target_user(message, args: list[str]) -> str | None:
    """Resolve a user ID from reply, mention, or command args."""
    replied = getattr(message, "replied_to_message", None)
    if replied and getattr(replied, "sender_id", None):
        return str(replied.sender_id)

    mentions = getattr(message, "mentions", None)
    if mentions:
        return str(mentions[0].user_id)

    if args:
        return str(args[0])

    return None
