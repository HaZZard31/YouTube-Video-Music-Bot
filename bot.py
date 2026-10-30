import os
import re
import asyncio
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
REQUIRED_CHAT_ID = -1004311264974
REQUIRED_CHAT_LINK = "https://t.me/+CVr-2-wLKts5MTg1"

MESSAGES = {
    'start': "👋 Welcome to **youTubeBest00Bot**!\n\nSend me any YouTube link (Video or Shorts). I will give you fast, high-quality download options.",
    'invalid_link': "❌ Please send a valid YouTube link.",
    'downloading': "📥 Downloading media at high speed, please wait...",
    'uploading': "📤 Uploading file to Telegram...",
    'error': "❌ An error occurred during processing. Please try again later.",
    'fsub_msg': "⚠️ **You must join our group to use this bot!**\n\nPlease join using the button below and then try sending the link again.",
    'fsub_join': "📢 Join Group",
    'fsub_try': "🔄 Try Again"
}

async def is_user_member(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=REQUIRED_CHAT_ID, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception as e:
        print(f"Force Join Error: {e}")
        return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MESSAGES['start'], parse_mode='Markdown')

def extract_youtube_url(text: str) -> str:
    match = re.search(r'(https?://(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/|embed/)|youtu\.be/[^\s]+))', text)
    return match.group(0) if match else None

def download_youtube_media(url: str, quality: str):
    os.makedirs('downloads', exist_ok=True)
    ydl_opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'noplaylist': True,
        'socket_timeout': 30,
        'retries': 5,
        'fragment_retries': 5,
    }
    
    if quality == 'mp3':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        })
    else:
        ydl_opts.update({
            'format': f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best[height<={quality}]/best',
        })
        
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if quality == 'mp3':
                filename = os.path.splitext(filename)[0] + '.mp3'
            return filename
    except Exception as e:
        print(f"YTDL Error: {e}")
        return None

async def youtube_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if not data.startswith("yt_"):
        return
        
    try:
        _, quality, yt_url = data.split("_", 2)
    except ValueError:
        await query.edit_message_text(text=MESSAGES['error'])
        return
    
    await query.edit_message_text(text=MESSAGES['downloading'])

    loop = asyncio.get_event_loop()
    file_path = await loop.run_in_executor(None, download_youtube_media, yt_url, quality)

    if not file_path or not os.path.exists(file_path):
        await query.edit_message_text(text="❌ Download failed. The video might be restricted or unavailable.")
        return

    file_size = os.path.getsize(file_path)
    if file_size > 50 * 1024 * 1024:
        await query.edit_message_text(text="❌ File size exceeds Telegram's 50MB limit! Please choose a lower quality (e.g., 480p, 360p, or MP3).")
        if os.path.exists(file_path):
            os.remove(file_path)
        return

    await query.edit_message_text(text=MESSAGES['uploading'])

    try:
        if quality == 'mp3':
            with open(file_path, 'rb') as audio:
                await context.bot.send_audio(chat_id=query.message.chat_id, audio=audio, caption="Downloaded via youTubeBest00Bot ✨")
        else:
            with open(file_path, 'rb') as video:
                await context.bot.send_video(chat_id=query.message.chat_id, video=video, caption="Downloaded in HD ✨", supports_streaming=True)
        
        await query.message.delete()

        try:
            if query.message.reply_to_message:
                await query.message.reply_to_message.delete()
        except Exception:
            pass

    except Exception as e:
        print(f"Upload Error: {e}")
        await query.edit_message_text(text="❌ Upload failed due to network timeout or file size restriction.")
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user and not await is_user_member(context, user.id):
        keyboard = [
            [InlineKeyboardButton(MESSAGES['fsub_join'], url=REQUIRED_CHAT_LINK)],
            [InlineKeyboardButton(MESSAGES['fsub_try'], url=f"https://t.me/{context.bot.username}")]
        ]
        await update.message.reply_text(
            MESSAGES['fsub_msg'],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    text = update.message.text.strip() if update.message.text else ""
    yt_url = extract_youtube_url(text)
    
    if yt_url:
        keyboard = [
            [
                InlineKeyboardButton("1080p 🎬", callback_data=f"yt_1080_{yt_url}"),
                InlineKeyboardButton("720p 🎬", callback_data=f"yt_720_{yt_url}"),
            ],
            [
                InlineKeyboardButton("480p 🎬", callback_data=f"yt_480_{yt_url}"),
                InlineKeyboardButton("360p 🎬", callback_data=f"yt_360_{yt_url}"),
            ],
            [
                InlineKeyboardButton("144p 🎬", callback_data=f"yt_144_{yt_url}"),
                InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"yt_mp3_{yt_url}"),
            ]
        ]
        await update.message.reply_text("🎬 **Select Video Quality / Format:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    await update.message.reply_text(MESSAGES['invalid_link'])

def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(60)
        .pool_timeout(60)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(youtube_callback, pattern=r"^yt_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("youTubeBest00Bot is running smoothly with full optimizations...")
    app.run_polling()

if __name__ == "__main__":
    main()
