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

# Fayllar saqlanadigan vaqtinchalik papka
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Render port talab qilgani uchun oddiy web server
async def handle(request):
    return web.Response(text="Bot is running successfully!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server {port}-portda ishga tushdi.")

# yt-dlp yordamida video va musiqani birga yuklab olish funksiyasi
def download_media(url: str) -> str:
    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s.%(ext)s'),
        # Video va audioni birlashtirib, eng yaxshi sifatli mp4 formatga o'tkazadi
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        base, _ = os.path.splitext(filename)
        mp4_file = base + '.mp4'
        if os.path.exists(mp4_file):
            return mp4_file
        return filename

async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        logging.error("BOT_TOKEN topilmadi! Render Environment Variables'ga qo'shganingizni tekshiring.")
        return

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # /start buyrug'i
    @dp.message(F.text == "/start")
    async def cmd_start(message: types.Message):
        await message.answer(
            "Salom! 👋\n\n"
            "Menga **Instagram**, **YouTube** yoki **TikTok** havolasini yuboring, "
            "men sizga videoni **musiqasi va ovozi bilan birga** tezda yuklab beraman!"
        )

    # Havolalarni qabul qilib, yuklab beruvchi handler
    @dp.message(F.text.startswith("http"))
    async def handle_url(message: types.Message):
        url = message.text.strip()
        processing_msg = await message.answer("⏳ Video yuklab olinmoqda, iltimos biroz kuting...")
        
        file_path = None
        try:
            # yt-dlp bloklanib qolmasligi uchun uning ishini alohida oqimga (executor) qo'yamiz
            loop = asyncio.get_running_loop()
            file_path = await loop.run_in_executor(None, download_media, url)
            
            if file_path and os.path.exists(file_path):
                # Videoni foydalanuvchiga yuborish
                video_file = types.FSInputFile(file_path)
                await message.answer_video(
                    video=video_file, 
                    caption="✅ Marhamat, videongiz tayyor!"
                )
                await processing_msg.delete()
            else:
                await message.answer("❌ Kechirasiz, bu havoladan videoni yuklab bo'lmadi.")
                await processing_msg.delete()
                
        except Exception as e:
            logging.error(f"Xatolik yuz berdi: {e}")
            await message.answer(f"❌ Xatolik yuz berdi: {e}")
            try:
                await processing_msg.delete()
            except:
                pass
        finally:
            # Server xotirasi to'lib qolmasligi uchun yuklangan videoni o'chirib tashlaymiz
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass

    # Veb serverni ham, bot pollingni ham bir vaqtda ishga tushiramiz
    await start_web_server()
    
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Bot polling muvaffaqiyatli boshlandi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi!")
