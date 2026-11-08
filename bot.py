Python
import logging
import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import yt_dlp

TOKEN = "9111287076:AAES9VAw0zlvxG9KG4MIQCJ1IhAMpwUnmjE"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "Salom! 👋 **SaberPlus Bot**'ga xush kelibsiz!\n\n"
        "Menga Instagram, TikTok yoki boshqa platformalardan video yoki musiqa havolasini yuboring, men uni darhol yuklab beraman!"
    )

@dp.message()
async def download_media(message: types.Message):
    url = message.text.strip()
    
    if not url.startswith("http"):
        await message.answer("Iltimos, yaroqli havola (link) yuboring!")
        return

    processing_msg = await message.answer("⏳ Havola tekshirilmoqda va yuklab olinmoqda, iltimos kuting...")

    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'noplaylist': True,
    }

    try:
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                return filename, info.get('title', 'Media')

        loop = asyncio.get_running_loop()
        file_path, title = await loop.run_in_executor(None, download)

        await message.answer("📤 Fayl yuborilmoqda...")

        with open(file_path, 'rb') as f:
            await message.answer_video(
                video=f, 
                caption=f"✨ **{title}**\n\n@saberplus_bot orqali yuklab olindi!"
            )

        os.remove(file_path)
        await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)

    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await message.edit_text("❌ Kechirasiz, bu havoladan ma'lumotni yuklab bo'lmadi.")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
