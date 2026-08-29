import re
import unicodedata

ZWNJ = "\u200c"

ARABIC_MAP = str.maketrans({
    "ي": "ی", "ك": "ک", "ؤ": "و", "إ": "ا", "أ": "ا", "آ": "آ",
    "ة": "ه", "ۀ": "ه",
})
DIACRITICS = re.compile(r"[\u064B-\u0652\u0670\u0640]")   # اعراب + کشیده
PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.translate(ARABIC_MAP)
    text = DIACRITICS.sub("", text)
    text = text.replace(ZWNJ, " ")
    text = PUNCT.sub(" ", text)
    text = text.translate(DIGITS)
    return re.sub(r"\s+", " ", text).strip()


STOPWORDS = {
    # حروف و ادات
    "از", "به", "با", "بر", "در", "را", "که", "چه", "تا", "هم", "نیز",
    "این", "آن", "اینک", "چون", "اگر", "ولی", "اما", "یا", "و", "ای",
    "هر", "همه", "هیچ", "چند", "کدام", "کجا", "کی", "چرا", "من", "تو",
    "او", "ما", "شما", "ایشان", "خود", "بی", "نه", "بلی", "آری", "پس",
    "زان", "کز", "کاین", "بس", "دگر", "دیگر", "یک", "دو",
}

AUX = {
    # افعال معین و پرکاربرد — واژهٔ محتوایی نیستند
    "ام", "ای", "است", "ست", "اند", "ند", "نیست", "نی", "هست", "باش",
    "باشد", "دارد", "ندارد", "دارم", "داری", "داریم", "دارند", "نبود",
    "بود", "بودیم", "شد", "شود", "شدم", "شدن", "کند", "کرد", "کن",
    "کنم", "گشت", "گردد", "می", "همی", "شو", "نگشت", "داد", "زد",
    "رفت", "آمد", "گرفت", "خواست", "ماند", "نشست", "گفت", "دهد",
    "گیرد", "رود", "توان", "خواهد", "خواهی", "دار", "گوید", "دانم",
    "دانی", "باید", "شدیم", "گشتم", "رفتم",
}

# تخلص شاعر — تقریباً در بیت آخر همهٔ ۲۸۲۷ غزل هست.
TAKHALLOS = {"بیدل"}

DROP = STOPWORDS | AUX | TAKHALLOS
MIN_TOKEN_LEN = 2


def tokenize(text: str, drop_stopwords: bool = True) -> list[str]:
    toks = normalize(text).split()
    if not drop_stopwords:
        return toks
    return [t for t in toks if len(t) >= MIN_TOKEN_LEN and t not in DROP]
