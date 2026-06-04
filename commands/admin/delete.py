"""
Message deletion command.
Usage (admin only):
  Reply to any message and send /delet — the bot will unsend/remove that message.
  Note: Facebook only allows unsending messages sent by the bot itself.
"""


async def handle_delet(client, message, admin_ids: list[str]):
    """Unsend the message the admin replied to."""
    if str(message.sender_id) not in admin_ids:
        await client.send_message(
            "❌ Only admins can use /delet.", message.thread_id
        )
        return

    # The admin must reply to a message
    target_id = message.replied_to_message_id
    if not target_id:
        # Try the nested replied_to_message object
        if message.replied_to_message:
            target_id = message.replied_to_message.id

    if not target_id:
        await client.send_message(
            "⚠️ Please *reply* to the message you want to delete, then send /delet.",
            message.thread_id,
        )
        return

    try:
        await client.unsend(target_id, message.thread_id)
        # Silently confirm by reacting — or just delete admin's /delet command too
        await client.unsend(message.id, message.thread_id)
    except Exception as e:
        await client.send_message(
            f"❌ Could not delete the message.\n"
            "Note: I can only delete messages that I sent myself.",
            message.thread_id,
        )
        client.logger.warning(f"/delet failed: {e}")
