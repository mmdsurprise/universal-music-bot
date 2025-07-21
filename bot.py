import os import aiohttp from dotenv import load_dotenv from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup from telegram.constants import ParseMode from telegram.ext import ( ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters )

شناسایی آهنگ از منابع مختلف

from utils.recognize import recognize_with_audd from utils.shazam import recognize_with_shazam from utils.google_search import recognize_with_google from utils.deezer import recognize_with_deezer from utils.muzikaz import recognize_with_muzikaz from utils.anghami import search_anghami from utils.fizy import search_fizy

موتورهای جست‌وجو

from utils.bing_search import bing_search from utils.ddg_search import ddg_search from utils.yahoo_search import yahoo_search from utils.yep_search import yep_search from utils.ask_search import ask_search from utils.metamind_search import metamind_search

دانلود آهنگ

from utils.downloader import download_audio_from_link

load_dotenv() BOT_TOKEN = os.getenv("BOT_TOKEN") CHANNEL_ID = os.getenv("CHANNEL_ID") or "@suprisemusic" CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME") or "suprisemusic"

application = ApplicationBuilder().token(BOT_TOKEN).build()

پیام‌های خوش‌آمد

welcome_messages = { "fa": "سلام به ربات آهنگ‌یاب بین‌المللی خوش اومدی 🎧\n\nبرای استفاده از ربات، کافیه یه تیکه از آهنگ یا ویس یا کلیپ اون رو بفرستی تا من کاملش رو برات پیدا کنم.\n\n🔒 قبل از استفاده لطفاً اول در کانال ما عضو شو.", "en": "Welcome to the International Music Finder Bot 🎧\n\nTo use the bot, just send me a voice or a part of the song and I’ll find the full version for you.\n\n🔒 Before using, please make sure you have joined our channel.", "tr": "Uluslararası Müzik Bulucu Botuna hoş geldiniz 🎧\n\nBotu kullanmak için sadece şarkının bir kısmını veya ses kaydını gönderin, ben sizin için tam halini bulurum.\n\n🔒 Devam etmeden önce lütfen kanalımıza katılın.", "ar": "مرحبًا بك في روبوت البحث عن الأغاني الدولي 🎧\n\nلاستخدام الروبوت، فقط أرسل جزءًا من الأغنية أو رسالة صوتية وسأجد النسخة الكاملة لك.\n\n🔒 قبل الاستخدام، تأكد من أنك انضممت إلى قناتنا." }

keyboard_labels = { "fa": "✅ بررسی عضویت", "en": "✅ Check Membership", "tr": "✅ Üyeliği Kontrol Et", "ar": "✅ التحقق من العضوية" }

دستور استارت

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user_lang = update.effective_user.language_code or "en" message = welcome_messages.get(user_lang, welcome_messages["en"]) button_text = keyboard_labels.get(user_lang, keyboard_labels["en"]) keyboard = InlineKeyboardMarkup([ [InlineKeyboardButton("🔗 عضویت در کانال", url="https://t.me/suprisemusic")], [InlineKeyboardButton(button_text, callback_data="check_membership")] ]) await update.message.reply_text(message, reply_markup=keyboard)

بررسی عضویت

async def check_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() user_id = query.from_user.id try: member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id) if member.status in ("member", "administrator", "creator"): await query.edit_message_text( text="✅ عضویتت تایید شد! حالا می‌تونی از ربات استفاده کنی. فقط کافیه تیکه آهنگ، ویس یا کلیپت رو بفرستی 🎵" ) else: keyboard = InlineKeyboardMarkup([ [InlineKeyboardButton("🔗 عضویت در کانال", url="https://t.me/suprisemusic")], [InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_membership")] ]) await query.message.reply_text( "❌ عضویت شما تایید نشد. لطفاً ابتدا در کانال عضو شوید و سپس دوباره دکمه بررسی عضویت را بزنید.", reply_markup=keyboard ) except Exception as e: await query.edit_message_text(text="⚠️ خطا در بررسی عضویت. لطفاً بعداً تلاش کن.") print(f"Membership check error: {e}")

پردازش ویس / ویدیو

async def handle_audio_video(update: Update, context: ContextTypes.DEFAULT_TYPE): message = update.message user_id = message.from_user.id file = None

if message.audio:
    file = await context.bot.get_file(message.audio.file_id)
elif message.voice:
    file = await context.bot.get_file(message.voice.file_id)
elif message.video:
    file = await context.bot.get_file(message.video.file_id)
elif message.video_note:
    file = await context.bot.get_file(message.video_note.file_id)
else:
    await message.reply_text("لطفاً ویس، آهنگ یا کلیپ تصویری ارسال کنید.")
    return

file_path = file.file_path
downloaded_file = await file.download_as_bytearray()
temp_filename = f"{user_id}_temp_input"
with open(temp_filename, 'wb') as f:
    f.write(downloaded_file)

await context.bot.send_chat_action(chat_id=message.chat.id, action="typing")

result = recognize_with_audd(temp_filename)
if not result:
    result = recognize_with_shazam(temp_filename)
if not result:
    result = recognize_with_google(temp_filename)
if not result:
    result = recognize_with_deezer(temp_filename)
if not result:
    result = recognize_with_fizy(temp_filename)
if not result:
    result = recognize_with_muzikaz(temp_filename)
if not result:
    result = recognize_with_anghami(temp_filename)

os.remove(temp_filename)

if result:
    title = result['title']
    artist = result['artist']
    await search_and_send_audio(title, artist, update, context)
else:
    await message.reply_text("❌ نتونستم آهنگ رو شناسایی کنم")

بخش ارسال آهنگ

async def search_and_send_audio(title, artist, update: Update, context: ContextTypes.DEFAULT_TYPE): query = f"{title} {artist} mp3 download" search_engines = [ bing_search, ddg_search, yahoo_search, yep_search, ask_search, metamind_search ]

for engine in search_engines:
    try:
        link = await engine(query)
        if link:
            file_path = await download_audio_from_link(link, title, artist)
            if file_path and os.path.exists(file_path):
                with open(file_path, 'rb') as audio:
                    sent = await context.bot.send_audio(
                        chat_id=CHANNEL_ID,
                        audio=audio,
                        caption=f"🎵 {title} - {artist}",
                        parse_mode=ParseMode.HTML
                    )
                os.remove(file_path)

                message_id = sent.message_id
                post_link = f"https://t.me/{CHANNEL_USERNAME}/{message_id}"
                await update.message.reply_text(
                    f"✅ آهنگ با موفقیت در کانال آپلود شد.\n📥 لینک دانلود:\n{post_link}"
                )
                return
    except Exception as e:
        print(f"❌ خطا در موتور {engine.__name__}: {e}")
        continue

await update.message.reply_text("❌ متاسفانه نتونستم آهنگ رو پیدا کنم. لطفاً دوباره امتحان کن.")

پیام متفرقه

async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text("متوجه نشدم چی گفتی. لطفاً آهنگ، ویس یا اسم خواننده بفرست 🎵")

افزودن هندلرها

application.add_handler(CommandHandler("start", start)) application.add_handler(CallbackQueryHandler(check_membership_callback, pattern="check_membership")) application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO | filters.VIDEO | filters.VIDEO_NOTE, handle_audio_video)) application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

print("🤖 Bot is running...") application.run_polling()

