#!/bin/bash
# ADS-Modbus Gateway control script
# Usage:
#   ./gateway.sh start       Start gateway in background
#   ./gateway.sh stop        Stop gateway
#   ./gateway.sh restart     Restart gateway
#   ./gateway.sh status      Check if running
#   ./gateway.sh log         Tail live logs

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="${APP_DIR}/venv/bin/activate"
PID_FILE="${APP_DIR}/.gateway.pid"
LOG_DIR="${APP_DIR}/logs"
LOG_FILE="${LOG_DIR}/gateway.log"

mkdir -p "$LOG_DIR"

start() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Gateway already running (PID $(cat "$PID_FILE"))"
        return 1
    fi

    echo "Starting ADS-Modbus Gateway..."
    cd "$APP_DIR"
    source "$VENV"
    nohup python main.py --config config/mapping.yaml \
        >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "Started (PID $!), log: $LOG_FILE"
}

stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "Gateway not running (no PID file)"
        return 1
    fi

    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping Gateway (PID $PID)..."
        kill "$PID"
        # wait up to 10s for graceful shutdown
        for i in $(seq 1 10); do
            kill -0 "$PID" 2>/dev/null || break
            sleep 1
        done
        # force kill if still alive
        if kill -0 "$PID" 2>/dev/null; then
            echo "Force killing..."
            kill -9 "$PID"
        fi
        echo "Stopped"
    else
        echo "Gateway not running (stale PID file)"
    fi
    rm -f "$PID_FILE"
}

status() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Running (PID $(cat "$PID_FILE"))"
    else
        echo "Not running"
        rm -f "$PID_FILE" 2>/dev/null
    fi
}

log() {
    tail -f "$LOG_FILE"
}

case "${1:-}" in
    start)   start ;;
    stop)    stop ;;
    restart) stop; sleep 1; start ;;
    status)  status ;;
    log)     log ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|log}"
        exit 1
        ;;
esac
