import os
import json
import importlib.util
from pathlib import Path
from groq import AsyncGroq
from bot_config import load_config, resolve_path

_here = Path(__file__).parent
CONFIG = load_config()


def _load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, _here / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_role = _load_module("role")
_image = _load_module("image_gen")

SYSTEM_PROMPT = _role.SYSTEM_PROMPT
generate_and_send_image = _image.generate_and_send_image

MEMORY_DIR = resolve_path(CONFIG.get("paths", {}).get("roleplay_memory", "runtime/roleplay_memory"))
MEMORY_DIR.mkdir(exist_ok=True)

MODEL = CONFIG.get("groq", {}).get("model", "llama-3.3-70b-versatile")

IMAGE_KEYWORDS = [
    "photo", "picture", "image", "selfie", "pic", "ছবি", "তোমার ছবি",
    "দেখাও", "দাও", "show me", "your photo", "send photo", "give me photo",
    "তোমাকে দেখতে", "ফটো", "একটা ছবি",
]

LOVE_KEYWORDS = [
    "love you", "i love you", "ভালোবাসি তোমাকে", "তোমাকে ভালোবাসি",
    "পছন্দ করি তোমাকে", "love u", "তোমাকে পছন্দ করি",
]


def _load_memory(uid: str) -> dict:
    path = MEMORY_DIR / f"{uid}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "uid": uid,
        "name": None,
        "loves_anu": False,
        "details": {},
        "history": [],
    }


def _save_memory(uid: str, data: dict):
    path = MEMORY_DIR / f"{uid}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _detect_name(text: str) -> str | None:
    import re
    for pat in [r"(?:আমার নাম|my name is|i am called|i'm|i am|ami)\s+([A-Za-zঀ-৿]+)"]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _is_image_request(text: str) -> bool:
    return any(kw in text.lower() for kw in IMAGE_KEYWORDS)


def _is_love_expression(text: str) -> bool:
    return any(kw in text.lower() for kw in LOVE_KEYWORDS)


def _build_system_prompt(memory: dict) -> str:
    extra_parts = []
    if memory.get("name"):
        extra_parts.append(f"এই user এর নাম {memory['name']}। নাম ধরে কথা বলো মাঝে মাঝে।")
    if memory.get("loves_anu"):
        extra_parts.append("এই user তোমাকে পছন্দ করে। একটু বেশি মিষ্টি ব্যবহার করো।")
    for k, v in memory.get("details", {}).items():
        extra_parts.append(f"{k}: {v}")
    if extra_parts:
        return SYSTEM_PROMPT + "\n\nUser সম্পর্কে জানা তথ্য:\n" + "\n".join(extra_parts)
    return SYSTEM_PROMPT


async def handle_anu(client, message, text: str):
    api_key = os.getenv("GROQ_API_KEY") or CONFIG.get("groq", {}).get("api_key")
    if not api_key:
        await client.send_message("আমি এখন একটু ব্যস্ত আছি, পরে কথা বলো! 😅", message.thread_id)
        return

    uid = str(message.sender_id)
    thread_id = message.thread_id
    memory = _load_memory(uid)

    detected_name = _detect_name(text)
    if detected_name and not memory.get("name"):
        memory["name"] = detected_name

    if _is_love_expression(text):
        memory["loves_anu"] = True

    if _is_image_request(text):
        _save_memory(uid, memory)
        await generate_and_send_image(client, thread_id)
        return

    # Build messages list
    messages = [{"role": "system", "content": _build_system_prompt(memory)}]
    for h in memory.get("history", [])[-20:]:
        role = "assistant" if h["role"] == "model" else h["role"]
        messages.append({"role": role, "content": h["text"]})
    messages.append({"role": "user", "content": text})

    try:
        groq_client = AsyncGroq(api_key=api_key)
        response = await groq_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=300,
            temperature=0.9,
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        reply = "একটু সমস্যা হচ্ছে, আবার চেষ্টা করো! 😅"
        client.logger.warning(f"Groq error: {e}")

    memory.setdefault("history", [])
    memory["history"].append({"role": "user", "text": text})
    memory["history"].append({"role": "model", "text": reply})
    memory["history"] = memory["history"][-40:]

    _save_memory(uid, memory)
    await client.send_message(reply, thread_id)
