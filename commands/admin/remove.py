"""
Remove participant command.
Usage:
  • Reply to someone's message and send /remove  ← most reliable
  • /remove @mention                             ← works if mention data is available
  Bot admins and current group admins can use this command.
  Bot must have group admin privilege for this action.
"""

import sys
from pathlib import Path

GROUP_CONTROL_DIR = Path(__file__).resolve().parents[1] / "group_control"
if str(GROUP_CONTROL_DIR) not in sys.path:
    sys.path.insert(0, str(GROUP_CONTROL_DIR))

from storage import can_use_group_control, is_protected_user


async def handle_remove(client, message, admin_ids: list[str]):
    """Remove a participant from the group."""
    if not await can_use_group_control(client, message, admin_ids):
        await client.send_message(
            "❌ Only bot admins or this group’s admins can use /remove.",
            message.thread_id,
        )
        return

    target_id = None
    target_name = None

    # Priority 1: reply to the target's message (most reliable)
    if message.replied_to_message:
        target_id = str(message.replied_to_message.sender_id)

    # Priority 2: mention (only works if Messenger sends mention metadata)
    elif message.mentions:
        target_id = str(message.mentions[0].user_id)
        target_name = message.mentions[0].name

    if not target_id:
        await client.send_message(
            "⚠️ How to use /remove:\n"
            "• Reply to the person's message you want to remove, then send /remove\n"
            "• Example: swipe their message → type /remove → send",
            message.thread_id,
        )
        return

    # Try to get the name if we don't have it yet
    if not target_name:
        try:
            users = await client.fetch_user_info(target_id)
            user = users.get(target_id)
            target_name = user.name if user else target_id
        except Exception:
            target_name = target_id

    if await is_protected_user(client, message.thread_id, target_id, admin_ids):
        await client.send_message(
            f"🚫 Cannot remove {target_name} — bot admins, group admins, and myself are protected.",
            message.thread_id,
        )
        return

    try:
        await client.send_message(
            f"👢 Removing {target_name} from the group...",
            message.thread_id,
        )
        await client.remove_participant(message.thread_id, target_id)
    except Exception as e:
        await client.send_message(
            f"❌ Failed to remove {target_name}.\n"
            "Make sure I have admin privileges in this group.",
            message.thread_id,
        )
        client.logger.warning(f"/remove failed for {target_id}: {e}")
