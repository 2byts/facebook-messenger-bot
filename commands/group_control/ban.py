import sys
from pathlib import Path

_dir = Path(__file__).resolve().parent
if str(_dir) not in sys.path:
    sys.path.insert(0, str(_dir))

from storage import can_use_group_control, is_protected_user, load_group, resolve_target_user, save_group


async def handle_ban(client, message, args: list[str], admin_ids: list[str]):
    if not await can_use_group_control(client, message, admin_ids):
        await client.send_message(
            "❌ Only bot admins or this group’s admins can use /ban.",
            message.thread_id,
        )
        return

    thread_id = message.thread_id
    target_id = resolve_target_user(message, args)

    if not target_id:
        await client.send_message(
            "⚠️ How to use /ban:\n"
            "• Reply to the person's message, then send /ban\n"
            "• Or: /ban <user_id>",
            thread_id,
        )
        return

    if await is_protected_user(client, thread_id, target_id, admin_ids):
        await client.send_message("🚫 Cannot ban bot admins, group admins, or myself.", thread_id)
        return

    group = load_group(thread_id)

    if target_id in group["banned"]:
        await client.send_message("Already banned.", thread_id)
        return

    group["banned"].append(target_id)
    save_group(thread_id, group)

    target_name = target_id
    try:
        users = await client.fetch_user_info(target_id)
        user = users.get(target_id)
        if user:
            target_name = user.name
    except Exception:
        pass

    kicked = False
    try:
        await client.remove_participant(thread_id, target_id)
        kicked = True
    except Exception as e:
        client.logger.warning(f"/ban kick failed for {target_id}: {e}")

    if kicked:
        await client.send_message(
            f"🚫 Banned and removed {target_name} ({target_id}).",
            thread_id,
        )
    else:
        await client.send_message(
            f"🚫 Banned {target_name} ({target_id}).\n"
            "Could not remove them — make sure I have admin privileges.",
            thread_id,
        )


async def enforce_banned_user(client, message):
    """Kick banned users if they still post in the group."""
    sender_id = str(message.sender_id)
    thread_id = message.thread_id

    if await is_protected_user(client, thread_id, sender_id, []):
        client.logger.warning("Skipped ban enforcement for protected user %s", sender_id)
        return

    try:
        await client.remove_participant(thread_id, sender_id)
    except Exception as e:
        client.logger.warning(f"ban enforcement kick failed for {sender_id}: {e}")

    try:
        await client.send_message(
            "🚫 You are banned from this group.",
            thread_id,
        )
    except Exception as e:
        client.logger.warning(f"ban enforcement warn failed: {e}")
