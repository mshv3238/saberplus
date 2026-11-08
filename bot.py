import asyncio
import logging
import os
import sys
import json
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
import yt_dlp
from shazamio import Shazam

# 1. Loggingni sozlash (Xatoliklarni terminalda ko'rsatish uchun)
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

USERS_FILE = "users.json"
user_urls = {}

# --- SOZLAMALAR (O'zingizga moslab o'zgartirasiz) ---
ADMIN_ID = 123456789          # <-- O'zingizning Telegram ID raqamingizni yozing
CHANNEL_ID = "@sizning_kanal" # <-- Majburiy obuna bo'ladigan kanal username (agar kerak bo'lmasa bo'sh qoldiring)
CHANNEL_URL = "https://t.me/sizning_kanal" # <-- Kanal havolasi

# Foydalanuvchilarni bazaga qo'shish va sanash
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

# 2. Render "Port scan timeout" xatosi bermasligi uchun Web-server
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

# 3. Videoni yuklab olish (YouTube, Instagram, TikTok)
def download_video(url: str) -> str:
    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s.%(ext)s'),
        'format': 'best[ext=mp4]/best',
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# 4. Audioni yuklab olish va Shazam orqali musiqa nomini aniqlash
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

# Majburiy obunani tekshirish funksiyasi
async def check_subscription(bot: Bot, user_id: int) -> bool:
    if not CHANNEL_ID:
        return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except Exception:
        pass
    return False

async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        logging.error("BOT_TOKEN topilmadi!")
        return

    # Render serverini birinchi bo'lib ishga tushiramiz
    await start_web_server()

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # --- /start BUYRUG'I VA REKLAMA/KANAL TEKSHiriruvi ---
    @dp.message(F.text == "/start")
    async def cmd_start(message: types.Message):
        user_id = message.from_user.id
        count = add_user(user_id)

        # Majburiy obuna tekshiruvi
        if CHANNEL_ID and not await check_subscription(bot, user_id):
            builder = InlineKeyboardBuilder()
            builder.button(text="📢 Kanalga obuna bo'lish", url=CHANNEL_URL)
            builder.button(text="✅ Obunani tekshirish", callback_data="check_sub")
            builder.adjust(1)
            
            await message.answer(
                "⚠️ <b>Botdan foydalanish uchun homiy kanalimizga obuna bo'ling!</b>\n\n"
                "Obuna bo'lgach, <b>\"✅ Obunani tekshirish\"</b> tugmasini bosing:",
                reply_markup=builder.as_markup()
            )
            return

        await message.answer(
            f"✨ <b>SaberPlus Bot</b>'ga xush kelibsiz!\n\n"
            f"📊 Jami foydalanuvchilar: <b>{count} ta</b>\n\n"
            "📥 Menga Instagram, YouTube yoki TikTok havolasini yuboring. "
            "Men sizga videoni va musiqasini yuklab beraman!",
            reply_markup=get_main_keyboard()
        )

    # Obunani tekshirish tugmasi uchun handler
    @dp.callback_query(F.data == "check_sub")
    async def callback_check_sub(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        if await check_subscription(bot, user_id):
            await callback.message.delete()
            count = get_user_count() if 'get_user_count' in globals() else 0
            await callback.message.answer(
                "✅ Rahmat! Obuna tasdiqlandi.\n\n"
                "📥 Endi Instagram, YouTube yoki TikTok havolasini yuborishingiz mumkin!",
                reply_markup=get_main_keyboard()
            )
        else:
            await callback.answer("❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)

    def get_main_keyboard():
        builder = InlineKeyboardBuilder()
        builder.button(text="📢 Reklama joylashtirish", url="https://t.me/sizning_username") # O'z profilingizni yozing
        builder.button(text="ℹ️ Bot haqida", callback_data="about_bot")
        builder.adjust(1)
        return builder.as_markup()

    @dp.callback_query(F.data == "about_bot")
    async def about_callback(callback: types.CallbackQuery):
        await callback.answer("SaberPlus — Instagram, YouTube va TikTok'dan video va musiqa yuklovchi tezkor bot!", show_alert=True)

    # --- ADMIN REKLAMA TARQATISH BUYRUG'I (/send) ---
    @dp.message(F.text.startswith("/send"))
    async def broadcast_message(message: types.Message):
        if message.from_user.id != ADMIN_ID:
            return

        text = message.text[len("/send"):].strip()
        if not text:
            await message.answer("❌ Xabar matnini yozing. Masalan: /send Reklama matni")
            return

        if not os.path.exists(USERS_FILE):
            await message.answer("❌ Foydalanuvchilar bazasi bo'sh.")
            return

        with open(USERS_FILE, "r") as f:
            users = json.load(f)

        success = 0
        blocked = 0
        
        await message.answer(f"📢 Reklama tarqatish boshlandi. Jami: {len(users)} ta foydalanuvchi.")

        for uid in users:
            try:
                await bot.send_message(uid, text)
                success += 1
                await asyncio.sleep(0.04) # Telegram spam cheklovi uchun
            except Exception:
                blocked += 1

        await message.answer(f"✅ Reklama tarqatildi!\n\n✔️ Yetib bordi: {success} ta\n❌ Bloklaganlar: {blocked} ta")

    # --- HAVOLALARNI QABUL QILISH VA VIDEO YUKLASH ---
    @dp.message(F.text.startswith("http"))
    async def handle_url(message: types.Message):
        user_id = message.from_user.id
        
        # Majburiy obunani tekshirish
        if CHANNEL_ID and not await check_subscription(bot, user_id):
            builder = InlineKeyboardBuilder()
            builder.button(text="📢 Kanalga obuna bo'lish", url=CHANNEL_URL)
            builder.button(text="✅ Obunani tekshirish", callback_data="check_sub")
            builder.adjust(1)
            await message.answer("⚠️ Botdan foydalanish uchun avval homiy kanalga obuna bo'ling!", reply_markup=builder.as_markup())
            return

        url = message.text.strip()
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
                builder.adjust(1)
                
                await message.answer_video(
                    video=video_file,
                    caption="✅ <b>SaberPlus</b> orqali yuklab olindi!\n\n👇 Musiqasini ham yuklab olish uchun tugmani bosing:",
                    reply_markup=builder.as_markup()
                )
                await processing_msg.delete()
            else:
                await message.answer("❌ Kechirasiz, bu havoladan videoni yuklab bo'lmadi.")
                await processing_msg.delete()
                
        except Exception as e:
            logging.error(f"Xatolik: {e}")
            await message.answer(f"❌ Xatolik yuz berdi: Videoni yuklash imkoni bo'lmadi.")
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

    # --- MUSIQANI SHAZAM ORQALI TOPISH VA YUBORISH ---
    @dp.callback_query(F.data == "get_audio_version")
    async def send_audio_callback(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        url = user_urls.get(user_id)
        
        if not url:
            await callback.answer("❌ Havola topilmadi yoki eskirgan. Qaytadan yuboring.", show_alert=True)
            return

        await callback.message.answer("🎧 Musiqa Shazam orqali qidirilmoqda, iltimos kuting...")
        audio_path = None
        try:
            audio_path, track_info = await get_audio_and_recognize(url)
            if audio_path and os.path.exists(audio_path):
                audio_file = types.FSInputFile(audio_path)
                await callback.message.answer_audio(
                    audio=audio_file,
                    caption=f"🎵 <b>Musiqa:</b> {track_info}\n🤖 <i>SaberPlus orqali topildi</i>"
                )
                await callback.answer("Musiqa tayyor! 🎉")
            else:
                await callback.message.answer("❌ Kechirasiz, musiqani aniqlab bo'lmadi.")
        except Exception as e:
            logging.error(f"Audio xatolik: {e}")
            await callback.message.answer(f"❌ Xatolik yuz berdi.")
        finally:
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except:
                    pass

    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("SaberPlus bot polling boshlandi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi!")
