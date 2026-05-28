#!/bin/bash

BACKEND_PORT=8000
FRONTEND_PORT=3000

# پیدا کردن IP محلی
LOCAL_IP=$(hostname -I | awk '{print $1}')

# بستن پروسه‌ها هنگام خروج
cleanup(){
  echo ""
  echo "در حال بستن سرورها..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  echo "بسته شد."
  exit 0
}
trap cleanup INT TERM

# اجرای backend
echo "راه‌اندازی Backend..."
source backend/venv/bin/activate
cd backend
uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload &
BACKEND_PID=$!
cd ..

# اجرای frontend
echo "راه‌اندازی Frontend..."
cd frontend
python3 -m http.server "$FRONTEND_PORT" --bind 0.0.0.0 &
FRONTEND_PID=$!
cd ..

# کمی صبر تا سرورها بالا بیان
sleep 1

echo ""
echo "──────────────────────────────────"
echo "  Frontend:    http://${LOCAL_IP}:${FRONTEND_PORT}"
echo "  Backend API: http://${LOCAL_IP}:${BACKEND_PORT}"
echo "──────────────────────────────────"
echo "  برای خروج Ctrl+C بزنید"
echo "──────────────────────────────────"
echo ""

# منتظر ماندن
wait
