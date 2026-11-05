# 🤖 Xodimlarni baholash boti

Toshkent shahar Bosh boshqarmasi — **Bosh boshqarma bilan ishlash tashkiliy-kadrlar bo'limi xodimlarini baholash** uchun Telegram bot.

**Texnologiyalar:** Python 3.11+, aiogram 3, SQLAlchemy 2 (async), Alembic, PostgreSQL / SQLite, Docker.

## Imkoniyatlar

- 9 qadamli so'rovnoma (FSM — har bir qadam alohida holat): ism-familiya → ish joyi → xodim → funksiya → muddat bahosi + sabab → sifat bahosi + sabab → takliflar
- Har bir qadamda **⬅️ Orqaga** va **❌ Bekor qilish**, takliflar qadamida **⏭ O'tkazib yuborish**
- `/start` istalgan paytda jarayonni boshidan boshlaydi
- Validatsiya: ism-familiya kamida 2 so'z va faqat harflar (`O'ktam`, `G'ulomov` kabi tutuq belgilari ham mumkin); sabablar bo'sh bo'lmasligi kerak
- Matn o'rniga tugma (yoki aksincha) yuborilsa — xato xabari va savol qayta beriladi
- Spamdan himoya: bir foydalanuvchi bitta xodimni `FEEDBACK_COOLDOWN_HOURS` soatda bir marta baholay oladi (standart: 24, `0` — cheklovsiz)
- Admin buyruqlari: `/stats`, `/export` (Excel), `/employees` (qo'shish / faol-nofaol / o'chirish)

## Loyiha tuzilmasi

```
.
├── main.py                  # kirish nuqtasi: migratsiyalar, polling, graceful shutdown
├── alembic/                 # DB migratsiyalari (0001 — jadvallar + 3 ta standart xodim)
├── bot/
│   ├── config.py            # .env sozlamalari
│   ├── texts.py             # barcha matnlar
│   ├── states/              # FSM holatlari (Survey, AdminStates)
│   ├── keyboards/           # inline klaviaturalar va callback_data
│   ├── db/                  # modellar, engine, repo (so'rovlar)
│   ├── middlewares/db.py    # har update uchun DB sessiya
│   ├── filters/admin.py     # IsAdmin filtri (ADMIN_IDS)
│   ├── handlers/            # start, survey, admin, errors
│   └── utils/               # validatorlar, Excel eksport
└── tests/                   # pytest: validatorlar, repo, to'liq suhbat oqimi
```

## Sozlash (.env)

`.env.example` dan nusxa oling va qiymatlarni to'ldiring:

```bash
cp .env.example .env
```

| O'zgaruvchi | Tavsif |
|---|---|
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) dan olingan token |
| `ADMIN_IDS` | Admin Telegram ID lari, vergul bilan (`111,222`). ID ni [@userinfobot](https://t.me/userinfobot) orqali bilish mumkin |
| `DB_URL` | PostgreSQL: `postgresql+asyncpg://bot:bot_password@db:5432/baholash_bot`<br>SQLite: `sqlite+aiosqlite:///data/bot.db` |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | docker-compose dagi PostgreSQL uchun (DB_URL bilan mos bo'lsin) |
| `FEEDBACK_COOLDOWN_HOURS` | Qayta baholash oralig'i, soat (standart `24`) |
| `TIMEZONE` | Excel eksportdagi vaqt mintaqasi (standart `Asia/Tashkent`) |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

Namuna:

```env
BOT_TOKEN=1234567890:AAExampleTokenReplaceMe
ADMIN_IDS=111111111
DB_URL=postgresql+asyncpg://bot:bot_password@db:5432/baholash_bot
POSTGRES_DB=baholash_bot
POSTGRES_USER=bot
POSTGRES_PASSWORD=bot_password
FEEDBACK_COOLDOWN_HOURS=24
TIMEZONE=Asia/Tashkent
LOG_LEVEL=INFO
```

## Ishga tushirish

### 1-variant: Docker (PostgreSQL bilan) — tavsiya etiladi

```bash
cp .env.example .env      # BOT_TOKEN va ADMIN_IDS ni kiriting
docker compose up -d --build
docker compose logs -f bot
```

Bot ishga tushganda Alembic migratsiyalari avtomatik bajariladi va `employees` jadvaliga
3 ta standart xodim qo'shiladi. To'xtatish: `docker compose down` (ma'lumotlar `pgdata` volume'da saqlanadi).

> Docker'da SQLite ishlatmoqchi bo'lsangiz, `.env` da `DB_URL=sqlite+aiosqlite:///data/bot.db` qiling —
> fayl `botdata` volume'da saqlanadi (`db` servisi baribir ishga tushadi, lekin ishlatilmaydi).

### 2-variant: Lokal (SQLite bilan)

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # DB_URL=sqlite+aiosqlite:///data/bot.db qiling
python main.py
```

### Migratsiyalar qo'lda

```bash
alembic upgrade head                 # oxirgi versiyaga
alembic revision --autogenerate -m "o'zgarish"   # model o'zgarganda yangi migratsiya
```

## Admin buyruqlari

| Buyruq | Vazifasi |
|---|---|
| `/stats` | Jami baholashlar, ishtirokchilar soni, xodimlar bo'yicha o'rtacha ball (muddat va sifat alohida), ish joyi va funksiyalar kesimi |
| `/export` | Barcha javoblar `.xlsx` faylda |
| `/employees` | Xodimlar ro'yxati: nomini bosish — faol/nofaol; 🗑 — o'chirish (baholari bo'lsa faqat nofaol qilinadi); ➕ — yangi xodim |

Nofaol xodimlar so'rovnomada ko'rinmaydi, lekin ularning baholari statistika va eksportda qoladi.

## Testlar

```bash
pip install -r requirements-dev.txt
pytest -q
```

`tests/test_flow.py` Telegram API'ni soxta sessiya bilan almashtirib, butun suhbatni (`/start` → ... → tashakkur),
xato kiritishlarni, "Orqaga"/"Bekor qilish" tugmalarini, spam cheklovini va admin buyruqlarini tekshiradi.

## Telegram'da qo'lda tekshirish

1. `/start` → **Albatta**
2. Ism-familiya: avval `Vali` (rad etiladi), keyin `Aliyev Vali`
3. Ish joyi va xodimni tanlang; ish joyi bosqichida matn yozib ko'ring — xato xabari chiqadi
4. Funksiyada **Va boshqa** → erkin matn; **⬅️ Orqaga** ishlashini tekshiring
5. Baholar va sabablarni kiriting (sabab o'rniga tugma bossangiz — ogohlantirish chiqadi)
6. Takliflarni yozing yoki **⏭ O'tkazib yuborish** → yakuniy tashakkur xabari
7. Shu xodimni qayta baholashga urinib ko'ring — cheklov haqida xabar chiqadi
8. Admin akkauntidan: `/stats`, `/export`, `/employees`

## Eslatmalar

- FSM holatlari xotirada (`MemoryStorage`) saqlanadi: bot qayta ishga tushsa, tugallanmagan so'rovnomalarni
  `/start` bilan qaytadan boshlash kerak. Saqlangan javoblar DB da qoladi.
- Bot SIGINT/SIGTERM signallarida to'g'ri to'xtaydi: polling to'xtaydi, HTTP sessiya va DB ulanishlari yopiladi.
