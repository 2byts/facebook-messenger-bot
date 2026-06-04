import asyncio
import os


async def handle_stop(client, message, admin_ids: list[str]):
    """Admin-only command to shut down the bot process."""
    if str(message.sender_id) not in admin_ids:
        await client.send_message("❌ Only admins can use /stop.", message.thread_id)
        return

    await client.send_message("🛑 Bot is shutting down now.", message.thread_id)
    client.logger.warning("/stop used by admin; shutting down bot process.")

    await asyncio.sleep(1)
    os._exit(0)
