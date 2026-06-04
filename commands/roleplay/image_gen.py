import urllib.parse
from datetime import datetime, timezone, timedelta
from bot_config import load_config

BOT_CONFIG = load_config().get("bot", {})
BANGLADESH_TZ = timezone(timedelta(hours=BOT_CONFIG.get("timezone_hours", 6)))


def get_time_context() -> tuple[str, str]:
    hour = datetime.now(BANGLADESH_TZ).hour
    if 5 <= hour < 12:
        return "morning", "bright morning sunlight, college campus, fresh daylight"
    elif 12 <= hour < 17:
        return "afternoon", "afternoon sunlight, outdoors in Dhaka city, warm"
    elif 17 <= hour < 20:
        return "evening", "golden hour sunset, warm glowing light, beautiful sky"
    else:
        return "night", "cozy indoor room, soft warm lamp light, nighttime, relaxed"


def get_anu_reply(time_of_day: str) -> str:
    replies = {
        "morning": "এই নাও সকালের ছবি! কলেজে যাওয়ার আগে তুলেছিলাম 📸😊",
        "afternoon": "এই নাও দুপুরের একটা ছবি! বাইরে একটু ঘুরছিলাম 😄📸",
        "evening": "সন্ধ্যার ছবি দিলাম! আলোটা কিন্তু সুন্দর ছিল 🌅📸",
        "night": "রাতের বেলা ঘরে বসে তোলা ছবি 😊 একটু ঝাপসা হলেও ভালো লাগছে 🌙📸",
    }
    return replies.get(time_of_day, "এই নাও আমার ছবি! 📸")


async def generate_and_send_image(client, thread_id: str):
    time_of_day, scene = get_time_context()

    prompt = (
        f"anime 8K photo of a beautiful young hinata from naruto college girl, 21 years old, "
        f"long dark hair, wearing casual traditional japanis clothes, "
        f"anime look, {scene}, anime, high quality, "
        f"soft natural lighting, friendly smile"
    )

    seed = int(datetime.now(BANGLADESH_TZ).timestamp())
    encoded = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=512&height=768&nologo=true&seed={seed}&model=flux"
    )

    reply_text = get_anu_reply(time_of_day)
    await client.send_message(reply_text, thread_id)
    await client.send_files_from_url(thread_id, [url])
