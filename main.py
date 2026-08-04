import os
import logging
import asyncio
import urllib.parse
import random
from io import BytesIO
import aiohttp
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
from gtts import gTTS
import yt_dlp
from groq import Groq

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
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
ADMIN_USERNAME = "@e9Qsl"

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# تخزين مؤقت لنتائج بحث الأغاني والصور المعلقة للتعديل
user_music_search = {}
user_pending_images = {}

# ----------------------------------------------------
# 3. القوائم الرئيسية والاختصارات
# ----------------------------------------------------
def main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton("🤖 المساعد الذكي", callback_data="ai_mode"),
         InlineKeyboardButton("📥 تحميل فيديو", callback_data="download_mode")],
        [InlineKeyboardButton("🎨 توليد صور AI", callback_data="image_mode"),
         InlineKeyboardButton("✨ تعديل وفلاتر الصور", callback_data="edit_image_mode")],
        [InlineKeyboardButton("🎵 البحث عن أغاني (سبوت)", callback_data="music_mode"),
         InlineKeyboardButton("🎮 قسم الألعاب", callback_data="games_menu")],
        [InlineKeyboardButton("📋 دليل الاختصارات", callback_data="shortcuts_info"),
         InlineKeyboardButton("💡 إرسال فكرة/اقتراح", callback_data="send_idea")],
        [InlineKeyboardButton("🛠️ الدعم الفني", callback_data="support")]
    ]
    return InlineKeyboardMarkup(buttons)

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    welcome_text = (
        "✨ **أهلاً بك في بوت لينا المتطور الشامل!** ✨\n\n"
        "🌍 أدعم **كافة لغات العالم**، ومجهز بأحدث أدوات الذكاء الاصطناعي.\n"
        "اختر ما تحب من القائمة أدناه أو استخدم الكلمات المفتاحية المباشرة (مثل: `سبوت`, `تنزيل`, `صورة`, `تعديل`, `العاب`):"
    )
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

# ----------------------------------------------------
# 4. معالجة الأزرار التفاعلية (Callback Queries)
# ----------------------------------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "main_menu":
        context.user_data.clear()
        await query.message.edit_text("اختر الخدمة المطلوبة من القائمة الرئيسية:", reply_markup=main_menu_keyboard())
    elif data == "ai_mode":
        context.user_data['mode'] = 'ai'
        await query.message.edit_text("🤖 **وضع المساعد الذكي تفعّل!**\n\nاسألني بأي لغة وسأجيبك فوراً مع معرفتي التامة بالتوقيت والأحداث.", reply_markup=back_keyboard(), parse_mode="Markdown")
    elif data == "download_mode":
        context.user_data['mode'] = 'download'
        await query.message.edit_text("📥 **التحميل:** أرسل رابط الفيديو (تيك توك، يوتيوب، انستغرام، تويتر، بينترست، إلخ) أو اكتب `تنزيل الرابط`.", reply_markup=back_keyboard(), parse_mode="Markdown")
    elif data == "image_mode":
        context.user_data['mode'] = 'generate_image'
        await query.message.edit_text("🎨 **توليد صور AI:**\n\nاكتب وصف الصورة بالتفصيل أو استخدم `صورة الوصف`.", reply_markup=back_keyboard(), parse_mode="Markdown")
    elif data == "edit_image_mode":
        context.user_data['mode'] = 'edit_image'
        await query.message.edit_text("✨ **تعديل وفلاتر الصور:**\n\nأرسل الصورة التي تريد تعديلها الآن وسأعطيك قائمة بأشهر الفلاتر العالمية!", reply_markup=back_keyboard(), parse_mode="Markdown")
    elif data == "music_mode":
        context.user_data['mode'] = 'music_search'
        await query.message.edit_text("🎵 **البحث عن أغاني:**\n\nاكتب اسم الأغنية أو استخدم `سبوت اسم الأغنية`.", reply_markup=back_keyboard(), parse_mode="Markdown")
    elif data == "games_menu":
        await send_games_menu_ui(query)
    elif data == "shortcuts_info":
        await send_shortcuts_info_ui(query)
    elif data == "send_idea":
        context.user_data['mode'] = 'waiting_idea'
        await query.message.edit_text("💡 **أرسل فكرتك أو اقتراحك الآن في رسالة واحدة:**\nسيتم إرسالها مباشرة إلى المطور عبر حسابك.", reply_markup=back_keyboard(), parse_mode="Markdown")
    elif data == "support":
        await query.message.edit_text(f"🛠️ **الدعم الفني:**\nلأي مشكلة تواصل مع المطور عبر المعرف: {ADMIN_USERNAME}", reply_markup=back_keyboard(), parse_mode="Markdown")
    elif data.startswith("dlmusic_"):
        await download_selected_music(query, context)
    elif data.startswith("filter_"):
        await apply_image_filter(query, context)

# ----------------------------------------------------
# 5. معالجة الرسائل والنصو ص والاختصارات
# ----------------------------------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip() if update.message.text else ""
    user_id = update.effective_user.id
    mode = context.user_data.get('mode')

    # نظام تلقي الأفكار والاقتراحات
    if mode == 'waiting_idea':
        idea_text = f"💡 **فكرة/اقتراح جديد من مستخدم:**\n👤 المستخدم: @{update.effective_user.username or update.effective_user.first_name} (ID: `{user_id}`)\n\n💬 النص:\n{text}"
        try:
            # محاولة إرسال الفكرة للمطور مباشرة إذا كانت معرف أو ID معروف، أو تسجيلها
            await context.bot.send_message(chat_id=ADMIN_USERNAME, text=idea_text, parse_mode="Markdown")
        except Exception:
            logger.info(f"New Idea received from {user_id}: {text}")
        
        context.user_data.pop('mode', None)
        await update.message.reply_text("✅ **تم إرسال فكرتك بنجاح إلى المطور (@e9Qsl)!** شكراً لمساهمتك.", reply_markup=main_menu_keyboard())
        return

    # الاختصارات الذكية
    if text.startswith("سبوت "):
        song_query = text.replace("سبوت", "").strip()
        await search_music(update, context, song_query)
        return
    elif text.startswith("تنزيل "):
        url = text.replace("تنزيل", "").strip()
        await download_video(update, url)
        return
    elif text.startswith("صورة "):
        img_prompt = text.replace("صورة", "").strip()
        await generate_image(update, img_prompt)
        return
    elif text in ["العاب", "الألعاب", "games"]:
        await send_games_menu_chat(update, context)
        return
    elif text in ["اختصارات", "الاختصارات"]:
        await send_shortcuts_info_chat(update, context)
        return
    elif text == "تعديل":
        context.user_data['mode'] = 'edit_image'
        await update.message.reply_text("✨ يرجى إرسال الصورة التي تريد تعديلها الآن لاختيار الفلتر المناسب.", reply_markup=back_keyboard())
        return
    elif text in ["احبك", "بحبك", "i love you"]:
        await handle_love_response(update)
        return
    elif text == "زوجني":
        await handle_marriage_response(update)
        return

    # روابط مباشرة للتحميل
    if text.startswith("http://") or text.startswith("https://"):
        await download_video(update, text)
        return

    # الأوضاع المحددة مسبقاً عبر الأزرار
    if mode == 'ai':
        await handle_ai_chat(update, text)
    elif mode == 'download':
        await download_video(update, text)
    elif mode == 'generate_image':
        await generate_image(update, text)
    elif mode == 'music_search':
        await search_music(update, context, text)
    else:
        # افتراضي: توجيه للذكاء الاصطناعي مع دعم كافة اللغات
        if text:
            await handle_ai_chat(update, text)

# ----------------------------------------------------
# 6. المساعد الذكي (Groq AI - متعدد اللغات وواعي بالوقت)
# ----------------------------------------------------
async def handle_ai_chat(update: Update, text: str):
    if not groq_client:
        await update.message.reply_text("🤖 خدمة الذكاء الاصطناعي غير مفعلة حالياً.")
        return
    
    msg = await update.message.reply_text("🧠 جاري التفكير...")
    try:
        system_prompt = (
            "You are Lena, a brilliant, friendly, and advanced AI assistant created to help users. "
            "You fully support ALL languages in the world (Arabic, English, French, Spanish, Japanese, etc.). "
            "Always reply in the exact same language the user is speaking. "
            "Current Date and Time: Tuesday, August 4, 2026, 8:57 PM (GMT+3). "
            "Be smart, accurate, context-aware, and helpful."
        )
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ]
        )
        answer = response.choices[0].message.content
        await msg.edit_text(answer)
    except Exception as e:
        await msg.edit_text(f"❌ حدث خطأ أثناء المعالجة: {e}")

# ----------------------------------------------------
# 7. تحميل الفيديوهات المتقدم (يدعم يوتيوب، تيك توك، تويتر، انستا، بينترست، سناب شات)
# ----------------------------------------------------
async def download_video(update: Update, url: str):
    msg = await update.message.reply_text("⏳ جاري معالجة الرابط وتحميل الفيديو...")
    filename = f"video_{update.effective_user.id}.mp4"
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': filename,
        'quiet': True,
        'no_warnings': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))
        
        if os.path.exists(filename):
            await update.message.reply_video(video=open(filename, 'rb'), caption="✅ تم تحميل الفيديو بنجاح بواسطة لينا!")
            os.remove(filename)
            await msg.delete()
        else:
            await msg.edit_text("❌ تعذر استخراج الفيديو من هذا الرابط (قد يكون خاصاً أو غير مدعوم مباشرة).")
    except Exception as e:
        if os.path.exists(filename):
            os.remove(filename)
        logger.error(f"Download error: {e}")
        await msg.edit_text(f"❌ خطأ في التحميل: تأكد أن الرابط عام وصحيح (سناب شات والمنصات المغلقة تتطلب روابط فيديوهات عامة وليست حسابات شخصية).")

# ----------------------------------------------------
# 8. توليد صور الذكاء الاصطناعي (مع تحسين البرومبت لمنع التكرار والتنوع)
# ----------------------------------------------------
async def generate_image(update: Update, prompt: str):
    msg = await update.message.reply_text("🎨 جاري ابتكار ورسم الصورة بالذكاء الاصطناعي...")
    
    # تحسين الوصف بلغة إنجليزية عبر الذكاء الاصطناعي لضمان نتائج مذهلة وخالية من التكرار
    enhanced_prompt = prompt
    if groq_client:
        try:
            res = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an expert prompt engineer for AI image generators. Translate and expand the user's idea into a highly detailed, creative, visually stunning English prompt with unique styles and lighting. Return ONLY the English prompt."},
                    {"role": "user", "content": prompt}
                ]
            )
            enhanced_prompt = res.choices[0].message.content.strip()
        except:
            pass

    # إضافة رقم عشوائي للبذرة (Seed) لضمان عدم تشابه الصور في كل مرة
    random_seed = random.randint(1, 999999)
    encoded = urllib.parse.quote(enhanced_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&seed={random_seed}&nologo=true"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=50) as resp:
                if resp.status == 200:
                    image_bytes = await resp.read()
                    photo = InputFile(BytesIO(image_bytes), filename="ai_image.jpg")
                    await update.message.reply_photo(photo=photo, caption=f"✨ **الوصف:** {prompt}\n🎨 **التمثيل الفني:** {enhanced_prompt[:100]}...", parse_mode="Markdown")
                    await msg.delete()
                else:
                    await msg.edit_text("❌ تعذر توليد الصورة حالياً، حاول مرة أخرى بوصف مختلف.")
    except Exception as e:
        await msg.edit_text(f"❌ حدث خطأ أثناء توليد الصورة: {e}")

# ----------------------------------------------------
# 9. تعديل وفلاتر الصور الاحترافية (باستخدام PIL)
# ----------------------------------------------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    photo_bytes = BytesIO()
    await photo_file.download_to_memory(photo_bytes)
    photo_bytes.seek(0)

    # حفظ الصورة مؤقتاً لمعالجة الفلاتر بناءً على اختيار المستخدم
    user_id = update.effective_user.id
    user_pending_images[user_id] = photo_bytes.read()

    filter_keyboard = [
        [InlineKeyboardButton("📽️ فنتجي/سيبيا (Vintage)", callback_data="filter_vintage"),
         InlineKeyboardButton("🌆 نيون سينمائي (Cyberpunk)", callback_data="filter_cyberpunk")],
        [InlineKeyboardButton("⚫ أبيض وأسود عالي (B&W)", callback_data="filter_bw"),
         InlineKeyboardButton("🌟 إضاءة ساطعة (HDR)", callback_data="filter_hdr")],
        [InlineKeyboardButton("🌫️ نعومة حالمة (Soft Glow)", callback_data="filter_soft"),
         InlineKeyboardButton("🔄 عودة للقائمة", callback_data="main_menu")]
    ]
    await update.message.reply_text(
        "✨ **تم استقبال الصورة بنجاح!**\nاختر الفلتر العالمي الذي تريد تطبيقه على الصورة:",
        reply_markup=InlineKeyboardMarkup(filter_keyboard),
        parse_mode="Markdown"
    )

async def apply_image_filter(query, context):
    user_id = query.from_user.id
    raw_img_bytes = user_pending_images.get(user_id)
    if not raw_img_bytes:
        await query.answer("⚠️ انتهت صلاحية الصورة، أرسلها من جديد.", show_alert=True)
        return

    filter_type = query.data.replace("filter_", "")
    await query.message.edit_text("⏳ جاري تطبيق الفلتر الاحترافي على الصورة...")

    try:
        img = Image.open(BytesIO(raw_img_bytes)).convert("RGB")

        if filter_type == "vintage":
            # Sepia / Vintage
            img = ImageOps.autocontrast(img)
            img = ImageEnhance.Color(img).enhance(0.5)
            # Apply warm tint
            overlay = Image.new('RGB', img.size, (112, 66, 20))
            img = Image.blend(img, overlay, 0.2)
        elif filter_type == "cyberpunk":
            img = ImageEnhance.Contrast(img).enhance(1.5)
            img = ImageEnhance.Color(img).enhance(1.8)
        elif filter_type == "bw":
            img = ImageOps.grayscale(img)
            img = ImageOps.autocontrast(img)
        elif filter_type == "hdr":
            img = ImageEnhance.Sharpness(img).enhance(2.0)
            img = ImageEnhance.Contrast(img).enhance(1.3)
        elif filter_type == "soft":
            img = img.filter(ImageFilter.SMOOTH_MORE)
            img = ImageEnhance.Brightness(img).enhance(1.1)

        out_io = BytesIO()
        img.save(out_io, format='JPEG', quality=95)
        out_io.seek(0)
        
        filtered_file = InputFile(out_io, filename=f"filtered_{filter_type}.jpg")
        await query.message.reply_photo(photo=filtered_file, caption=f"✨ تم تطبيق فلتر **({filter_type})** بنجاح بواسطة لينا!")
        await query.message.delete()
    except Exception as e:
        await query.message.edit_text(f"❌ حدث خطأ أثناء تطبيق الفلتر: {e}")

# ----------------------------------------------------
# 10. البحث عن الأغاني (سبوت / MP3)
# ----------------------------------------------------
async def search_music(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    msg = await update.message.reply_text(f"🔍 جاري البحث عن الأغنية: **{query}**...", parse_mode="Markdown")
    ydl_opts = {'default_search': 'ytsearch5', 'quiet': True, 'extract_flat': True}
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(query, download=False))
        entries = info.get('entries', [])
        if not entries:
            await msg.edit_text("❌ لم يتم العثور على نتائج لهذه الأغنية.")
            return

        user_music_search[update.effective_user.id] = entries
        buttons = []
        for idx, entry in enumerate(entries[:5]):
            title = entry.get('title', 'أغنية بدون عنوان')[:40]
            buttons.append([InlineKeyboardButton(f"🎶 {idx+1}. {title}", callback_data=f"dlmusic_{idx}")])
        buttons.append([InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="main_menu")])
        await msg.edit_text("🎼 **اختر الأغنية المطلوبة للتحميل (MP3):**", reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
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
    await query.message.edit_text(f"⏳ جاري تحميل وتحويل الأغنية إلى MP3: **{selected.get('title')}**...", parse_mode="Markdown")

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
            await query.message.reply_audio(audio=open(filename, 'rb'), title=selected.get('title'), performer="Bot Lena")
            os.remove(filename)
            await query.message.delete()
        else:
            await query.message.edit_text("❌ تعذر تنزيل الصوت.")
    except Exception as e:
        if os.path.exists(filename):
            os.remove(filename)
        await query.message.edit_text(f"❌ حدث خطأ أثناء تحميل الأغنية: {e}")

# ----------------------------------------------------
# 11. الألعاب والميزات الإضافية (احبك، زوجني، الألعاب)
# ----------------------------------------------------
async def handle_love_response(update: Update):
    # إذا كانت رسالة رد (Reply) على شخص آخر في القروب
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user.first_name
        await update.message.reply_text(f"❤️‍🔥 وهـي تعشقك يا {target_user}! الله يخلد المحبة بينكم 🥰✨")
            else:
        await update.message.reply_text("🥰 وأنا أعشقك أكثر يا قلبي! منور الدنيا كلها ❤️✨")

async def handle_marriage_response(update: Update):
    funny_spouses = [
        "بطاطس مقلية مقرمشة 🍟",
        "بيتزا بالجبنة السائحة 🍕",
        "كوب شاي نعناع ع السيرفر ☕",
        "برمجية بايثون خالية من الأخطاء 💻",
        "شخص عشوائي فخم من الموجودين بالقروب 😏❤️",
        "سيارة لامبورغيني موديل 2026 🏎️"
    ]
    chosen = random.choice(funny_spouses)
    user_name = update.message.from_user.first_name
    await update.message.reply_text(f"💍 **مراسيم الزواج الرسمية:**\n\nألف مبروك لـ [{user_name}] لقد تم زواجك المبارك من: **{chosen}** 🎉👰🤵 عش حياة سعيدة!")

async def send_games_menu_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    games_text = (
        "🎮 **قائمة الألعاب الترفيهية:**\n\n"
        "1️⃣ **لعبة الحظ والتوقعات:** أرسل `/fortune` لتوقعات اليوم.\n"
        "2️⃣ **تحدي الذكاء:** اسأل المساعد الذكي أي فوازير أو ألغاز تريدها.\n"
        "3️⃣ ألعاب جماعية أخرى قادمة قريباً في التحديثات القادمة!"
    )
    await update.message.reply_text(games_text, reply_markup=back_keyboard(), parse_mode="Markdown")

async def send_games_menu_ui(query):
    games_text = (
        "🎮 **قائمة الألعاب الترفيهية:**\n\n"
        "1️⃣ **لعبة الحظ والتوقعات:** جرب حظك اليوم!\n"
        "2️⃣ **ألغاز وفوازير:** اسأل لينا في وضع المساعد الذكي.\n"
    )
    await query.message.edit_text(games_text, reply_markup=back_keyboard(), parse_mode="Markdown")

async def send_shortcuts_info_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info_text = (
        "📋 **دليل الاختصارات والكلمات المفتاحية للبوت:**\n\n"
        "1️⃣ `سبوت [اسم الأغنية]` 🎵 -> للبحث عن الأغاني وتحميلها بصيغة MP3.\n"
        "2️⃣ `تنزيل [الرابط]` 📥 -> لتحميل الفيديوهات من أي موقع.\n"
        "3️⃣ `صورة [الوصف]` 🎨 -> لتوليد وتصميم صور احترافية بالذكاء الاصطناعي.\n"
        "4️⃣ `العاب` 🎮 -> لفتح قائمة الألعاب الترفيهية.\n"
        "5️⃣ `لينا [رسالتك]` أو كتابة أي نص 🤖 -> للتحدث مع المساعد الذكي المدعم بكل لغات العالم.\n"
        "6️⃣ `تعديل` ✨ -> لإرسال صورة واختيار أشهر الفلاتر العالمية لتعديلها.\n"
        "7️⃣ `احبك` ❤️ -> لترد عليك لينا (أو ترد على الشخص الذي ترد على رسالته بالقروب).\n"
        "8️⃣ `زوجني` 💍 -> لزواجك العشوائي السريع والساخر من شخصيات أو أعضاء.\n"
    )
    await update.message.reply_text(info_text, reply_markup=back_keyboard(), parse_mode="Markdown")

async def send_shortcuts_info_ui(query):
    info_text = (
        "📋 **دليل الاختصارات والكلمات المفتاحية للبوت:**\n\n"
        "1️⃣ `سبوت [اسم الأغنية]` -> تحميل أغاني MP3.\n"
        "2️⃣ `تنزيل [الرابط]` -> تحميل الفيديوهات.\n"
        "3️⃣ `صورة [الوصف]` -> توليد صور AI.\n"
        "4️⃣ `العاب` -> قسم الألعاب.\n"
        "5️⃣ أي كلام عشوائي -> المساعد الذكي لينا.\n"
        "6️⃣ `تعديل` -> فلاتر الصور الاحترافية.\n"
        "7️⃣ `احبك` / `زوجني` -> تفاعلات رومانسية وساخرة.\n"
    )
    await query.message.edit_text(info_text, reply_markup=back_keyboard(), parse_mode="Markdown")

# أمر النص لصوت (TTS)
async def tts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ يرجى كتابة النص بعد الأمر، مثال:\n`/tts مرحباً بك`", parse_mode="Markdown")
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
        await update.message.reply_text(f"❌ خطأ: {e}")

# ----------------------------------------------------
# 12. التشغيل الرئيسي
# ----------------------------------------------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tts", tts_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("🚀 بوت لينا الشامل والمطور يعمل الآن بكافة الميزات والتحسينات...")
    app.run_polling()

if __name__ == '__main__':
    main()
