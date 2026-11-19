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

## دیتابیس تازه (نصب از صفر)
migrationهای قدیمی فرض می‌کنند جدول‌ها از قبل هستند. برای دیتابیس خالی: یک بار برنامه را اجرا کنید (`create_all` جدول‌ها را می‌سازد) و سپس:
```bash
cd backend && alembic stamp head && python import_data.py
```
برای دیتابیس موجود همان `alembic upgrade head` (در `upload.sh`) کافی است.

## نشست‌ها
توکن ورود یک سال اعتبار دارد و فرانت روزی یک‌بار آن را تمدید می‌کند (`POST /auth/refresh`)؛ بنابراین استفادهٔ منظم، نشست را عملاً ماندگار نگه می‌دارد.
خروج (`/auth/logout`)، تغییر رمز و بازیابی رمز با بالا بردن `users.token_version` همهٔ توکن‌های قبلی کاربر را باطل می‌کنند.

## HTTPS
تنظیم nginx در `server_setup.sh` فقط پورت ۸۰ را دارد. اگر TLS را خود سرور می‌بندد:
`sudo apt install certbot python3-certbot-nginx && sudo certbot --nginx -d bideli.ir -d www.bideli.ir`
(certbot ریدایرکت ۸۰←۴۴۳ را هم اضافه می‌کند). اگر پشت CDN است، همان‌جا فعال کنید.

## حالت آفلاین
service worker صفحهٔ اصلی و پاسخ شعرهایی را که کاربر دیده کش می‌کند (حداکثر ۴۰۰ مورد)؛ مسیرهای کاربری هرگز کش نمی‌شوند.
