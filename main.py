import asyncio
import logging
import os
import json
import urllib.parse
import base64
from io import BytesIO
import aiohttp
import yt_dlp
from PIL import Image, ImageEnhance, ImageOps
from groq import AsyncGroq
from gtts import gTTS

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup, Message, 
    FSInputFile, BufferedInputFile, CallbackQuery
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ==================== البيانات الخاصة بك ====================
BOT_TOKEN = "8683431048:AAEVfzSCrimFwy10eumlterTffgG2o_2lOM"
GROQ_API_KEY = "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"

# إعداد الخدمات
groq_client = AsyncGroq(api_key=GROQ_API_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ذاكرة مؤقتة
user_music_search = {}
USERS_FILE = "bot_users.json"

# ==================== إدارة قاعدة مستخدمي البوت ====================
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_user(user_id):
    users = load_users()
    if user_id not in users:
        users.add(user_id)
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(users), f)

# ==================== حالات المستخدم ====================
class UserStates(StatesGroup):
    ai_chat = State()
    download_video = State()
    generate_image = State()
    edit_image = State()
    ocr_vision = State()
    make_pdf = State()
    text_to_speech = State()
    music_search = State()
    feedback = State()
    admin_broadcast = State()

# ==================== القوائم والأزرار ====================
def main_keyboard(user_id):
    buttons = [
        [InlineKeyboardButton(text="🤖 المساعد الذكي (جميع اللغات)", callback_data="ai_mode")],
        [InlineKeyboardButton(text="📥 تحميل فيديو (كل المنصات)", callback_data="download_mode"), 
         InlineKeyboardButton(text="🎨 توليد صور AI", callback_data="image_mode")],
        [InlineKeyboardButton(text="✨ تعديل وتحسين الصور", callback_data="edit_image_mode"),
         InlineKeyboardButton(text="🔍 استخراج النص من الصورة (OCR)", callback_data="ocr_mode")],
        [InlineKeyboardButton(text="🎵 البحث عن أغاني (MP3)", callback_data="music_mode"),
         InlineKeyboardButton(text="📄 تحويل صورة إلى PDF", callback_data="pdf_mode")],
        [InlineKeyboardButton(text="🎙️ تحويل نص إلى صوت", callback_data="tts_mode"),
         InlineKeyboardButton(text="🎮 الألعاب والتسلية", callback_data="games_mode")],
        [InlineKeyboardButton(text="📢 تقديم شكوى / إقتراح", callback_data="feedback_mode")],
        [InlineKeyboardButton(text="⚙️ لوحة تحكم الأدمن", callback_data="admin_mode")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]
    ])

def admin_keyboard():
    buttons = [
        [InlineKeyboardButton(text="📊 إحصائيات المستخدمين", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 إرسال اذاعة جماعية", callback_data="admin_broadcast_start")],
        [InlineKeyboardButton(text="🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def games_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🎲 رمي زهر", callback_data="game_dice"),
         InlineKeyboardButton(text="🎯 تصويب الهدف", callback_data="game_dart")],
        [InlineKeyboardButton(text="⚽ ركلة جزاء", callback_data="game_football"),
         InlineKeyboardButton(text="🎰 ماكينة الحظ", callback_data="game_slots")],
        [InlineKeyboardButton(text="🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ==================== الأوامر العامة ====================
@dp.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    await state.clear()
    save_user(message.from_user.id)
    
    temp_msg = await message.answer("🔄 جاري تحديث الواجهة...", reply_markup=types.ReplyKeyboardRemove())
    await temp_msg.delete()

    welcome_text = (
        f"أهلاً بك يا {message.from_user.first_name} في البوت الشامل المتطور! 🚀\n\n"
        "جميع الخدمات أدناه تعمل بكفاءة عالية، اختر ما تحتاجه:"
    )
    await message.answer(welcome_text, reply_markup=main_keyboard(message.from_user.id))

@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("اختر الخدمة المطلوبة من القائمة الرئيسية:", reply_markup=main_keyboard(callback.from_user.id))

# ==================== 1. المساعد الذكي ====================
@dp.callback_query(F.data == "ai_mode")
async def enter_ai_mode(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.ai_chat)
    text = "🤖 **وضع المساعد الذكي تفعّل!**\n\nاسألني بأي لغة تريدها (عربي، إنجليزي، فرنسي...) وسأجيبك فوراً."
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

@dp.message(UserStates.ai_chat)
async def ai_chat_handler(message: Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        chat_completion = await groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful multi-lingual assistant."},
                {"role": "user", "content": message.text}
            ],
            model="llama-3.1-8b-instant",
        )
        reply = chat_completion.choices[0].message.content
        await message.answer(reply, reply_markup=back_keyboard())
    except Exception as e:
        await message.answer(f"❌ حدث خطأ:\n`{str(e)}`", parse_mode="Markdown", reply_markup=back_keyboard())

# ==================== 2. استخراج النص من الصور (Groq Vision OCR) ====================
@dp.callback_query(F.data == "ocr_mode")
async def enter_ocr_mode(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.ocr_vision)
    text = "🔍 **وضع استخراج النصوص من الصور!**\n\nأرسل أي صورة تحتوي على كتابة (بالعربية أو الإنجليزية)، وسيقوم الذكاء الاصطناعي بفرز واستخراج الكلمات منها بدقة."
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

@dp.message(UserStates.ocr_vision, F.photo)
async def ocr_handler(message: Message):
    status_msg = await message.answer("🔍 جاري تحليل الصورة وقراءة النصوص بواسطة الذكاء الاصطناعي...")
    
    photo = message.photo[-1]
    photo_bytes = BytesIO()
    await bot.download(photo, destination=photo_bytes)
    base64_image = base64.b64encode(photo_bytes.getvalue()).decode('utf-8')

    try:
        chat_completion = await groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "استخرج كامل النصوص والمحتويات المكتوبة داخل هذه الصورة بدقة عالية وباللغة الأصليّة المكتوبة بها:"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            model="llama-3.2-11b-vision-instruct",
        )
        extracted_text = chat_completion.choices[0].message.content
        await status_msg.edit_text(f"📝 **النص المستخرج من الصورة:**\n\n{extracted_text}", parse_mode="Markdown")
    except Exception as e:
        await status_msg.edit_text(f"❌ تعذر قراءة الصورة:\n`{str(e)}`", parse_mode="Markdown")

# ==================== 3. تحويل الصور إلى PDF ====================
@dp.callback_query(F.data == "pdf_mode")
async def enter_pdf_mode(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.make_pdf)
    text = "📄 **تحويل الصور إلى ملف PDF!**\n\nأرسل الصورة التي تريد تحويلها لملف PDF الآن."
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

@dp.message(UserStates.make_pdf, F.photo)
async def pdf_handler(message: Message):
    status_msg = await message.answer("📄 جاري إنشاء ملف PDF...")
    
    photo = message.photo[-1]
    photo_bytes = BytesIO()
    await bot.download(photo, destination=photo_bytes)
    photo_bytes.seek(0)

    try:
        img = Image.open(photo_bytes)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        pdf_bytes = BytesIO()
        img.save(pdf_bytes, format='PDF', resolution=100.0)
        pdf_bytes.seek(0)

        pdf_file = BufferedInputFile(pdf_bytes.read(), filename=f"document_{message.from_user.id}.pdf")
        await bot.send_document(chat_id=message.chat.id, document=pdf_file, caption="✅ تم تحويل الصورة إلى مستند PDF بنجاح!", reply_markup=back_keyboard())
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ حدث خطأ أثناء إنشاء PDF:\n`{str(e)}`", parse_mode="Markdown")

# ==================== 4. لوحة تحكم الأدمن ====================
@dp.callback_query(F.data == "admin_mode")
async def enter_admin_mode(callback: CallbackQuery):
    text = "⚙️ **لوحة تحكم الأدمن:**\n\nيمكنك متابعة الإحصائيات وإرسال إشعار عام لجميع مستخدمي البوت."
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=admin_keyboard())

@dp.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: CallbackQuery):
    users = load_users()
    await callback.answer(f"📊 إجمالي عدد مستخدمي البوت: {len(users)} مستخدم", show_alert=True)

@dp.callback_query(F.data == "admin_broadcast_start")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.admin_broadcast)
    text = "📢 **إرسال ذاعة جماعية:**\n\nاكتب الرسالة التي تريد إرسالها لجميع المستخدمين الآن."
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

@dp.message(UserStates.admin_broadcast)
async def perform_broadcast(message: Message, state: FSMContext):
    users = load_users()
    status_msg = await message.answer(f"⏳ جاري إرسال الرسالة إلى {len(users)} مستخدم...")
    
    count = 0
    for user_id in users:
        try:
            await bot.send_message(chat_id=user_id, text=f"📢 **تنويه إداري:**\n\n{message.text}", parse_mode="Markdown")
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass

    await status_msg.edit_text(f"✅ تم إرسال الإذاعة بنجاح إلى {count} مستخدم!", reply_markup=back_keyboard())
    await state.clear()

# ==================== 5. تحميل الفيديو والصور ====================
@dp.callback_query(F.data == "download_mode")
async def enter_download_mode(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.download_video)
    text = (
        "📥 **تنزيل الوسائط الشامل!**\n\n"
        "أرسل رابط المقطع أو الصورة من:\n"
        "• YouTube / Shorts\n• TikTok\n• Instagram\n• Snapchat\n• Pinterest\n• Twitter / X"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

@dp.message(UserStates.download_video)
async def download_video_handler(message: Message):
    url = message.text.strip()
    if not url.startswith("http"):
        await message.answer("⚠️ يرجى إرسال رابط صحيح يبدأ بـ http/https", reply_markup=back_keyboard())
        return

    status_msg = await message.answer("⏳ جاري المعالجة والتحميل...")
    output_filename = f"media_{message.from_user.id}.%(ext)s"

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_filename,
        'quiet': True,
        'max_filesize': 50 * 1024 * 1024,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }

    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=True))
        filename = yt_dlp.YoutubeDL(ydl_opts).prepare_filename(info)

        if os.path.exists(filename):
            media_file = FSInputFile(filename)
            if filename.endswith(('.jpg', '.png', '.webp', '.jpeg')):
                await bot.send_photo(chat_id=message.chat.id, photo=media_file, caption="✅ تم التحميل بنجاح!")
            else:
                await bot.send_video(chat_id=message.chat.id, video=media_file, caption="✅ تم التحميل بنجاح!")
            
            os.remove(filename)
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ لم نتمكن من العثور على الملف.")
    except Exception as e:
        await status_msg.edit_text(f"❌ حدث خطأ أثناء التحميل:\n`{str(e)}`", parse_mode="Markdown")

# ==================== 6. توليد الصور ====================
@dp.callback_query(F.data == "image_mode")
async def enter_image_mode(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.generate_image)
    text = "🎨 **توليد الصور بالذكاء الاصطناعي!**\n\nاكتب وصف الصورة بالتفصيل."
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

@dp.message(UserStates.generate_image)
async def generate_image_handler(message: Message):
    status_msg = await message.answer("🎨 جاري رسم الصورة...")
    encoded_prompt = urllib.parse.quote(message.text)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url, timeout=45) as resp:
                if resp.status == 200:
                    image_data = await resp.read()
                    photo_file = BufferedInputFile(image_data, filename="ai_image.jpg")
                    await bot.send_photo(chat_id=message.chat.id, photo=photo_file, caption=f"✨ **الوصف:** {message.text}", reply_markup=back_keyboard())
                    await status_msg.delete()
                else:
                    await status_msg.edit_text("❌ حدث خطأ أثناء توليد الصورة.")
    except Exception as e:
        await status_msg.edit_text(f"❌ تعذر توليد الصورة:\n`{str(e)}`", parse_mode="Markdown")

# ==================== 7. تعديل وتحسين الصور ====================
@dp.callback_query(F.data == "edit_image_mode")
async def enter_edit_image_mode(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.edit_image)
    text = "✨ **تعديل وتحسين الصور!**\n\nأرسل الصورة الآن لتحسين ألوانها ووضوحها تلقائياً."
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

@dp.message(UserStates.edit_image, F.photo)
async def edit_image_handler(message: Message):
    status_msg = await message.answer("🛠️ جاري تعديل وتحسين ألوان الصورة...")
    
    photo = message.photo[-1]
    photo_bytes = BytesIO()
    await bot.download(photo, destination=photo_bytes)
    photo_bytes.seek(0)

    try:
        img = Image.open(photo_bytes)
        img = ImageOps.autocontrast(img)
        img = ImageEnhance.Color(img).enhance(1.25)
        img = ImageEnhance.Sharpness(img).enhance(1.4)

        output_io = BytesIO()
        img.save(output_io, format='JPEG', quality=95)
        output_io.seek(0)

        photo_file = BufferedInputFile(output_io.read(), filename="enhanced_image.jpg")
        await bot.send_photo(chat_id=message.chat.id, photo=photo_file, caption="✨ تم تحسين وتعديل الصورة بنجاح!", reply_markup=back_keyboard())
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ حدث خطأ أثناء التعديل:\n`{str(e)}`", parse_mode="Markdown")

# ==================== 8. البحث عن الأغاني MP3 ====================
@dp.callback_query(F.data == "music_mode")
async def enter_music_mode(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.music_search)
    text = "🎵 **البحث عن الأغاني والموسيقى!**\n\nاكتب اسم الأغنية أو الفنان."
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

@dp.message(UserStates.music_search)
async def music_search_handler(message: Message):
    status_msg = await message.answer("🔍 جاري البحث...")
    query = message.text.strip()

    ydl_opts = {'default_search': 'ytsearch5', 'quiet': True, 'extract_flat': True}

    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(query, download=False))
        entries = info.get('entries', [])

        if not entries:
            await status_msg.edit_text("❌ لم يتم العثور على أي نتائج.")
            return

        user_music_search[message.from_user.id] = entries
        buttons = []
        for idx, entry in enumerate(entries[:5]):
            title = entry.get('title', 'أغنية بدون عنوان')[:35]
            buttons.append([InlineKeyboardButton(text=f"🎶 {idx+1}. {title}", callback_data=f"dlmusic_{idx}")])
        
        buttons.append([InlineKeyboardButton(text="🔙 العودة للقائمة الرئيسية", callback_data="main_menu")])
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)

        await status_msg.edit_text("🎼 اختر الأغنية لتحميلها بصيغة MP3:", reply_markup=markup)
    except Exception as e:
        await status_msg.edit_text(f"❌ حدث خطأ أثناء البحث:\n`{str(e)}`", parse_mode="Markdown")

@dp.callback_query(F.data.startswith("dlmusic_"))
async def download_selected_music(callback: CallbackQuery):
    idx = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    entries = user_music_search.get(user_id)

    if not entries or idx >= len(entries):
        await callback.answer("⚠️ انتهت الجلسة، أعد البحث.", show_alert=True)
        return

    selected = entries[idx]
    video_url = f"https://www.youtube.com/watch?v={selected['id']}"
    await callback.message.edit_text(f"⏳ جاري تنزيل: **{selected.get('title')}**...", parse_mode="Markdown")

    output_filename = f"song_{user_id}.mp3"
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_filename,
        'quiet': True,
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
    }

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([video_url]))

        if os.path.exists(output_filename):
            audio_file = FSInputFile(output_filename)
            await bot.send_audio(chat_id=callback.message.chat.id, audio=audio_file, title=selected.get('title'), reply_markup=back_keyboard())
            os.remove(output_filename)
            await callback.message.delete()
        else:
            await callback.message.edit_text("❌ تعذر استخراج الصوت.", reply_markup=back_keyboard())
    except Exception as e:
        if os.path.exists(output_filename):
            os.remove(output_filename)
        await callback.message.edit_text(f"❌ حدث خطأ:\n`{str(e)}`", parse_mode="Markdown", reply_markup=back_keyboard())

# ==================== 9. تحويل النص إلى صوت ====================
@dp.callback_query(F.data == "tts_mode")
async def enter_tts_mode(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.text_to_speech)
    text = "🎙️ **تحويل النص إلى صوت!**\n\nاكتب أي نص لتحويله لصوت."
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

@dp.message(UserStates.text_to_speech)
async def tts_handler(message: Message):
    status_msg = await message.answer("🗣️ جاري إنتاج الصوت...")
    filename = f"tts_{message.from_user.id}.mp3"
    try:
        gTTS(text=message.text, lang='ar').save(filename)
        audio_file = FSInputFile(filename)
        await bot.send_voice(chat_id=message.chat.id, voice=audio_file, reply_
