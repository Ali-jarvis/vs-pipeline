#!/bin/bash
# =====================================================================
# submit_screen.sh — launch screen_worker.sh fully detached.
#
# After running this you can:
#   * close your SSH session
#   * close your laptop lid
#   * disconnect from VPN
# ...and the screening will keep running on the server.
#
# Usage:
#   ./submit_screen.sh                       # 50 CPUs (default)
#   NJOBS=80 LIGAND_DIR=pdbqt_out ./submit_screen.sh
#   ./submit_screen.sh --check               # dry-run: show plan, exit
#
# Then check progress with:  ./monitor_screen.sh
# Stop the job with:          ./stop_screen.sh
# =====================================================================

set -euo pipefail

WORKER="${WORKER:-./screen_worker.sh}"
PID_FILE="${PID_FILE:-screen.pid}"
RUN_LOG="${RUN_LOG:-screen.run.log}"
CONDA_ENV="${CONDA_ENV:-vs_run}"
NICE_LEVEL="${NICE_LEVEL:-10}"
IONICE_CLASS="${IONICE_CLASS:-2}"

DRY_RUN=0
[[ "${1:-}" == "--check" ]] && DRY_RUN=1

NPROC_TOTAL=$(nproc)
CPU_RESERVE="${CPU_RESERVE:-4}"
# Permanent default: 50 parallel Vina jobs. Override with NJOBS=N.
PLAN_NJOBS="${NJOBS:-50}"
PLAN_CPU_PER_JOB="${CPU_PER_JOB:-1}"
PLAN_TOTAL=$(( PLAN_NJOBS * PLAN_CPU_PER_JOB ))

echo "CPU plan:"
echo "  Total cores on this server : $NPROC_TOTAL"
echo "  Reserved (CPU_RESERVE)     : $CPU_RESERVE"
echo "  Parallel Vina jobs (NJOBS) : $PLAN_NJOBS"
echo "  CPUs per Vina (CPU_PER_JOB): $PLAN_CPU_PER_JOB"
echo "  Total CPUs that will be used: $PLAN_TOTAL"
echo "  Niceness                   : $NICE_LEVEL (higher = politer to others)"
echo ""

if (( PLAN_TOTAL > NPROC_TOTAL )); then
    echo "ERROR: requested $PLAN_TOTAL CPUs but only $NPROC_TOTAL available."
    echo "Lower NJOBS or CPU_PER_JOB. Refusing to oversubscribe."
    exit 1
fi

if (( DRY_RUN )); then
    echo "Dry run (--check) — exiting without submitting."
    exit 0
fi

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "A screening job is already running (pid=$(cat "$PID_FILE"))."
    echo "Stop it first with ./stop_screen.sh, or check with ./monitor_screen.sh"
    exit 1
fi

[[ -x "$WORKER" ]] || chmod +x "$WORKER" 2>/dev/null || true
[[ -f "$WORKER" ]] || { echo "ERROR: worker '$WORKER' missing"; exit 1; }

CONDA_SH=""
for p in "$HOME/miniconda3/etc/profile.d/conda.sh" \
         "$HOME/anaconda3/etc/profile.d/conda.sh" \
         "/opt/conda/etc/profile.d/conda.sh" \
         "/opt/miniconda3/etc/profile.d/conda.sh"; do
    [[ -f "$p" ]] && { CONDA_SH="$p"; break; }
done
if [[ -z "$CONDA_SH" ]]; then
    echo "WARNING: couldn't locate conda.sh — worker will assume '$CONDA_ENV' is already active."
fi

export NJOBS="$PLAN_NJOBS"

ENV_DUMP=$(mktemp)
{
    [[ -n "$CONDA_SH" ]] && echo "source '$CONDA_SH' && conda activate '$CONDA_ENV'"
    for var in LIGAND_DIR OUT_DIR CONFIG VINA_BIN EXHAUSTIVENESS NUM_MODES \
               NJOBS CPU_PER_JOB CPU_RESERVE SEED STATUS_FILE DETAIL_LOG; do
        if [[ -n "${!var:-}" ]]; then
            printf 'export %s=%q\n' "$var" "${!var}"
        fi
    done
    echo "exec bash '$WORKER'"
} > "$ENV_DUMP"

LAUNCH="nice -n $NICE_LEVEL"
if command -v ionice >/dev/null 2>&1; then
    LAUNCH="ionice -c $IONICE_CLASS $LAUNCH"
fi

nohup setsid $LAUNCH bash "$ENV_DUMP" >"$RUN_LOG" 2>&1 </dev/null &
PID=$!
echo "$PID" > "$PID_FILE"

sleep 2
if ! kill -0 "$PID" 2>/dev/null; then
    if grep -q "FINISHED" "$RUN_LOG" 2>/dev/null; then
        echo "Worker completed in under 2 seconds (small library). Final state:"
        tail -n 3 "$RUN_LOG"
        rm -f "$PID_FILE"
        exit 0
    fi
    echo "ERROR: worker died immediately. Check $RUN_LOG:"
    echo "------"
    tail -n 30 "$RUN_LOG"
    rm -f "$PID_FILE"
    exit 1
fi

echo "Screening submitted."
echo "  PID            : $PID  (saved to $PID_FILE)"
echo "  Run log        : $RUN_LOG"
echo "  Status file    : ${STATUS_FILE:-screen.status}"
echo "  Detail log     : ${DETAIL_LOG:-screen.detail.log}"
echo ""
echo "You can safely 'exit' the SSH session now."
echo "Check progress later with:  ./monitor_screen.sh"
echo "Stop the job with:           ./stop_screen.sh"
