# دیوان بیدل دهلوی

سایت دیوان بیدل (bideli.ir): غزل‌ها، ترجیع‌بند، واژه‌نامه، «زند بیدل»، خوانش‌ها و پژواک‌ها.
بک‌اند FastAPI + Postgres، فرانت یک فایل `frontend/index.html`.

## راه‌اندازی محلی
```bash
./init.sh            # venv، نصب پکیج‌ها، ساخت backend/.env
./dev.sh             # بک‌اند :8000 و فرانت :3001
```
در `backend/.env` مقدارهای زیر لازم است (نمونه در `.env.example`):

| کلید | توضیح |
|---|---|
| `SECRET_KEY` | حداقل ۱۶ کاراکتر؛ بدون آن برنامه بالا نمی‌آید |
| `DATABASE_URL` | پیش‌فرض SQLite؛ روی سرور Postgres |
| `SMS_IR_API_KEY`, `SMS_IR_TEMPLATE_ID` | ارسال OTP (بدون آن کد در لاگ چاپ می‌شود) |
| `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` | اعلان ثبت‌نام (اختیاری) |

روی سرور می‌توان `POSTGRES_PASSWORD` را در `.env` ریشه تنظیم کرد.

## ادمین
فقط کاربر با `id = ADMIN_USER_ID` (در `backend/main.py`) به مسیرهای ساخت/ویرایش/حذف خوانش و پژواک و آپلود دسترسی دارد.
اسکریپت‌های `add_khanesh.sh` و `update_khanesh.sh` اطلاعات ورود را از `BIDEL_LOGIN` و `BIDEL_PASSWORD` می‌خوانند.

## تست
```bash
cd backend && pip install -r requirements-dev.txt && pytest -q
```

## دیپلوی
`./deploy.sh` ← بکاپ (`backup.sh`، نگهداری ۱۴ نسخهٔ آخر) ← `prepare.sh` ← `upload.sh` (rsync، docker-compose، `alembic upgrade head`).
`SERVER_IP` و `SERVER_USER` را می‌شود با متغیر محیطی عوض کرد. فقط **یک worker** اجرا کنید: کش سلوک و ایندکس همسایه درون‌فرایندی است.

## ساختار
- `backend/` — API، مدل‌ها، migrationها (`migrations/`)، تست‌ها (`tests/`)
- `frontend/` — سایت، service worker، فونت‌ها
- `design/` — طرح‌های پژواک و مستند سلوک
