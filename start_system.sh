#!/bin/bash

# echo "Starting Redis (assuming it's managed separately or already running)..."
# redis-server & # Nếu bạn muốn script tự chạy Redis (không khuyến khích lắm)

echo "Starting Database Logger..."
# Chạy ngầm và ghi log vào file
python -m services.event_consumer > event_consumer.log 2>&1 &
EVENT_CONSUMER_PID=$!
echo "Event Consumer PID: $EVENT_CONSUMER_PID"

echo "Starting Alerter..."
python -m services.alerter > alerter.log 2>&1 &
ALERTER_PID=$!
echo "Alerter PID: $ALERTER_PID"

echo "Starting API Server (Uvicorn)..."
uvicorn services.api:app --port 8088 > api_server.log 2>&1 &
API_PID=$!
echo "API Server PID: $API_PID"

echo "System components started."
echo "Use 'kill <PID>' or 'pkill -f services.' or 'pkill -f uvicorn' to stop components."
