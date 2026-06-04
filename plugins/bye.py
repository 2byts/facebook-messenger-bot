from pathlib import Path

_here = Path(__file__).parent
GIF_PATH = str(_here / "assets" / "bye.gif")


def goodbye_text(target_name: str) -> str:
    return (
        f"Goodbye, {target_name}! 👋\n"
        f"আশা করি ভালো থাকবে। Take care! 🌸\n"
        f"See you around!"
    )


async def handle_participant_removed(
    client,
    message,
    target_id: str,
    target_name: str,
    thread_id: str,
):
    """Send a goodbye message (and GIF) after a successful /remove kick."""
    text = goodbye_text(target_name)
    await client.send_message(text, thread_id)

    gif = Path(GIF_PATH)
    if gif.exists():
        await client.send_files_from_path(thread_id, [GIF_PATH])
    else:
        client.logger.warning("plugins/assets/bye.gif not found — skipping GIF send.")
