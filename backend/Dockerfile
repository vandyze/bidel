FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

COPY packages/ /app/packages/
RUN pip install --no-cache-dir --no-index --find-links=/app/packages -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
