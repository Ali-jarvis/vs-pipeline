#!/bin/bash
# =====================================================================
# stop_screen.sh — terminate a running screen.
# Uses the PID file written by submit_screen.sh and kills the whole
# process group (the worker + every Vina child it launched).
# =====================================================================

set -uo pipefail
PID_FILE="${PID_FILE:-screen.pid}"

if [[ ! -f "$PID_FILE" ]]; then
    echo "No PID file ($PID_FILE) — nothing to stop."
    exit 0
fi

PID=$(cat "$PID_FILE")
if ! kill -0 "$PID" 2>/dev/null; then
    echo "Process $PID is not running. Cleaning up PID file."
    rm -f "$PID_FILE"
    exit 0
fi

echo "Stopping screening job (pid $PID and children)..."
kill -TERM -- "-$PID" 2>/dev/null || kill -TERM "$PID"

for _ in {1..10}; do
    kill -0 "$PID" 2>/dev/null || break
    sleep 1
done
if kill -0 "$PID" 2>/dev/null; then
    echo "Still alive after SIGTERM — sending SIGKILL."
    kill -KILL -- "-$PID" 2>/dev/null || kill -KILL "$PID"
fi

rm -f "$PID_FILE"
echo "Stopped. Partial outputs in vina_out/ are preserved — rerun submit_screen.sh to resume."
