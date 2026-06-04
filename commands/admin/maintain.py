"""
Maintenance mode toggle.
Usage (admin only):
  /maintain run  — enable maintenance mode (bot ignores all non-admin messages)
  /maintain end  — disable maintenance mode (bot resumes normal operation)
"""

# Shared state — main.py imports this dict to check the flag
state = {"active": False}


async def handle_maintain(client, message, admin_ids: list[str]):
    """Handle /maintain run and /maintain end commands."""
    if str(message.sender_id) not in admin_ids:
        await client.send_message(
            "❌ Only admins can change maintenance mode.", message.thread_id
        )
        return

    parts = message.text.strip().split()
    if len(parts) < 2:
        status = "🟢 ON" if state["active"] else "🔴 OFF"
        await client.send_message(
            f"⚙️ Maintenance mode is currently {status}.\n"
            "Use /maintain run to enable or /maintain end to disable.",
            message.thread_id,
        )
        return

    sub = parts[1].lower()

    if sub == "run":
        state["active"] = True
        await client.send_message(
            "🔧 Maintenance mode is now ON.\n"
            "I will not respond to any non-admin messages until maintenance ends.",
            message.thread_id,
        )

    elif sub == "end":
        state["active"] = False
        await client.send_message(
            "✅ Maintenance mode is now OFF.\n"
            "I am back online and ready!",
            message.thread_id,
        )

    else:
        await client.send_message(
            "❓ Unknown option. Use:\n• /maintain run\n• /maintain end",
            message.thread_id,
        )
