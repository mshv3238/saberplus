import asyncio
import logging
import os
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder
import yt_dlp

# Loggingni sozlash
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Foydalanuvchilarning oxirgi havolalarini saqlab turish uchun lug'at
user_urls = {}

# Render uchun web server
async def handle(request):
    return web.Response(text="SaberPlus Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server {port}-portda ishga tushdi.")

# Videoni yuklab olish (musiqasi va ovozi bilan birga)
def download_video(url: str) -> str:
    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s.%(ext)s'),
        'format': 'best[ext=mp4]/best',
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# Faqat audioni yuklab olish
def download_audio(url: str) -> str:
    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s_audio.%(ext)s'),
        'format': 'bestaudio/best',
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        base, _ = os.path.splitext(filename)
        mp3_file = base + '.mp3'
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
            "✨ <b>SaberPlus Bot</b>'ga xush kelibsiz!\n\n"
            "Menga Instagram, YouTube yoki TikTok havolasini yuboring. "
            "Men sizga videoni **musiqasi bilan birga** yuklab beraman va qo'shimcha ravishda musiqasini ham alohida olishingiz uchun imkoniyat yarataman!"
        )

    @dp.message(F.text.startswith("http"))
    async def handle_url(message: types.Message):
        url = message.text.strip()
        user_id = message.from_user.id
        user_urls[user_id] = url  # Havolani vaqtincha saqlaymiz
        
        processing_msg = await message.answer("⏳ Video tayyorlanmoqda, iltimos biroz kuting...")
        
        file_path = None
        try:
            loop = asyncio.get_running_loop()
            file_path = await loop.run_in_executor(None, download_video, url)
            
            if file_path and os.path.exists(file_path):
                video_file = types.FSInputFile(file_path)
                
                # Tugma yaratamiz: Musiqasini ham olish uchun
                builder = InlineKeyboardBuilder()
                builder.button(text="🎵 Musiqasini ham yuklab olish", callback_data="get_audio_version")
                
                await message.answer_video(
                    video=video_file,
                    caption="✅ <b>SaberPlus</b> orqali yuklab olindi!\n\n👇 Musiqasi kerak bo'lsa, tugmani bosing:",
                    reply_markup=builder.as_markup()
                )
                await processing_msg.delete()
            else:
                await message.answer("❌ Kechirasiz, bu havoladan videoni yuklab bo'lmadi.")
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

    # Foydalanuvchi "Musiqasini ham yuklab olish" tugmasini bosganda
    @dp.callback_query(F.data == "get_audio_version")
    async def send_audio_callback(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        url = user_urls.get(user_id)
        
        if not url:
            await callback.answer("❌ Havola topilmadi yoki eskirgan. Iltimos, havolani qaytadan yuboring.", show_alert=True)
            return

        await callback.message.answer("🎧 Musiqa tayyorlanmoqda, biroz kuting...")
        audio_path = None
        try:
            loop = asyncio.get_running_loop()
            audio_path = await loop.run_in_executor(None, download_audio, url)
            
            if audio_path and os.path.exists(audio_path):
                audio_file = types.FSInputFile(audio_path)
                await callback.message.answer_audio(
                    audio=audio_file,
                    caption="🎵 <b>SaberPlus</b> — Musiqa versiyasi"
                )
                await callback.answer("Marhamat, musiqa tayyor! 🎉")
            else:
                await callback.message.answer("❌ Kechirasiz, musiqani ajratib bo'lmadi.")
        except Exception as e:
            logging.error(f"Audio xatolik: {e}")
            await callback.message.answer(f"❌ Xatolik yuz berdi: {e}")
        finally:
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except:
                    pass

    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("SaberPlus bot polling boshlandi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi!")
