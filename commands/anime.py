import os
import re
import asyncio
import aiohttp
from difflib import SequenceMatcher
from pathlib import Path
from groq import AsyncGroq
from bot_config import load_config, resolve_path

CONFIG = load_config()

# 🎌 Core API Infrastructure — Adheres strictly to docs.api.jikan.moe specifications
JIKAN_API_BASE = "https://api.jikan.moe/v4"

# 📂 System Directories
DOWNLOAD_DIR = resolve_path(CONFIG.get("paths", {}).get("anime_downloads", "runtime/anidown"))
THUMBNAIL_DIR = resolve_path(CONFIG.get("paths", {}).get("anime_thumbnails", "runtime/thumbnails"))

DOWNLOAD_DIR.mkdir(exist_ok=True)
THUMBNAIL_DIR.mkdir(exist_ok=True)

# ─────────────────────────────
# 🛠️ INTERNAL UTILITY FUNCTIONS
# ─────────────────────────────


def log(title, data=None):
    print(f"\n⚙️ [DEBUG] {title}")
    if data is not None:
        print(data)


def norm(t):
    return re.sub(r"\s+", " ", t.lower().strip()) if t else ""


def score(a, b):
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def slugify(text):
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower())
    return s.strip("_")


def title_variants(item):
    variants = [item.get("title"), item.get("title_english"), item.get("title_japanese")]
    variants.extend(t.get("title") for t in item.get("titles", []) if t.get("title"))
    return [v for v in variants if v]


async def _correct_query_with_groq(query: str) -> str:
    """
    🧠 Uses Groq AI to check for typing mistakes or spelling errors in the anime name.
    If a typo like 'naruro' is sent, it returns 'naruto'.
    """
    api_key = os.getenv("GROQ_API_KEY") or CONFIG.get("groq", {}).get("api_key")
    if not api_key:
        log("⚠️ GROQ API KEY MISSING - Skipping AI Typo Correction")
        return query

    # Strict system instructions so the model only outputs the corrected text string
    system_prompt = (
        "You are an anime search parsing engine. Your job is to correct spelling mistakes "
        "and typos in anime titles submitted by users. Respond with ONLY the corrected title. "
        "Do not include punctuation, explanations, introductions, or extra text. "
        "Example Input: naruro shippuden -> Example Output: naruto shippuden"
    )

    try:
        groq_client = AsyncGroq(api_key=api_key)
        response = await groq_client.chat.completions.create(
            model=CONFIG.get("groq", {}).get("model", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            max_tokens=50,
            temperature=0.2,  # Kept very low so it doesn't hallucinate random names
        )
        corrected_title = response.choices[0].message.content.strip()
        bad_answers = (
            "no corrected title",
            "no title",
            "not available",
            "unknown",
            "n/a",
        )
        if not corrected_title or any(bad in norm(corrected_title) for bad in bad_answers):
            return query
        log(f"🧠 GROQ TYPO CORRECTION LAYER: '{query}' -> '{corrected_title}'")
        return corrected_title
    except Exception as e:
        log(f"❌ Groq Correction Layer Error: {e}")
        return query


# ─────────────────────────────
# 🛰️ JIKAN V4 SEARCH & DOWNLOAD ENGINE
# ─────────────────────────────


async def search_anime_jikan(session, query):
    """
    🔍 Queries Jikan v4 search resource: GET /anime?q={query}&limit=5
    Extracts core text properties along with graphic thumbnail asset paths.
    """
    log("📡 JIKAN V4 SEARCH REQUEST", query)
    url = f"{JIKAN_API_BASE}/anime"
    params = {"q": query, "limit": "5"}

    try:
        async with session.get(url, params=params, timeout=10) as r:
            if r.status == 429:
                log("⚠️ RATE LIMIT HIT (429) - Sleeping briefly before retrying")
                await asyncio.sleep(2)
                return await search_anime_jikan(session, query)

            if r.status != 200:
                return None

            payload = await r.json()
            results = payload.get("data", [])
    except Exception as e:
        log("❌ JIKAN API FETCH EXCEPTION", e)
        return None

    if not results:
        return None

    best = None
    best_score = 0
    best_rank = 0
    for item in results:
        item_best_score = 0
        for title_variant in title_variants(item):
            if not title_variant:
                continue
            s = score(query, title_variant)
            item_best_score = max(item_best_score, s)

        type_bonus = {
            "TV": 0.08,
            "ONA": 0.04,
            "OVA": 0.02,
            "Movie": 0.0,
            "Special": -0.03,
            "Music": -0.05,
            "CM": -0.05,
            "PV": -0.05,
        }.get(item.get("type"), 0)

        rank = item_best_score + type_bonus
        if rank > best_rank:
            best_score = item_best_score
            best_rank = rank
            best = item

    return best if best_score >= 0.65 else None


async def download_thumbnail(session, url, anime_id):
    """
    📥 Downloads the high-quality thumbnail from the web
    and saves it locally inside the /thumbnails directory.
    """
    if not url:
        return None

    local_path = THUMBNAIL_DIR / f"anime_{anime_id}.jpg"
    log("💾 DOWNLOADING COVER ART TO LOCAL STORAGE", local_path)

    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                with open(local_path, "wb") as f:
                    f.write(await response.read())
                return local_path
    except Exception as e:
        log("❌ THUMBNAIL DOWNLOAD EXCEPTION", e)

    return None


# ─────────────────────────────
# 🤖 EXPORTED COMMAND HANDLERS
# ─────────────────────────────


async def handle_anime(client, message):
    """
    🎌 Processes the /anime description info command.
    Downloads the high-quality thumbnail locally and uploads it with detailed text.
    """
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await client.send_message(
            "⚠️ **Usage:** `/anime [name]`", message.thread_id
        )

    raw_query = parts[1]

    # 🧠 Run the AI typo helper directly before calling the search API!
    query = await _correct_query_with_groq(raw_query)

    async with aiohttp.ClientSession() as session:
        anime = await search_anime_jikan(session, query)
        if not anime:
            return await client.send_message(
                "❌ **No metadata found on MyAnimeList.**", message.thread_id
            )

        # 📄 1. Parse metadata text structures out of the API response payload
        title = anime.get("title_english") or anime.get("title") or "Unknown Title"
        genres = ", ".join([g.get("name", "") for g in anime.get("genres", [])])
        synopsis = anime.get("synopsis", "No synopsis available.")
        mal_id = anime.get("mal_id")

        # 🖼️ 2. Extract and download the high-resolution JPG asset
        remote_thumbnail_url = (
            anime.get("images", {}).get("jpg", {}).get("large_image_url")
        )
        local_image_path = await download_thumbnail(
            session, remote_thumbnail_url, mal_id
        )

        # ✨ Beautifully structured response layout with custom details
        response_text = (
            f"🎌 ✨ **{title}** ✨\n\n"
            f"🆔 **MAL ID:** `{mal_id}`\n"
            f"🎬 **Total Episodes:** {anime.get('episodes') or 'Ongoing 🌟'}\n"
            f"⭐ **Score:** {anime.get('score') or 'N/A'}\n"
            f"📺 **Type:** {anime.get('type', 'N/A')}\n"
            f"🎭 **Genres:** {genres or 'N/A'}\n\n"
            f"📝 **Synopsis:**\n{synopsis[:250]}..."
        )

        # Send the metadata info card text block first
        await client.send_message(response_text, message.thread_id)

        try:
            # 🚀 3. Uses path-based file sending array instead of open binary stream
            if local_image_path and local_image_path.exists():
                log("⬆️ UPLOADING THUMBNAIL VIA NATIVE PATH FILE STRATEGY")
                await client.send_files_from_path(
                    message.thread_id, [str(local_image_path)]
                )
            else:
                raise FileNotFoundError("Local image asset missing")

        except Exception as media_err:
            log("❌ THUMBNAIL UPLOAD ERROR - FALLING BACK TO URL LINK", media_err)
            if remote_thumbnail_url:
                await client.send_message(
                    f"📷 **Cover Art Link:** {remote_thumbnail_url}", message.thread_id
                )


async def handle_aniget(client, message):
    """
    🍿 Active placeholder function so the bot reads it and runs cleanly.
    The real video download features are disabled right now for your future edits!
    """
    await client.send_message(
        "⚙️ ✨ **The `/aniget` streaming system is currently down for upgrades! Check back later!** ✨ 🍿",
        message.thread_id,
    )


# ─────────────────────────────
# 🚧 FUTURE /ANIGET PIPELINE WORKING CODES
# ─────────────────────────────
# This commented block preserves the exact logic structure matching your exact client parameters!
#
# async def handle_aniget_PRODUCTION_LOGIC(client, message):
#     parts = message.text.split()
#     if len(parts) < 3:
#         return await client.send_message("⚠️ **Usage:** `/aniget [name] [episode]`", message.thread_id)
#
#     try:
#         ep = int(parts[-1])
#     except ValueError:
#         return await client.send_message("⚠️ **Episode must be a valid number!**", message.thread_id)
#
#     raw_query = " ".join(parts[1:-1])
#
#     # 🧠 Typo auto-correction integrated into the pipeline here too!
#     query = await _correct_query_with_groq(raw_query)
#
#     status_msg = await client.send_message("🔍 **Initializing stream connection layers...**", message.thread_id)
#
#     async with aiohttp.ClientSession() as session:
#         anime = await search_anime_jikan(session, query)
#         if not anime:
#             return await client.send_message("❌ **Anime title not found.**", message.thread_id)
#
#         title = anime.get("title_english") or anime.get("title")
#         video_url = None   # <-- Plug in your link extractor function here later!
#
#         if not video_url:
#             return await client.send_message(f"❌ **No streaming resources found for Episode {ep}.**", message.thread_id)
#
#         file_path = DOWNLOAD_DIR / f"{slugify(title)}_EP{ep}.mp4"
#         try:
#             async with session.head(video_url, allow_redirects=True, timeout=5) as head_resp:
#                 size_bytes = int(head_resp.headers.get('Content-Length', 0))
#                 size_mb = size_bytes / (1024 * 1024)
#
#             if 0 < size_mb <= 25.0:
#                 await client.send_message(f"📥 **Downloading video asset stream ({size_mb:.1f}MB)...**", message.thread_id)
#                 async with session.get(video_url) as video_resp:
#                     if video_resp.status == 200:
#                         with open(file_path, 'wb') as f:
#                             async for chunk in video_resp.content.iter_chunked(1024 * 4):
#                                 f.write(chunk)
#
#                 await client.send_message("🚀 **Shipping movie file directly to chat...**", message.thread_id)
#
#                 if file_path.exists():
#                     await client.send_files_from_path(message.thread_id, [str(file_path)])
#             else:
#                 fallback_text = f"🎌 **{title} — Episode {ep}**\n\n📺 **Direct Stream Player Link:**\n{video_url}"
#                 await client.send_message(fallback_text, message.thread_id)
#         except Exception as err:
#             log("❌ STREAM PIPELINE CRITICAL FALLBACK", err)
#             fallback_text = f"🎌 **{title} — Episode {ep}**\n\n📺 **Direct Stream Player Link:**\n{video_url}"
#             await client.send_message(fallback_text, message.thread_id)
#         finally:
#             if file_path.exists():
#                 os.remove(file_path)
