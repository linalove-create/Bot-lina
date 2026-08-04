import os
import logging
import asyncio
import urllib.parse
from io import BytesIO
import aiohttp
from PIL import Image, ImageEnhance, ImageOps
from gtts import gTTS
import yt_dlp
from groq import Groq

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ----------------------------------------------------
# 1. إعداد السجلات (Logging)
# ----------------------------------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----------------------------------------------------
# 2. الإعدادات والتوكينات
# ----------------------------------------------------
TOKEN = "8683431048:AAEVfzSCrimFwy10eumlterTffgG2o_2lOM"
GROQ_API_KEY = "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"

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# تخزين مؤقت لنتائج بحث الأغاني لكل مستخدم
user_music_search = {}

# ----------------------------------------------------
# 3. القائمة الرئيسية والميزات
# ----------------------------------------------------
def main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton("🤖 المساعد الذكي", callback_data="ai_mode"),
         InlineKeyboardButton("📥 تحميل فيديو", callback_data="download_mode")],
        [InlineKeyboardButton("🎨 توليد صور AI", callback_data="image_mode"),
         InlineKeyboardButton("✨ تحسين الصور", callback_data="edit_image_mode")],
        [InlineKeyboardButton("🎵 البحث عن أغاني (MP3)", callback_data="music_mode"),
         InlineKeyboardButton("📄 تحويل صورة لـ PDF", callback_data="pdf_mode")],
        [InlineKeyboardButton("🎙️ تحويل نص لصوت", callback_data="tts_help"),
         InlineKeyboardButton("🛠️ الدعم الفني", callback_data="support")]
    ]
    return InlineKeyboardMarkup(buttons)

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    welcome_text = (
        "✨ **أهلاً بك في بوت لينا المتطور!** ✨\n\n"
        "اختر الخدمة المطلوبة من القائمة أدناه أو أرسل رابطاً للتحميل مباشرة:"
    )
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

# ----------------------------------------------------
# 4. معالجة الأزرار والقوائم
# ----------------------------------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    context.user_data.clear()

    if data == "main_menu":
        await query.message.edit_text("اختر الخدمة المطلوبة من القائمة الرئيسية:", reply_markup=main_menu_keyboard())
    elif data == "ai_mode":
        context.user_data['mode'] = 'ai'
        await query.message.edit_text("🤖 **وضع المساعد الذكي تفعّل!**\n\nاسألني بأي سؤال وسأجيبك فوراً.", reply_markup=back_keyboard(), parse_mode="Markdown")
    elif data == "download_mode":
        context.user_data['mode'] = 'download'
        await query.message.edit_text("📥 **أرسل رابط المقطع** (يوتيوب، تيك توك، انستغرام، إلخ).", reply_markup=back_keyboard(), parse_mode="Markdown")
    elif data == "image_mode":
        context.user_data['mode'] = 'generate_image'
        await query.message.edit_text("🎨 **توليد الصور:**\n\nاكتب وصف الصورة بالتفصيل وسأقوم برسمها لك.", reply_markup=back_keyboard(), parse_mode="Markdown")
    elif data == "edit_image_mode":
        context.user_data['mode'] = 'edit_image'
        await query.message.edit_text("✨ **تحسين الصور:**\n\nأرسل الصورة التي تريد تعديلها وتحسين جودتها.", reply_markup=back_keyboard(), parse_mode="Markdown")
    elif data == "music_mode":
        context.user_data['mode'] = 'music_search'
        await query.message.edit_text("🎵 **البحث عن أغاني:**\n\nاكتب اسم الأغنية أو الفنان للبحث عنها.", reply_markup=back_keyboard(), parse_mode="Markdown")
    elif data == "pdf_mode":
        context.user_data['mode'] = 'make_pdf'
        await query.message.edit_text("📄 **تحويل الصور إلى PDF:**\n\nأرسل الصورة لتحويلها مباشرة إلى ملف PDF.", reply_markup=back_keyboard(), parse_mode="Markdown")
    elif data == "tts_help":
        await query.message.edit_text("🎙️ **تحويل النص لصوت:**\n\nاستخدم الأمر `/tts` متبوعاً بالنص.\nمثال: `/tts مرحبا بك`", reply_markup=back_keyboard(), parse_mode="Markdown")
    elif data == "support":
        await query.message.edit_text("🛠️ **الدعم الفني:**\n\nلأي استفسار تواصل مع المطور.", reply_markup=back_keyboard(), parse_mode="Markdown")
    elif data.startswith("dlmusic_"):
        await download_selected_music(query, context)

# ----------------------------------------------------
# 5. الوظائف والخدمات المتقدمة
# ----------------------------------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip() if update.message.text else ""
    mode = context.user_data.get('mode')

    # إذا أرسل رابطاً مباشراً بدون وضع محدد
    if text.startswith("http://") or text.startswith("https://"):
        await download_video(update, text)
        return

    if mode == 'ai':
        await handle_ai_chat(update, text)
    elif mode == 'download':
        if text.startswith("http"):
            await download_video(update, text)
        else:
            await update.message.reply_text("⚠️ يرجى إرسال رابط صحيح يبدأ بـ http", reply_markup=back_keyboard())
    elif mode == 'generate_image':
        await generate_image(update, text)
    elif mode == 'music_search':
        await search_music(update, context, text)
    else:
        # افتراضي: إذا كتب نصاً عادياً يتحول للذكاء الاصطناعي مباشرة
        if text:
            await handle_ai_chat(update, text)

# ميزة الذكاء الاصطناعي
async def handle_ai_chat(update: Update, text: str):
    if not groq_client:
        await update.message.reply_text("🤖 خدمة الذكاء الاصطناعي غير مفعلة.")
        return
    msg = await update.message.reply_text("🧠 جاري التفكير...")
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "أنت مساعد ذكي ولطيف اسمك لينا، تجيب باللغة العربية."},
                {"role": "user", "content": text}
            ]
        )
        await msg.edit_text(response.choices[0].message.content)
    except Exception as e:
        await msg.edit_text(f"❌ حدث خطأ: {e}")

# ميزة تنزيل الفيديوهات
async def download_video(update: Update, url: str):
    msg = await update.message.reply_text("⏳ جاري تحميل الفيديو...")
    filename = f"video_{update.effective_user.id}.mp4"
    ydl_opts = {'format': 'best[ext=mp4]/best', 'outtmpl': filename, 'quiet': True}
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))
        if os.path.exists(filename):
            await update.message.reply_video(video=open(filename, 'rb'), caption="✅ تم التحميل بنجاح!")
            os.remove(filename)
            await msg.delete()
        else:
            await msg.edit_text("❌ تعذر تحميل الفيديو.")
    except Exception as e:
        if os.path.exists(filename):
            os.remove(filename)
        await msg.edit_text(f"❌ خطأ في التحميل: {e}")

# ميزة توليد الصور
async def generate_image(update: Update, prompt: str):
    msg = await update.message.reply_text("🎨 جاري رسم الصورة...")
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=45) as resp:
                if resp.status == 200:
                    image_bytes = await resp.read()
                    photo = BufferedInputFile(image_bytes, filename="ai.jpg")
                    await update.message.reply_photo(photo=photo, caption=f"✨ الوصف: {prompt}")
                    await msg.delete()
                else:
                    await msg.edit_text("❌ تعذر توليد الصورة.")
    except Exception as e:
        await msg.edit_text(f"❌ حدث خطأ: {e}")

# معالجة الصور المرسلة (تحسين أو تحويل لـ PDF)
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get('mode')
    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    photo_bytes = BytesIO()
    await photo_file.download_to_memory(photo_bytes)
    photo_bytes.seek(0)

    if mode == 'edit_image':
        msg = await update.message.reply_text("🛠️ جاري تحسين الصورة...")
        try:
            img = Image.open(photo_bytes)
            img = ImageOps.autocontrast(img)
            img = ImageEnhance.Color(img).enhance(1.2)
            img = ImageEnhance.Sharpness(img).enhance(1.3)
            out_io = BytesIO()
            img.save(out_io, format='JPEG', quality=95)
            out_io.seek(0)
            buffered_file = BufferedInputFile(out_io.read(), filename="enhanced.jpg")
            await update.message.reply_photo(photo=buffered_file, caption="✨ تم تحسين جودة الصورة بنجاح!")
            await msg.delete()
        except Exception as e:
            await msg.edit_text(f"❌ خطأ في المعالجة: {e}")

    elif mode == 'make_pdf':
        msg = await update.message.reply_text("📄 جاري تحويل الصورة إلى PDF...")
        try:
            img = Image.open(photo_bytes).convert('RGB')
            pdf_io = BytesIO()
            img.save(pdf_io, format='PDF')
            pdf_io.seek(0)
            pdf_file = BufferedInputFile(pdf_io.read(), filename="document.pdf")
            await update.message.reply_document(document=pdf_file, caption="✅ تم التحويل إلى PDF بنجاح!")
            await msg.delete()
        except Exception as e:
            await msg.edit_text(f"❌ خطأ في التحويل: {e}")
    else:
        await update.message.reply_text("⚠️ يرجى اختيار وضع (تحسين الصور) أو (تحويل لـ PDF) من القائمة أولاً.")

# البحث عن الأغاني
async def search_music(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    msg = await update.message.reply_text("🔍 جاري البحث عن الأغنية...")
    ydl_opts = {'default_search': 'ytsearch5', 'quiet': True, 'extract_flat': True}
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(query, download=False))
        entries = info.get('entries', [])
        if not entries:
            await msg.edit_text("❌ لم يتم العثور على نتائج.")
            return

        user_music_search[update.effective_user.id] = entries
        buttons = []
        for idx, entry in enumerate(entries[:5]):
            title = entry.get('title', 'أغنية')[:35]
            buttons.append([InlineKeyboardButton(f"🎶 {idx+1}. {title}", callback_data=f"dlmusic_{idx}")])
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")])
        await msg.edit_text("🎼 اختر الأغنية المطلوبة للتحميل:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await msg.edit_text(f"❌ خطأ في البحث: {e}")

async def download_selected_music(query, context):
    idx = int(query.data.split("_")[1])
    user_id = query.from_user.id
    entries = user_music_search.get(user_id)
    if not entries or idx >= len(entries):
        await query.answer("⚠️ انتهت صلاحية البحث، أعد البحث من جديد.", show_alert=True)
        return

    selected = entries[idx]
    video_url = f"https://www.youtube.com/watch?v={selected['id']}"
    await query.message.edit_text(f"⏳ جاري تحميل الأغنية: **{selected.get('title')}**...", parse_mode="Markdown")

    filename = f"song_{user_id}.mp3"
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': filename,
        'quiet': True,
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
    }
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([video_url]))
        if os.path.exists(filename):
            await query.message.reply_audio(audio=open(filename, 'rb'), title=selected.get('title'))
            os.remove(filename)
            await query.message.delete()
        else:
            await query.message.edit_text("❌ تعذر تنزيل الصوت.")
    except Exception as e:
        if os.path.exists(filename):
            os.remove(filename)
        await query.message.edit_text(f"❌ حدث خطأ: {e}")

# أمر تحويل النص لصوت
async def tts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ يرجى كتابة النص بعد الأمر، مثال:\n`/tts مرحبا`", parse_mode="Markdown")
        return
    msg = await update.message.reply_text("🎙️ جاري توليد الصوت...")
    filename = f"tts_{update.effective_user.id}.mp3"
    try:
        gTTS(text=text, lang='ar').save(filename)
        await update.message.reply_voice(voice=open(filename, 'rb'))
        os.remove(filename)
        await msg.delete()
    except Exception as e:
        if os.path.exists(filename):
            os.remove(filename)
        await msg.edit_text(f"❌ خطأ: {e}")

# ----------------------------------------------------
# 6. التشغيل الرئيسي
# ----------------------------------------------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tts", tts_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("🚀 بوت لينا الشامل بكافة الميزات يعمل الآن...")
    app.run_polling()

if __name__ == '__main__':
    main()
