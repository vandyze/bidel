FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

COPY packages/ /app/packages/
RUN pip install --no-cache-dir --no-index --find-links=/app/packages -r requirements.txt

COPY . .

# اجرا با کاربر غیر root (هم‌شناسهٔ کاربر ubuntu روی سرور تا volume قابل نوشتن بماند)
RUN useradd -u 1000 -m app 2>/dev/null || true
USER 1000

EXPOSE 8000

# فقط یک worker: کش‌های درون‌فرایندی (سلوک، ایندکس همسایه) بین worker‌ها هماهنگ نمی‌شوند
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
