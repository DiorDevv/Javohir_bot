"""Botdagi barcha matnlar (o'zbek tili, lotin yozuvi). Parse mode: HTML."""
from __future__ import annotations

# --- Tugmalar --------------------------------------------------------------
BTN_START = "Albatta"
BTN_BACK = "⬅️ Orqaga"
BTN_CANCEL = "❌ Bekor qilish"
BTN_SKIP = "⏭ O'tkazib yuborish"

# Ish joyi variantlari: kod -> nom (DB ga nom yoziladi)
WORKPLACES: dict[str, str] = {
    "city": "Toshkent shahar Bosh boshqarmasi",
    "office": "Bosh ofis",
}

# Funksiyalar: kod -> nom
FUNCTION_OTHER = "other"
FUNCTIONS: dict[str, str] = {
    "hire": "Ishga qabul qilish",
    "position": "Lavozim o'zgarishi",
    "vacation": "Ta'tillar",
    "trip": "Xizmat safari",
    "dismissal": "Ishdan bo'shatish",
    "notice": "Bildirishnomalar",
    FUNCTION_OTHER: "Va boshqa",
}
# "Va boshqa" tanlanganda DB ga "Boshqa: <matn>" ko'rinishida yoziladi
FUNCTION_OTHER_PREFIX = "Boshqa: "

SCORES: dict[int, str] = {
    1: "yomon",
    2: "qoniqarsiz",
    3: "qoniqarli",
    4: "yaxshi",
    5: "a'lo",
}

# --- Suhbat oqimi ---------------------------------------------------------
GREETING = (
    "Assalomu alaykum 👋!\n"
    "Toshkent shahar Bosh boshqarmasi\n"
    "Bosh boshqarma bilan ishlash tashkiliy-kadrlar bo'limi xodimlarini baholashni boshlaymizmi?"
)

ASK_NAME = (
    "Ajoyib! 😍 Keling tanishib olamiz. Sizga qanday murojaat qilsam bo'ladi? "
    "(Ism-familiyangizni kiriting) 🤝"
)

ASK_WORKPLACE = (
    "Iborani davom ettiring: «Men............ xodimiman.»\n\n"
    "1. Toshkent shahar Bosh boshqarmasi\n"
    "2. Bosh ofis"
)

ASK_EMPLOYEE = (
    "Iltimos, quyidagi ro'yxatdan Siz bilan ishlagan xodimni tanlang. "
    "(Siz kim bilan muloqot qildingiz?)"
)

ASK_FUNCTION = (
    "Bosh boshqarma bilan ishlash tashkiliy-kadrlar bo'limi xodimi bilan "
    "qaysi funksiya bo'yicha ishladingiz?"
)

ASK_FUNCTION_OTHER = "Iltimos, qaysi funksiya bo'yicha ishlaganingizni yozib qoldiring ✍️"

CONTINUE = "Ajoyib, unda davom ettiramiz! 🚀 🔹"

Q_TIMING = (
    "Bosh boshqarma bilan ishlash tashkiliy-kadrlar bo'limi xodimining belgilangan muddatda "
    "ishlarni bajarishidan Siz qanchalik mamnun bo'ldingiz? ✍️ Javobni tanlang"
)

Q_QUALITY = (
    "Bosh boshqarma bilan ishlash tashkiliy-kadrlar bo'limi xodimining Siz bilan ishlash "
    "jarayonidagi ish sifatini qanday baholaysiz? ✍️ Javobni tanlang"
)

ASK_REASON = "Ushbu bahoni qo'yishingizga turtki bo'luvchi sababni ko'rsating! ✍️ 🤔"

ASK_SUGGESTIONS = (
    "Bosh boshqarma bilan ishlash tashkiliy-kadrlar bo'limi faoliyatini yanada yaxshilash va "
    "xizmat sifatini oshirish bo'yicha fikr va takliflaringizni qoldiring!? 📝✨"
)

THANKS = (
    "Ishtirok etganingiz uchun tashakkur!\n"
    "Sizning fikringiz xizmatlar sifatini yaxshilashga yordam beradi.\n"
    "Agar sizda qo'shimcha mulohazalar yoki takliflar bo'lsa, albatta bizga xabar bering 😊.\n"
    "Ko'rishguncha! 👋"
)

# --- Xatolar va yordamchi xabarlar ----------------------------------------
INVALID_NAME = (
    "⚠️ Ism-familiya noto'g'ri kiritildi.\n"
    "Kamida 2 ta so'z va faqat harflardan foydalaning. Masalan: <i>Aliyev Vali</i>"
)
EMPTY_TEXT = "⚠️ Javob bo'sh bo'lmasligi kerak. Iltimos, matn yozing ✍️"
TOO_LONG = "⚠️ Matn juda uzun. Iltimos, {limit} belgidan oshirmang."
TEXT_EXPECTED = "⚠️ Bu bosqichda javobni matn ko'rinishida yozing ✍️"
TEXT_EXPECTED_ALERT = "Bu bosqichda javobni matn ko'rinishida yozing ✍️"
BUTTON_EXPECTED = "⚠️ Iltimos, quyidagi tugmalardan birini tanlang 👇"
STALE_BUTTON = "Bu tugma eskirgan. Iltimos, oxirgi xabardagi tugmalardan foydalaning 👇"
NO_ACTIVE_SURVEY = "Baholash jarayoni faol emas. Boshlash uchun /start ni bosing 🙂"
EMPLOYEE_UNAVAILABLE = "Bu xodim ro'yxatda mavjud emas. Iltimos, boshqasini tanlang."
NO_EMPLOYEES = (
    "😔 Hozircha baholash uchun xodimlar ro'yxati bo'sh.\n"
    "Iltimos, keyinroq qayta urinib ko'ring."
)
COOLDOWN_ALERT = (
    "Siz bu xodimni yaqinda baholagansiz. "
    "Bitta xodimni {hours} soatda bir marta baholash mumkin ⏳"
)
COOLDOWN_FINAL = (
    "⏳ Siz bu xodimni yaqinda baholagansiz, shuning uchun javob qayta saqlanmadi.\n"
    "Boshqa xodimni baholash uchun /start ni bosing."
)
CANCELLED = "❌ Baholash bekor qilindi.\nQaytadan boshlash uchun /start ni bosing."
SESSION_EXPIRED = "⚠️ Sessiya ma'lumotlari topilmadi. Iltimos, /start orqali qaytadan boshlang."
SAVE_ERROR = "⚠️ Javobni saqlashda xatolik yuz berdi. Iltimos, birozdan so'ng qayta yuboring."
UNEXPECTED_ERROR = "⚠️ Kutilmagan xatolik yuz berdi. Iltimos, /start orqali qaytadan urinib ko'ring."
UNEXPECTED_ERROR_SHORT = "Kutilmagan xatolik yuz berdi. Qayta urinib ko'ring."

HELP = (
    "ℹ️ <b>Yordam</b>\n\n"
    "/start — baholashni boshlash (yoki boshidan qayta boshlash)\n"
    "/cancel — joriy baholashni bekor qilish"
)
HELP_ADMIN = (
    "\n\n👮 <b>Admin buyruqlari</b>\n"
    "/stats — umumiy statistika\n"
    "/export — barcha javoblar (Excel)\n"
    "/employees — xodimlar ro'yxatini boshqarish"
)

# Bot menyusidagi buyruqlar tavsifi
CMD_START = "Baholashni boshlash"
CMD_CANCEL = "Bekor qilish"
CMD_HELP = "Yordam"
CMD_STATS = "Statistika"
CMD_EXPORT = "Excel eksport"
CMD_EMPLOYEES = "Xodimlarni boshqarish"

# --- Admin ------------------------------------------------------------------
STATS_EMPTY = "📊 Hozircha birorta ham baholash yo'q."
EXPORT_EMPTY = "📁 Eksport qilish uchun javoblar hali yo'q."
EXPORT_CAPTION = "📁 Barcha javoblar: <b>{count}</b> ta"
EXPORT_PREPARING = "⏳ Fayl tayyorlanmoqda..."

EMPLOYEES_ADMIN = (
    "👥 <b>Xodimlar ro'yxati</b>\n\n"
    "🟢 — faol, ⚪️ — nofaol (so'rovnomada ko'rinmaydi)\n"
    "• Xodim nomini bossangiz — faol/nofaol holati almashadi\n"
    "• 🗑 — butunlay o'chirish (baholari bo'lmasa)"
)
EMPLOYEES_ADMIN_EMPTY = "👥 Xodimlar ro'yxati bo'sh. ➕ tugmasi orqali qo'shing."
BTN_ADD_EMPLOYEE = "➕ Xodim qo'shish"
BTN_ADMIN_CANCEL = "❌ Bekor qilish"
ASK_NEW_EMPLOYEE = "✍️ Yangi xodimning familiya va ismini kiriting (masalan: <i>Aliyeva Malika</i>):"
EMPLOYEE_ADDED = "✅ Xodim qo'shildi: <b>{name}</b>"
EMPLOYEE_EXISTS = "⚠️ Bunday nomli xodim allaqachon mavjud: <b>{name}</b>"
EMPLOYEE_ADD_CANCELLED = "❌ Xodim qo'shish bekor qilindi."
EMPLOYEE_ACTIVATED = "🟢 {name} — faol"
EMPLOYEE_DEACTIVATED = "⚪️ {name} — nofaol"
EMPLOYEE_DELETED = "🗑 {name} o'chirildi"
EMPLOYEE_HAS_FEEDBACK = (
    "{name} bo'yicha baholar mavjud, shuning uchun u butunlay o'chirilmadi — "
    "faqat nofaol qilindi."
)
EMPLOYEE_NOT_FOUND = "Xodim topilmadi."
