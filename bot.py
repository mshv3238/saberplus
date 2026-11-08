import asyncio
import logging
import os
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import yt_dlp

# Loggingni sozlash
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Render uchun web server
async def handle(request):
    return web.Response(text="TinglaBot clone is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server {port}-portda ishga tushdi.")

# YouTube / Instagram / TikTok'dan faqat MP3 (audio) yuklab olish funksiyasi
def download_audio(url: str) -> str:
    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s.%(ext)s'),
        'format': 'bestaudio/best',
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        # Fayl kengaytirib .mp3 ga o'tkazamiz
        base, _ = os.path.splitext(filename)
        mp3_file = base + '.mp3'
        
        # yt-dlp ba'zida webm/m4a yuklaydi, uni mp3 ga o'xshatib yuboramiz yoki mavjudini olamiz
        if os.path.exists(mp3_file):
            return mp3_file
        return filename

async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        logging.error("BOT_TOKEN topilmadi!")
        return

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    @dp.message(F.text == "/start")
    async def cmd_start(message: types.Message):
        await message.answer(
            "🎵 <b>TinglaBot</b>'ga xush kelibsiz!\n\n"
            "Menga YouTube, Instagram yoki TikTok havolasini yuboring, "
            "men sizga uni <b>musiqa (audio)</b> shaklida yuklab beraman!"
        )

    @dp.message(F.text.startswith("http"))
    async def handle_url(message: types.Message):
        url = message.text.strip()
        processing_msg = await message.answer("🎧 Musiqa tayyorlanmoqda, iltimos biroz kuting...")
        
        file_path = None
        try:
            loop = asyncio.get_running_loop()
            file_path = await loop.run_in_executor(None, download_audio, url)
            
            if file_path and os.path.exists(file_path):
                audio_file = types.FSInputFile(file_path)
                await message.answer_audio(
                    audio=audio_file,
                    caption="🎵 @TinglaBot orqali yuklab olindi!"
                )
                await processing_msg.delete()
            else:
                await message.answer("❌ Kechirasiz, bu havoladan audioni yuklab bo'lmadi.")
                await processing_msg.delete()
                
        except Exception as e:
            logging.error(f"Xatolik: {e}")
            await message.answer(f"❌ Xatolik yuz berdi: {e}")
            try:
                await processing_msg.delete()
            except:
                pass
        finally:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass

    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Bot polling boshlandi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi!")
