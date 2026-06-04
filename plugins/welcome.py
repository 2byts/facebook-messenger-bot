from pathlib import Path

from fbchat_muqit import ParticipantsAdded

_here = Path(__file__).parent
GIF_PATH = str(_here / "assets" / "welcome.gif")


def welcome_text(name: str) -> str:
    return (
        f"Welcome, {name}! 🌸\n"
        f"স্বাগতম! আমি Anu — এই গ্রুপে তোমাকে সাহায্য করতে পারি।\n"
        f"Feel free to say hi anytime! 😊"
    )


async def handle_new_participant(client, event: ParticipantsAdded):
    """Welcome newly added members (not when only the bot is added)."""
    thread_id = event.messageMetadata.thread_id
    member_count = len(event.participants)

    if member_count < 3:
        return

    bot_uid = str(client.uid)
    new_members = [
        p
        for p in event.added_participants
        if str(p.user_id) != bot_uid
    ]

    if not new_members:
        return

    gif_path = Path(GIF_PATH)
    send_gif = gif_path.exists()
    if not send_gif:
        client.logger.warning("plugins/assets/welcome.gif not found — skipping GIF send.")

    for participant in new_members:
        name = participant.name or str(participant.user_id)
        await client.send_message(welcome_text(name), thread_id)
        if send_gif:
            await client.send_files_from_path(thread_id, [GIF_PATH])
