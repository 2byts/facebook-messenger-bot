import sys
from pathlib import Path

_dir = Path(__file__).resolve().parent
if str(_dir) not in sys.path:
    sys.path.insert(0, str(_dir))

from storage import can_use_group_control, load_group, resolve_target_user, save_group


async def handle_unban(client, message, args: list[str], admin_ids: list[str]):
    if not await can_use_group_control(client, message, admin_ids):
        await client.send_message(
            "❌ Only bot admins or this group’s admins can use /unban.",
            message.thread_id,
        )
        return

    thread_id = message.thread_id
    target_id = resolve_target_user(message, args)

    if not target_id:
        await client.send_message(
            "⚠️ How to use /unban:\n"
            "• Reply to the person's message, then send /unban\n"
            "• Or: /unban <user_id>",
            thread_id,
        )
        return

    group = load_group(thread_id)

    if target_id not in group["banned"]:
        await client.send_message("User is not banned.", thread_id)
        return

    group["banned"].remove(target_id)
    save_group(thread_id, group)

    await client.send_message(f"✅ Unbanned user: {target_id}", thread_id)
