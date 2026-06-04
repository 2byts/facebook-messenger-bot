import asyncio
import sys
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from bot_config import load_config, resolve_path


async def main():
    print("🔐 Starting Telegram Login...")
    telegram = load_config().get("telegram", {})
    api_id = int(telegram.get("api_id"))
    api_hash = str(telegram.get("api_hash"))
    phone = str(telegram.get("phone"))
    session_file = str(resolve_path(telegram.get("session_file", "telegram_session")))

    client = TelegramClient(session_file, api_id, api_hash)

    await client.connect()

    if not await client.is_user_authorized():
        print(f"📱 Sending OTP to {phone}...")
        await client.send_code_request(phone)

        code = input("Enter OTP: ")

        try:
            await client.sign_in(phone, code)

        except SessionPasswordNeededError:
            password = input("🔐 Enter Telegram 2FA password: ")
            await client.sign_in(password=password)

    me = await client.get_me()
    print(f"✅ Logged in as {me.first_name}")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
