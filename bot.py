t web
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder
import yt_dlp
from shazamio import Shazam

# Loggingni sozlash
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

USERS_FILE = "users.json"
user_urls = {}

def add_user(user_id):
    users = set()
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    users = set(json.loads(content))
        except Exception:
            pass
    users.add(user_id)
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(list(users), f)
    except Exception:
        pass
    return len(users)

# Render uchun web server (Port ochib turish shart)
async def handle(request):
    return web.Response(text="SaberPlus Bot is running perfectly!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server {port}-portda muvaffaqiyatli ishga tushdi.")

def download_video(url: str) -> str:
    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s.%(ext)s'),
        'format': 'best[ext=mp4]/best',
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

async def get_audio_and_recognize(url: str):
    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s_audio.%(ext)s'),
        'format': 'bestaudio/best',
        'noplaylist': True,
    }
    loop = asyncio.get_running_loop()
    def extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            mp3_file = base + '.mp3'
            if os.path.exists(mp3_file):
                return mp3_file
            return filename

    audio_path = await loop.run_in_executor(None, extract)
    
    track_title = "Noma'lum musiqa"
    track_artist = "SaberPlus"
    
    if audio_path and os.path.exists(audio_path):
        try:
            shazam = Shazam()
            out = await shazam.recognize(audio_path)
            if 'track' in out:
                track_title = out['track'].get('title', 'Noma\'lum')
                track_artist = out['track'].get('subtitle', 'Noma\'lum artist')
        except Exception as e:
            logging.error(f"Shazam xatoligi: {e}")
            
    return audio_path, f"{track_artist} - {track_title}"

async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        logging.error("BOT_TOKEN topilmadi!")
        return

    # Oldin web server ishga tushadi
    await start_web_server()

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    @dp.message(F.text == "/start")
    async def cmd_start(message: types.Message):
        count = add_user(message.from_user.id)
        await message.answer(
            f"✨ <b>SaberPlus Bot</b>'ga xush kelibsiz!\n\n"
            f"📊 Jami foydalanuvchilar: <b>{count} ta</b>\n\n"
            "Menga Instagram, YouTube yoki TikTok havolasini yuboring!"
        )

    @dp.message(F.text.startswith("http"))
    async def handle_url(message: types.Message):
        url = message.text.strip()
        user_id = message.from_user.id
        user_urls[user_id] = url
        
        processing_msg = await message.answer("⏳ Video tayyorlanmoqda, iltimos biroz kuting...")
        
        file_path = None
        try:
            loop = asyncio.get_running_loop()
            file_path = await loop.run_in_executor(None, download_video, url)
            
            if file_path and os.path.exists(file_path):
                video_file = types.FSInputFile(file_path)
                builder = InlineKeyboardBuilder()
                builder.button(text="🎵 Musiqasini topish va yuklab olish", callback_data="get_audio_version")
                
                await message.answer_video(
                    video=video_file,
                    caption="✅ <b>SaberPlus</b> orqali yuklab olindi!",
                    reply_markup=builder.as_markup()
                )
                await processing_msg.delete()
            else:
                await message.answer("❌ Kechirasiz, videoni yuklab bo'lmadi.")
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

    @dp.callback_query(F.data == "get_audio_version")
    async def send_audio_callback(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        url = user_urls.get(user_id)
        
        if not url:
            await callback.answer("❌ Havola topilmadi yoki eskirgan. Qaytadan yuboring.", show_alert=True)
            return

        await callback.message.answer("🎧 Musiqa Shazam orqali aniqlanmoqda, kuting...")
        audio_path = None
        try:
            audio_path, track_info = await get_audio_and_recognize(url)
            if audio_path and os.path.exists(audio_path):
                audio_file = types.FSInputFile(audio_path)
                await callback.message.answer_audio(
                    audio=audio_file,
                    caption=f"🎵 <b>Musiqa:</b> {track_info}\n🤖 <i>SaberPlus</i>"
                )
                await callback.answer("Tayyor! 🎉")
            else:
                await callback.message.answer("❌ Musiqani aniqlab bo'lmadi.")
        except Exception as e:
            logging.error(f"Audio xatolik: {e}")
            await callback.message.answer(f"❌ Xatolik: {e}")
        finally:
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except:
                    pass

    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Bot polling boshlandi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi!")
