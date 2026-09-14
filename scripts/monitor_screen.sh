#!/bin/bash
# =====================================================================
# monitor_screen.sh — show progress of a running screen.
# Reads screen.status (written by screen_worker.sh) and prints a summary.
# Run as many times as you like; non-destructive.
#
# Flags:
#   -w   "watch" mode: refresh every 30s until the job ends
# =====================================================================

set -o pipefail
STATUS_FILE="${STATUS_FILE:-screen.status}"
PID_FILE="${PID_FILE:-screen.pid}"
WATCH=0
[[ "${1:-}" == "-w" ]] && WATCH=1

show() {
    if [[ ! -f "$STATUS_FILE" ]]; then
        echo "No status file ($STATUS_FILE). Has the job started?"
        return 1
    fi
    start_time="?" total=0 done=0 failed=0 skipped=0 remaining=0
    elapsed_sec=0 rate_per_min=0 eta_finish="?"
    ligand_dir="?" out_dir="?" config="?" njobs=0 cpu_per_job=0
    # shellcheck disable=SC1090
    source "$STATUS_FILE"

    local running="NO"
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        running="YES (pid $(cat "$PID_FILE"))"
    fi

    local pct=0
    (( total > 0 )) && pct=$(awk -v d=$done -v t=$total 'BEGIN{printf "%.1f", d/t*100}')

    local bar_len=40
    local filled=0
    (( total > 0 )) && filled=$(( done * bar_len / total ))
    local bar
    bar=$(printf '%*s' "$filled" '' | tr ' ' '#')
    bar+=$(printf '%*s' "$(( bar_len - filled ))" '' | tr ' ' '-')

    local h_elapsed
    h_elapsed=$(printf '%dh %02dm %02ds' $((elapsed_sec/3600)) $(( (elapsed_sec%3600)/60 )) $((elapsed_sec%60)))

    clear 2>/dev/null || true
    echo "================ Virtual Screening Status ================"
    echo "  Started        : $start_time"
    echo "  Running        : $running"
    echo "  Total ligands  : $total"
    echo "  Done           : $done"
    echo "  Failed         : $failed"
    echo "  Skipped (resume): $skipped"
    echo "  Remaining      : $remaining"
    echo ""
    echo "  Progress       : [$bar] $pct%"
    echo ""
    echo "  Elapsed        : $h_elapsed"
    echo "  Rate           : $rate_per_min ligands/min"
    echo "  ETA finish     : $eta_finish"
    echo ""
    echo "  Ligand dir     : $ligand_dir"
    echo "  Output dir     : $out_dir"
    echo "  Workers x cpu  : ${njobs} x ${cpu_per_job}"
    echo "==========================================================="
}

if (( WATCH )); then
    while true; do
        show || exit 1
        if [[ -f "$PID_FILE" ]] && ! kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            echo ""
            echo "Job is no longer running. Final status above."
            exit 0
        fi
        sleep 30
    done
else
    show
fi
