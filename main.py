import asyncio
import logging
import os
import urllib.parse
import yt_dlp
from groq import AsyncGroq
from gtts import gTTS

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ==================== البيانات الخاصة بك ====================
BOT_TOKEN = "8683431048:AAEVfzSCrimFwy10eumlterTffgG2o_2lOM"
GROQ_API_KEY = "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"

# إعداد الخدمات
groq_client = AsyncGroq(api_key=GROQ_API_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==================== حالات المستخدم ====================
class UserStates(StatesGroup):
    ai_chat = State()
    download_video = State()
    generate_image = State()
    text_to_speech = State()
    feedback = State()

# ==================== القوائم والأزرار ====================
def main_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🤖 المساعد الذكي (AI)", callback_data="ai_mode")],
        [InlineKeyboardButton(text="📥 تحميل فيديو", callback_data="download_mode"), 
         InlineKeyboardButton(text="🎨 توليد صور", callback_data="image_mode")],
        [InlineKeyboardButton(text="🎙️ تحويل نص إلى صوت", callback_data="tts_mode"),
         InlineKeyboardButton(text="🎮 الألعاب والتسلية", callback_data="games_mode")],
        [InlineKeyboardButton(text="📢 تقديم شكوى / إقتراح", callback_data="feedback_mode")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]
    ])

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
    
    # تنظيف الكيبورد القديم العالق
    temp_msg = await message.answer("🔄 جاري التحديث...", reply_markup=types.ReplyKeyboardRemove())
    await temp_msg.delete()

    welcome_text = (
        f"أهلاً بك يا {message.from_user.first_name} في البوت الشامل! 🚀\n\n"
        "جميع الخدمات جاهزة للعمل، اختر ما تريد من القائمة:"
    )
    await message.answer(welcome_text, reply_markup=main_keyboard())

@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("اختر الخدمة المطلوبة من القائمة الرئيسية:", reply_markup=main_keyboard())

# ==================== 1. المساعد الذكي ====================
@dp.callback_query(F.data == "ai_mode")
async def enter_ai_mode(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.ai_chat)
    text = "🤖 **تم تفعيل المساعد الذكي!**\n\nارسل أي سؤال أو استفسار للرد عليك فوراً."
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

@dp.message(UserStates.ai_chat)
async def ai_chat_handler(message: Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        chat_completion = await groq_client.chat.completions.create(
            messages=[{"role": "user", "content": message.text}],
            model="llama-3.1-8b-instant",
        )
        reply = chat_completion.choices[0].message.content
        await message.answer(reply, reply_markup=back_keyboard())
    except Exception as e:
        await message.answer(f"❌ حدث خطأ:\n`{str(e)}`", parse_mode="Markdown", reply_markup=back_keyboard())

# ==================== 2. تحميل الفيديو ====================
@dp.callback_query(F.data == "download_mode")
async def enter_download_mode(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.download_video)
    text = "📥 **وضع تحميل الفيديوهات!**\n\nأرسل رابط الفيديو الآن (تيك توك، انستغرام، يوتيوب...)."
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

@dp.message(UserStates.download_video)
async def download_video_handler(message: Message):
    url = message.text.strip()
    if not url.startswith("http"):
        await message.answer("⚠️ يرجى إرسال رابط صحيح يبدأ بـ http/https", reply_markup=back_keyboard())
        return

    status_msg = await message.answer("⏳ جاري معالجة وتحميل الفيديو...")
    output_filename = f"video_{message.from_user.id}.mp4"

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_filename,
        'quiet': True,
        'max_filesize': 50 * 1024 * 1024  # حد أقصى 50 ميجابايت لتليجرام
    }

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))

        if os.path.exists(output_filename):
            video_file = FSInputFile(output_filename)
            await bot.send_video(chat_id=message.chat.id, video=video_file, caption="✅ تم التحميل بنجاح!")
            os.remove(output_filename)
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ لم نتمكن من استخراج الفيديو، قد يكون الرابط غير مدعوم أو خاص.")
    except Exception as e:
        if os.path.exists(output_filename):
            os.remove(output_filename)
        await status_msg.edit_text(f"❌ حدث خطأ أثناء التحميل:\n`{str(e)}`", parse_mode="Markdown")

# ==================== 3. توليد الصور ====================
@dp.callback_query(F.data == "image_mode")
async def enter_image_mode(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.generate_image)
    text = "🎨 **وضع توليد الصور!**\n\nاكتب وصف الصورة باللغة الإنجليزية للتحسين (مثال: `a futuristic city at sunset, highly detailed`)."
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

@dp.message(UserStates.generate_image)
async def generate_image_handler(message: Message):
    status_msg = await message.answer("🎨 جاري رسم الصورة بالذكاء الاصطناعي...")
    encoded_prompt = urllib.parse.quote(message.text)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"

    try:
        await bot.send_photo(chat_id=message.chat.id, photo=image_url, caption=f"✨ الوصف: {message.text}", reply_markup=back_keyboard())
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ تعذر توليد الصورة:\n`{str(e)}`", parse_mode="Markdown")

# ==================== 4. تحويل النص إلى صوت ====================
@dp.callback_query(F.data == "tts_mode")
async def enter_tts_mode(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.text_to_speech)
    text = "🎙️ **تحويل النص إلى صوت!**\n\nاكتب النص الذي تريد تحويله إلى مقطع صوتي."
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

@dp.message(UserStates.text_to_speech)
async def tts_handler(message: Message):
    status_msg = await message.answer("🗣️ جاري إنتاج المقطع الصوتي...")
    filename = f"tts_{message.from_user.id}.mp3"
    
    try:
        tts = gTTS(text=message.text, lang='ar')
        tts.save(filename)

        audio_file = FSInputFile(filename)
        await bot.send_voice(chat_id=message.chat.id, voice=audio_file, reply_markup=back_keyboard())
        await status_msg.delete()
        os.remove(filename)
    except Exception as e:
        if os.path.exists(filename):
            os.remove(filename)
        await status_msg.edit_text(f"❌ حدث خطأ أثناء إنشاء الصوت:\n`{str(e)}`", parse_mode="Markdown")

# ==================== 5. الألعاب ====================
@dp.callback_query(F.data == "games_mode")
async def enter_games_mode(callback: types.CallbackQuery):
    text = "🎮 **قسم الألعاب والتسلية!**\n\nاختر اللعبة التفاعلية التي تود تجربتها:"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=games_keyboard())

@dp.callback_query(F.data.startswith("game_"))
async def play_game(callback: types.CallbackQuery):
    game_type = callback.data.split("_")[1]
    emoji_map = {
        "dice": "🎲",
        "dart": "🎯",
        "football": "⚽",
        "slots": "🎰"
    }
    emoji = emoji_map.get(game_type, "🎲")
    await bot.send_dice(chat_id=callback.message.chat.id, emoji=emoji)

# ==================== 6. تقديم شكوى / اقتراح ====================
@dp.callback_query(F.data == "feedback_mode")
async def enter_feedback_mode(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.feedback)
    text = "📢 **تقديم شكوى أو اقتراح!**\n\nاكتب رسالتك وسيتم توجيهها لمطور البوت مباشرة."
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

@dp.message(UserStates.feedback)
async def feedback_handler(message: Message, state: FSMContext):
    feedback_text = (
        f"📩 **رسالة جديدة من مستخدم:**\n"
        f"👤 الاسم: {message.from_user.full_name} (@{message.from_user.username})\n"
        f"🆔 الآيدي: `{message.from_user.id}`\n\n"
        f"💬 الرسالة:\n{message.text}"
    )
    # إرسال تأكيد للمستخدم
    await message.answer("✅ تم استلام رسالتك بنجاح! شكرًا لتواصلك معنا.", reply_markup=main_keyboard())
    await state.clear()

# ==================== تشغيل البوت ====================
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
