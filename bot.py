import os
import json
import requests
import yt_dlp
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, MessageHandler, filters, CommandHandler,
    CallbackContext, ContextTypes
)

# مشخصات شما (به صورت ثابت وارد شده)
BOT_TOKEN = '6429471851:AAGBPIRyoT-WvsY0H7HkmH0wtpDFwlt1Ggo'
ADMIN_ID = 6201054084
ACR_KEY = '0376a4412cd5c60c7695cd7b4e390c20'
AUDD_KEY = '2df291d1793a3943db4d1d60e3e0f7c2'
GPT_KEY = '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'

CHANNEL_ID = "@suprisemusic"
CACHE_FILE = "used.json"
USAGE_LIMIT = 5

# ------------------------- راه‌اندازی لاگ‌ها -----------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------- ابزارها -----------------------------
def is_user_member(user_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember?chat_id={CHANNEL_ID}&user_id={user_id}"
    response = requests.get(url).json()
    status = response.get("result", {}).get("status", "")
    return status in ["member", "administrator", "creator"]

def load_usage():
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, "r") as f:
        return json.load(f)

def save_usage(usage):
    with open(CACHE_FILE, "w") as f:
        json.dump(usage, f)

def check_duplicate(file_id):
    if os.path.exists("cache.json"):
        with open("cache.json", "r") as f:
            data = json.load(f)
    else:
        data = []

    if file_id in data:
        return True
    data.append(file_id)
    with open("cache.json", "w") as f:
        json.dump(data, f)
    return False

# ------------------------- جستجو با ChatGPT/AI -----------------------------
def search_song_google_ai(query):
    headers = {
        "Authorization": f"Bearer {GPT_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"""I received this audio query from a user: '{query}'. Search Google or song databases and tell me the name of the song, artist, and provide a YouTube or download link if possible."""
    data = {
        "model": "gpt-4",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
    try:
        return res.json()["choices"][0]["message"]["content"]
    except:
        return "نتوانستم چیزی پیدا کنم."

# ------------------------- دانلود از یوتیوب -----------------------------
def download_song_from_youtube(query, filename="output.mp3"):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": filename,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }],
        "quiet": True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=True)
            return filename
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return None

# ------------------------- تشخیص آهنگ -----------------------------
def identify_song_acr(file_path):
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {'api_token': ACR_KEY}
        response = requests.post('https://api.acrcloud.com/v1/identify', files=files, data=data)
    result = response.json()
    try:
        return result['metadata']['music'][0]
    except:
        return None

def identify_song_audd(file_path):
    with open(file_path, 'rb') as f:
        response = requests.post('https://api.audd.io/', data={'api_token': AUDD_KEY, 'return': 'apple_music,spotify'}, files={'file': f})
    result = response.json()
    try:
        return result['result']
    except:
        return None

# ------------------------- کنترل پیام ها -----------------------------
async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    usage = load_usage()
    usage[str(user.id)] = 0
    save_usage(usage)

    # زبان کاربر
    lang = user.language_code or "en"
    greetings = {
        "fa": f"سلام {user.first_name} عزیز 🌟\nبرای دریافت آهنگ، وویس یا ویدیو بفرست.",
        "en": f"Hello {user.first_name}! 🎵\nSend a voice, audio or video file to identify and get the song.",
    }

    # پیام خوش‌آمدگویی
    msg = greetings.get(lang, greetings["en"])
    await update.message.reply_text(msg)

    # ارسال اطلاعات به ادمین
    info = f"👤 New User:\nID: {user.id}\nName: {user.full_name}\nLang: {lang}"
    await context.bot.send_message(chat_id=ADMIN_ID, text=info)

async def stats(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    usage = load_usage()
    await update.message.reply_text(f"👥 Total Users: {len(usage)}")

async def handle_media(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = user.id

    if not is_user_member(chat_id):
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")]])
        await update.message.reply_text("برای استفاده از ربات ابتدا در کانال عضو شوید:", reply_markup=btn)
        return

    usage = load_usage()
    count = usage.get(str(chat_id), 0)
    if count >= USAGE_LIMIT:
        await update.message.reply_text("⛔️ سقف استفاده روزانه شما پر شده است.")
        return

    file = update.message.voice or update.message.audio or update.message.video
    if not file:
        await update.message.reply_text("فایل پشتیبانی نشده.")
        return

    file_id = file.file_id
    if check_duplicate(file_id):
        await update.message.reply_text("این فایل قبلاً ارسال شده است.")
        return

    file_path = f"{chat_id}_{file_id}.mp3"
    await file.get_file().download_to_drive(file_path)

    result = identify_song_acr(file_path) or identify_song_audd(file_path)

    if result:
        title = result.get("title") or "Unknown"
        artist = result.get("artist") or "Unknown"
        query = f"{title} {artist}"
        mp3_file = download_song_from_youtube(query)
        if not mp3_file:
            result_text = search_song_google_ai(query)
            await update.message.reply_text(f"🔍 AI Search Result:\n{result_text}")
            return
    else:
        await update.message.reply_text("تشخیص ممکن نشد. تلاش با هوش مصنوعی...")
        result_text = search_song_google_ai("نامشخص")
        await update.message.reply_text(f"🔍 AI Search Result:\n{result_text}")
        return

    sent = await context.bot.send_audio(chat_id=CHANNEL_ID, audio=open(mp3_file, "rb"), caption=f"{title} - {artist}")
    post_link = f"https://t.me/{CHANNEL_ID.lstrip('@')}/{sent.message_id}"
    await update.message.reply_text(f"✅ آهنگ با موفقیت ارسال شد!\n📎 [دریافت در کانال]({post_link})", parse_mode="Markdown")

    usage[str(chat_id)] = count + 1
    save_usage(usage)
    os.remove(file_path)

# ------------------------- اجرای ربات -----------------------------
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO | filters.VIDEO, handle_media))
app.run_polling()
