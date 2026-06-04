import sys
from pathlib import Path

_dir = Path(__file__).resolve().parent
if str(_dir) not in sys.path:
    sys.path.insert(0, str(_dir))

from storage import can_use_group_control, load_group, save_group


async def handle_settings(client, message, args: list[str], admin_ids: list[str]):
    if not await can_use_group_control(client, message, admin_ids):
        await client.send_message(
            "❌ Only bot admins or this group’s admins can use /settings.",
            message.thread_id,
        )
        return

    thread_id = message.thread_id
    group = load_group(thread_id)

    if not args:
        settings = group.get("settings") or {}
        if not settings:
            await client.send_message(
                "⚙️ No custom settings for this group.\n"
                "Usage: /settings <key> <on/off>",
                thread_id,
            )
            return

        lines = [f"  • {key}: {value}" for key, value in settings.items()]
        await client.send_message(
            "⚙️ Group settings:\n" + "\n".join(lines),
            thread_id,
        )
        return

    if len(args) < 2:
        await client.send_message(
            "Usage: /settings <key> <on/off>",
            thread_id,
        )
        return

    key = args[0].lower()
    value = args[1].lower() == "on"

    group["settings"][key] = value
    save_group(thread_id, group)

    await client.send_message(f"⚙️ {key} set to {value}", thread_id)
