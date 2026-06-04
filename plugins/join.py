from pathlib import Path
from fbchat_muqit import ParticipantsAdded
from bot_config import load_config

_here = Path(__file__).parent
GIF_PATH = str(_here / "assets" / "image.gif")
BOT_NICKNAME = load_config().get("bot", {}).get("nickname", "🌸 ʜɪɴᴀᴛᴀ 🌸")

WELCOME_TEXT = (
    "Hi! I am Hinata, your group assistant! 🌸\n"
    "আমি এই গ্রুপের সব কিছু দেখব এবং সবাইকে সাহায্য করব।\n\n"
    "Nickname set: 🌸 ʜɪɴᴀᴛᴀ 🌸\n"
    "I will watch group changes and help when needed. 👀"
)


async def handle_participant_joined(client, event: ParticipantsAdded):
    thread_id = event.messageMetadata.thread_id

    # Check if the client itself was added
    client_was_added = any(
        str(p.user_id) == str(client.uid)
        for p in event.added_participants
    )

    if not client_was_added:
        return

    # participants tuple holds all member IDs in the group
    member_count = len(event.participants)

    # Less than 3 members means individual/DM chat — skip
    if member_count < 3:
        return

    try:
        await client.change_nickname(thread_id, str(client.uid), BOT_NICKNAME)
    except Exception as exc:
        client.logger.warning("Could not set bot nickname in group %s: %s", thread_id, exc)

    # Send welcome text
    await client.send_message(WELCOME_TEXT, thread_id)

    # Send welcome GIF if it exists
    gif = Path(GIF_PATH)
    if gif.exists():
        await client.send_files_from_path(thread_id, [GIF_PATH])
    else:
        client.logger.warning("plugins/assets/image.gif not found — skipping GIF send.")
