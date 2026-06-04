"""
Leave group command.
Usage:
  /out — bot sends a farewell message then leaves the group.
  Bot admins and current group admins can use this command.
"""

import sys
from pathlib import Path

GROUP_CONTROL_DIR = Path(__file__).resolve().parents[1] / "group_control"
if str(GROUP_CONTROL_DIR) not in sys.path:
    sys.path.insert(0, str(GROUP_CONTROL_DIR))

from storage import can_use_group_control

FAREWELL_MESSAGE = (
    "👋 Goodbye everyone!\n"
    "আমাকে এই গ্রুপ থেকে বের করা হচ্ছে। \n"
    "দেখা হবে আবার! Take care everyone 💙\n"
    "— Anu 🌸"
)


async def handle_out(client, message, admin_ids: list[str]):
    """Send farewell message and leave the group."""
    if not await can_use_group_control(client, message, admin_ids):
        await client.send_message(
            "❌ Only bot admins or this group’s admins can use /out.",
            message.thread_id,
        )
        return

    try:
        await client.send_message(FAREWELL_MESSAGE, message.thread_id)
        # Remove self from the group
        await client.remove_participant(message.thread_id, str(client.uid))
    except Exception as e:
        await client.send_message(
            "❌ Failed to leave the group. Make sure I have the necessary permissions.",
            message.thread_id,
        )
        client.logger.warning(f"/out failed: {e}")
