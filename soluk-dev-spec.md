# سلوک من — داک فنی

**پروژه:** دیوان بیدل دهلوی
**Stack:** FastAPI + SQLAlchemy + PostgreSQL / Vanilla JS تک‌فایل
**نسخه:** ۱.۰

---

## ۱. خلاصه فنی

یک endpoint جدید که پروفایل مقامی کاربر رو از داده‌ی موجود (bookmarks، notes، ghazal_views، keywords) محاسبه می‌کنه، به‌علاوه یک جدول کوچک برای ثبت روزهای فعال.

**تغییر دیتابیس:** فقط **یک جدول جدید**. هیچ جدول موجودی تغییر نمی‌کنه.

---

## ۲. جدول جدید: UserActivity

### چرا لازمه

`GhazalView` برای «روزهای فعال» و «رشته» کافی نیست:

```
PK = (user_id, ghazal_id)
last_viewed_at  ← هر بازدید جدید، مقدار قبلی رو overwrite می‌کنه
```

اگه کاربر امروز غزلی رو بخونه که هفته پیش خونده، فقط `last_viewed_at` همون ردیف آپدیت می‌شه و هیچ رکورد مستقلی از «امروز» نمی‌مونه. نتیجه:
- روزهای فعال کمتر از واقعیت شمرده می‌شه
- رشته‌ی کاربر بی‌دلیل می‌شکنه

### مدل

```python
class UserActivity(Base):
    __tablename__ = "user_activity"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    date = Column(Date, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

یک ردیف در روز به‌ازای هر کاربر. حجم ناچیز.

### migration

**نیازی به Alembic نیست.** `Base.metadata.create_all()` جدول‌های جدید رو می‌سازه و به جدول‌های موجود دست نمی‌زنه. فقط ALTER روی جدول موجود بود که خطرناک می‌شد.

بعد از deploy یک بار ری‌استارت backend کافیه.

### ثبت فعالیت

یک helper که در سه نقطه صدا زده می‌شه:

```python
def touch_activity(db, user_id):
    today = date.today()
    exists = db.query(models.UserActivity).filter_by(
        user_id=user_id, date=today
    ).first()
    if not exists:
        db.add(models.UserActivity(user_id=user_id, date=today))
        db.commit()
```

نقاط فراخوانی:
- `POST /history/ghazal/{number}`
- `POST /bookmarks`
- `POST /notes`

نکته: در PostgreSQL بهتره به‌جای check-then-insert از `ON CONFLICT DO NOTHING` استفاده بشه تا race condition نداشته باشیم.

---

## ۳. الگوریتم

### ۳.۱ جمع‌آوری سیگنال‌ها

| منبع | وزن | مقام از کجا |
|---|---|---|
| `notes` | ۵ | واژه‌های داخل متن همون بیت |
| `bookmarks` | ۳ | واژه‌های داخل متن همون بیت |
| `ghazal_views` | ۱ | `GhazalKeyword` با ضرب در `count` |

بوکمارک و یادداشت روی **بیت** هستن، پس مقامشون رو از متن خود بیت درمی‌آریم نه از کل غزل. دقیق‌تره.

### ۳.۲ استخراج مقام یک بیت

```
۱. متن دو مصرع بیت رو بگیر
۲. نرمال‌سازی فارسی اعمال کن
۳. هر کدوم از ۲۲۲ واژه که در متن بود → مقامش امتیاز می‌گیره
۴. اگه هیچ واژه‌ای پیدا نشد → fallback به مقام غالب کل غزل
۵. واژه‌های با maqam == 'سایر' کاملاً حذف می‌شن
```

**نرمال‌سازی فارسی (اجباری):**
- `ي` → `ی`
- `ك` → `ک`
- حذف اعراب: `\u064B-\u0652`
- حذف `ـ` (کشیده)
- حذف نیم‌فاصله یا یکسان‌سازی با فاصله

بدون این مرحله تطبیق واژه‌ها روی متن دیوان به‌شدت ناقص می‌شه.

**بهینه‌سازی:** لیست ۲۲۲ واژه رو یک بار در حافظه با شکل نرمال‌شده cache کن. برای هر بیت به‌جای ۲۲۲ بار `in`، از یک regex ترکیبی (`|`.join) استفاده کن.

### ۳.۳ نرمال‌سازی نسبت به دیوان — بحرانی

**بدون این مرحله فیچر بی‌معنی می‌شه.** توزیع مقام‌ها در خود دیوان یکنواخت نیست؛ اگر مثلاً عشق ۳۰٪ کل واژه‌هاست، هر کاربری مقام غالبش عشق درمی‌آد و پروفایل همه شبیه هم می‌شه.

```
share_user[m] = raw[m] / Σ raw
baseline[m]   = corpus_total[m] / Σ corpus_total
index[m]      = share_user[m] / baseline[m]
radar[m]      = index[m] / max(index)      # 0..1
```

`baseline` یک بار از کل `GhazalKeyword` (join با `Keyword.maqam`) محاسبه و در حافظه‌ی پروسه cache می‌شه. با ری‌استارت دوباره ساخته می‌شه — مشکلی نیست چون فقط یک کوئری aggregate است.

اگه `baseline[m] == 0` بود، `index[m] = 0` بذار (تقسیم بر صفر).

### ۳.۴ مقام غالب

بیشترین `index`. اما اگه فاصله‌ی نفر اول و دوم کمتر از ۱۰٪ باشه، هر دو برگردونده می‌شن:

```python
if (top1 - top2) / top1 < 0.10:
    tied_with = second
```

### ۳.۵ سیر سلوک

سیگنال‌ها بر اساس `created_at` (bookmark/note) و `last_viewed_at` (view) در سطل‌های ماهانه گروه می‌شن، و برای هر ماه همون الگوریتم بالا جدا اجرا می‌شه.

- ماه‌های بدون سیگنال حذف می‌شن (نه صفر)
- اگه تعداد ماه‌ها < ۲ بود، `timeline: []` برگردون
- تاریخ‌ها میلادی برگردونده بشن (`YYYY-MM`)؛ تبدیل به شمسی کار frontend است

### ۳.۶ روزهای فعال و رشته

```sql
SELECT date FROM user_activity WHERE user_id = ? ORDER BY date
```

- `active_days` = تعداد ردیف‌ها
- `longest_streak` = بلندترین دنباله‌ی روزهای متوالی
- `current_streak` = دنباله‌ای که به امروز یا دیروز ختم می‌شه (دیروز هم قبوله تا کاربری که هنوز امروز نیومده رشته‌ش صفر نشه)

محاسبه در Python روی لیست تاریخ‌ها. تعداد ردیف‌ها کمه، کوئری پیچیده لازم نیست.

### ۳.۷ پیشنهاد غزل

از `least_maqam` (کمترین `index`):

```
غزل‌هایی که مقام غالبشون least_maqam است
  AND در ghazal_views این کاربر نیستن
  ORDER BY random
  LIMIT 3
```

اگه مقام غالب غزل‌ها از قبل محاسبه‌شده نیست، یک کوئری روی `GhazalKeyword` + `Keyword.maqam` با group by کافیه. اگه کند بود، یک بار محاسبه و در حافظه cache کن (۲۸۲۷ غزل، حجم ناچیز).

### ۳.۸ آستانه

```
signals_count = count(bookmarks) + count(notes) + count(ghazal_views)
```

کمتر از **۸** → `ready: false` و بقیه‌ی فیلدها خالی.

---

## ۴. Endpoint

```
GET /profile/soluk    ← نیاز به token
```

### پاسخ (ready = true)

```json
{
  "ready": true,
  "signals_count": 42,
  "threshold": 8,
  "radar": [
    {"id":"heyrat","label":"حیرت","value":1.0,"raw":86,"share":0.24,"baseline":0.15,"index":1.60}
  ],
  "dominant": {"id":"heyrat","label":"حیرت","tied_with":null},
  "timeline": [
    {"month":"2026-05","dominant":"talab"},
    {"month":"2026-06","dominant":"heyrat"}
  ],
  "top_words": [{"word":"آینه","count":7,"maqam":"حیرت"}],
  "highlight": {
    "poem_type":"g","poem_id":120,"couplet_index":3,
    "couplet":["مصرع اول","مصرع دوم"]
  },
  "least_maqam": {"id":"esteghna","label":"استغنا"},
  "suggestions": [{"number":812,"title":"..."}],
  "reading": {
    "ghazals_read":120,
    "active_days":34,
    "current_streak":5,
    "longest_streak":11
  }
}
```

### پاسخ (ready = false)

```json
{"ready": false, "signals_count": 3, "threshold": 8}
```

### کش

نتیجه‌ی هر کاربر با TTL ده دقیقه در یک dict در حافظه‌ی پروسه. کلید: `user_id`.
با یک worker و ۲GB RAM مشکلی نیست. اگه بعداً چند worker شد، باید به Redis منتقل بشه.

کش کاربر با هر `POST /bookmarks` یا `POST /notes` invalidate بشه تا نوار پیشرفت حالت «در حال شکل‌گیری» فوراً جلو بره.

### Endpoint دوم (برای bottom sheet)

```
GET /profile/soluk/maqam/{maqam_id}    ← نیاز به token
```

بیت‌های خود کاربر در اون مقام. با `limit` و `offset`.

---

## ۵. Frontend

### مسیرها

```
/soluk    ← صفحه اصلی
```

با History API Router موجود. Nginx تغییر نمی‌خواد چون `location /` با `try_files ... /index.html` این مسیر رو پوشش می‌ده.

### نکات پیاده‌سازی

- **Event Delegation:** کلیک روی رأس‌های رادار، chipهای واژه و کارت‌های پیشنهادی به handler سراسری اضافه بشه، نه `addEventListener` جدا
- **Loading:** `<div class="book-loader"><span></span><span></span><span></span></div>`
- **خطا:** `ctEl.innerHTML='<div class="er">خطا در محاسبه سلوک</div>'`
- **رادار:** کامپوننت Mood Radar موجود بازاستفاده بشه — پارامتری‌ش کن که هم داده‌ی غزل و هم داده‌ی کاربر رو بگیره. کد جدید ننویس
- **رنگ‌ها:** از همون آرایه `MOODS` موجود
- **تاریخ شمسی:** تبدیل `YYYY-MM` به نام ماه شمسی در frontend
- **توکن:** `localStorage` کلید `bidel_token`

### API_URL

بدون تغییر، همون الگوی موجود.

---

## ۶. Edge Caseها

| مورد | رفتار |
|---|---|
| بوکمارک روی زند | نادیده گرفته می‌شه (زند واژه‌نامه‌سازی نشده) |
| بوکمارک روی ترجیع | از `TerjeeKeyword` استفاده می‌شه |
| بیت بدون هیچ واژه‌ای | fallback به مقام غالب غزل |
| واژه با `maqam == 'سایر'` | کاملاً حذف |
| `Σ raw == 0` با وجود عبور از آستانه | `ready: false` برگردون |
| `baseline[m] == 0` | `index[m] = 0` |
| حذف بوکمارک | امتیاز کم می‌شه (محاسبه on-the-fly است) |
| کمتر از ۲ ماه داده | `timeline: []` |
| کاربر بدون توکن | ۴۰۱ |
| `least_maqam` بدون غزل نخوانده | `suggestions: []` |
| `couplet_index` خارج از محدوده (داده‌ی قدیمی) | رد شو، خطا نده |

---

## ۷. Acceptance Criteria

- [ ] جدول `user_activity` بعد از ری‌استارت backend خودکار ساخته می‌شه
- [ ] هیچ جدول موجودی تغییر نکرده
- [ ] بوکمارک، یادداشت و بازدید غزل هر سه `user_activity` رو ثبت می‌کنن
- [ ] دو بار فعالیت در یک روز فقط یک ردیف می‌سازه
- [ ] `current_streak` با فعالیت دیروز صفر نمی‌شه
- [ ] دو کاربر با ذائقه‌ی متفاوت، مقام غالب متفاوت می‌گیرن (تست نرمال‌سازی baseline)
- [ ] تطبیق واژه روی متنی با `ي` و `ك` عربی درست کار می‌کنه
- [ ] کاربر با ۷ سیگنال → `ready: false` با `signals_count: 7`
- [ ] پس از افزودن بوکمارک، `signals_count` بلافاصله آپدیت می‌شه (کش invalidate)
- [ ] پاسخ endpoint زیر ۸۰۰ms برای کاربری با ۲۰۰ بوکمارک و ۵۰۰ بازدید
- [ ] غزل‌های پیشنهادی قبلاً خوانده نشده‌ان
- [ ] بدون توکن → ۴۰۱

---

## ۸. ترتیب پیاده‌سازی

۱. مدل `UserActivity` + helper `touch_activity` + وصل کردن به سه endpoint موجود
۲. ماژول نرمال‌سازی فارسی + تطبیق واژه با متن بیت
۳. محاسبه `baseline` دیوان + cache
۴. تابع اصلی محاسبه‌ی پروفایل
۵. `GET /profile/soluk` + کش
۶. `GET /profile/soluk/maqam/{id}`
۷. Frontend: مسیر `/soluk` + بازاستفاده از رادار
۸. Frontend: کارت پروفایل + حالت در حال شکل‌گیری

## ۹. Deploy

```
./backup.sh
./prepare.sh
./upload.sh
```

بدون اسکریپت import اضافه. فقط ری‌استارت backend برای ساخته شدن جدول جدید.
