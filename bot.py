import logging
import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import CommandStart
from yt_dlp import YoutubeDL

# Tokeningizni shu yerga yozing yoki Render'dagi Environment Variables'ga BOT_TOKEN deb qo'shing
TOKEN = os.getenv("BOT_TOKEN", "7963212879:AAFrvj54m8l78cUnW9Z_z70a4y3WkO9o8-s")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Yuklamalar uchun papka
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Salom! Menga Instagram, YouTube yoki TikTok havolasini yuboring, men uni sizga yuklab beraman."
    )

@dp.message(F.text.startswith("http"))
async def download_media(message: Message):
    url = message.text.strip()
    processing_msg = await message.answer("⏳ Yuklab olinmoqda, iltimos kuting...")

    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
        'format': 'best',
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            title = info.get('title', 'Media')

        if os.path.exists(file_path):
            video_file = FSInputFile(file_path)
            await message.answer_video(
                video=video_file,
                caption=f"✨ **{title}**\n\n@saberplus_bot orqali yuklab olindi!"
            )
            try:
                os.remove(file_path)
            except:
                pass
        else:
            await message.answer("❌ Kechirasiz, faylni topib bo'lmadi.")

    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await message.answer("❌ Kechirasiz, bu havoladan ma'lumotni yuklab bo'lmadi.")
    
    try:
        await processing_msg.delete()
    except:
        pass

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
