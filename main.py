import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ----------------------------------------------------
# 1. إعداد السجلات (Logging)
# ----------------------------------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# التوكين الخاص بك مضاف هنا بشكل مباشر ومحمي
TOKEN = "8683431048:AAEVfzSCrimFwy10eumlterTffgG2o_2lOM"


# ----------------------------------------------------
# 2. أمر البداية /start
# ----------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("قسم الأسئلة ❓", callback_data='faq'),
            InlineKeyboardButton("الدعم الفني 🛠️", callback_data='support')
        ],
        [
            InlineKeyboardButton("حول البوت ℹ️", callback_data='about')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "أهلاً بك! يرجى اختيار أحد الخيارات من القائمة أدناه:",
        reply_markup=reply_markup
    )


# ----------------------------------------------------
# 3. معالج أزرار القائمة (Callback Queries)
# ----------------------------------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    # خيار الأسئلة الشائعة
    if query.data == 'faq':
        keyboard = [
            [InlineKeyboardButton("رجوع 🔙", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="قسم الأسئلة الشائعة:\n\n1. كيف أستخدم البوت؟\n2. ما هي الخدمات المتاحة؟",
            reply_markup=reply_markup
        )

    # خيار الدعم الفني
    elif query.data == 'support':
        keyboard = [
            [InlineKeyboardButton("رجوع 🔙", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="للتواصل مع الدعم الفني، يرجى مراسلة المسؤول مباشرة.",
            reply_markup=reply_markup
        )

    # خيار حول البوت
    elif query.data == 'about':
        keyboard = [
            [InlineKeyboardButton("رجوع 🔙", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="هذا البوت تم تطويره لتسهيل تقديم الخدمات والتواصل السريع.",
            reply_markup=reply_markup
        )

    # العودة للقائمة الرئيسية
    elif query.data == 'main_menu':
        keyboard = [
            [
                InlineKeyboardButton("قسم الأسئلة ❓", callback_data='faq'),
                InlineKeyboardButton("الدعم الفني 🛠️", callback_data='support')
            ],
            [
                InlineKeyboardButton("حول البوت ℹ️", callback_data='about')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="أهلاً بك! يرجى اختيار أحد الخيارات من القائمة أدناه:",
            reply_markup=reply_markup
        )


# ----------------------------------------------------
# 4. التشغيل الرئيسي للبوت (Main Function)
# ----------------------------------------------------
def main() -> None:
    # إنشاء تطبيق البوت
    app = ApplicationBuilder().token(TOKEN).build()

    # إضافة المعالجات (Handlers)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # بدء تشغيل البوت
    print("البوت يعمل الآن...")
    app.run_polling()


# ----------------------------------------------------
# 5. نقطة انطلاق البرنامج
# ----------------------------------------------------
if __name__ == '__main__':
    main()
