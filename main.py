import asyncio
import logging
import google.generativeai as genai

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ==================== البيانات الخاصة بك ====================
BOT_TOKEN = "8683431048:AAEVfzSCrimFwy10eumlterTffgG2o_2lOM"
GEMINI_API_KEY = "AQ.Ab8RN6L57Xjrx3S1xTkw_1eCod1hP2TwL6l_RGMXXtt5xcslPA"

# إعداد الذكاء الاصطناعي
genai.configure(api_key=GEMINI_API_KEY)
ai_model = genai.GenerativeModel("gemini-1.5-flash")

# إعداد البوت
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# حالات المستخدم
class UserStates(StatesGroup):
    ai_chat = State()

# ==================== القوائم والأزرار ====================
def main_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🤖 المساعد الذكي (AI)", callback_data="ai_mode")],
        [InlineKeyboardButton(text="📥 تحميل فيديو", callback_data="download_mode"), 
         InlineKeyboardButton(text="🎨 تعديل/توليد صور", callback_data="image_mode")],
        [InlineKeyboardButton(text="🎙️ تحويل نص إلى صوت", callback_data="tts_mode"),
         InlineKeyboardButton(text="🎮 الألعاب والتسلية", callback_data="games_mode")],
        [InlineKeyboardButton(text="📢 تقديم شكوى / إقتراح", callback_data="feedback_mode")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]
    ])

# ==================== معالجة الأوامر ====================

@dp.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    await state.clear()
    welcome_text = (
        f"أهلاً بك يا {message.from_user.first_name} في البوت الشامل! 🚀\n\n"
        "اختر الخدمة التي تريدها من الأزرار أدناه:"
    )
    await message.answer(welcome_text, reply_markup=main_keyboard())

@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("اختر من القائمة الرئيسية:", reply_markup=main_keyboard())

# ==================== المساعد الذكي ====================

@dp.callback_query(F.data == "ai_mode")
async def enter_ai_mode(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.ai_chat)
    text = (
        "🤖 **تم تفعيل وضع المساعد الذكي!**\n\n"
        "اسألني أي سؤال أو تحدث معي وسيتم الرد عليك فوراً."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

@dp.message(UserStates.ai_chat)
async def ai_chat_handler(message: Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        response = ai_model.generate_content(message.text)
        await message.answer(response.text, reply_markup=back_keyboard())
    except Exception as e:
        # إرسال تفاصيل الخطأ بدقة
        await message.answer(f"❌ حدث خطأ:\n\n`{str(e)}`", parse_mode="Markdown", reply_markup=back_keyboard())

# ==================== تشغيل البوت ====================

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
