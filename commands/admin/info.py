"""
User info command.
Usage (admin only):
  • Reply to someone's message and send /user   ← most reliable
  • /info @mention                              ← works if mention data is available
"""


async def handle_user(client, message, admin_ids: list[str]):
    """Fetch and display a user's profile information."""
    if str(message.sender_id) not in admin_ids:
        await client.send_message(
            "❌ Only admins can use /info", message.thread_id
        )
        return

    target_id = None

    # Priority 1: reply to the target's message (most reliable)
    if message.replied_to_message:
        target_id = str(message.replied_to_message.sender_id)

    # Priority 2: replied_to_message_id only (fetch sender)
    elif message.replied_to_message_id:
        try:
            fetched = await client.fetch_message_info(
                message.replied_to_message_id, message.thread_id
            )
            if fetched:
                target_id = str(fetched.sender_id)
        except Exception:
            pass

    # Priority 3: mention (works only when Messenger includes mention metadata)
    elif message.mentions:
        target_id = str(message.mentions[0].user_id)

    if not target_id:
        await client.send_message(
            "⚠️ How to use /info:\n"
            "• Reply to someone's message, then send /info\n"
            "• Example: swipe their message → type /info → send",
            message.thread_id,
        )
        return

    try:
        users = await client.fetch_user_info(target_id)
        user = users.get(target_id)
    except Exception as e:
        await client.send_message(
            f"❌ Failed to fetch user info: {e}", message.thread_id
        )
        return

    if not user:
        await client.send_message(
            "❌ Could not find that user.", message.thread_id
        )
        return

    profile_url = user.url or "N/A"
    username = f"@{user.username}" if user.username else "N/A"
    gender = user.gender.capitalize() if user.gender else "N/A"
    friend_status = "✅ Friend" if user.is_friend else "❌ Not a friend"
    pic_url = (
        user.image if isinstance(user.image, str)
        else str(user.image) if user.image
        else None
    )

    info = (
        f"👤 User Profile\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📛 Name: {user.name}\n"
        f"🔤 First name: {user.first_name or 'N/A'}\n"
        f"🪪 Username: {username}\n"
        f"🆔 User ID: {user.id}\n"
        f"⚥ Gender: {gender}\n"
        f"🤝 Friend status: {friend_status}\n"
    )

    await client.send_message(info, message.thread_id)

    # Send profile picture if available
    if pic_url:
        try:
            await client.send_files_from_url(message.thread_id, [pic_url])
        except Exception:
            pass
