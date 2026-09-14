#!/bin/bash
# =====================================================================
# screen_worker.sh — the actual screening loop.
# Do NOT run this directly if you want to close your laptop — use
# submit_screen.sh, which launches THIS worker fully detached.
# =====================================================================

set -uo pipefail

LIGAND_DIR="${LIGAND_DIR:-pdbqt_out}"
OUT_DIR="${OUT_DIR:-vina_out}"
CONFIG="${CONFIG:-vina_config.txt}"
VINA_BIN="${VINA_BIN:-vina}"
EXHAUSTIVENESS="${EXHAUSTIVENESS:-8}"
NUM_MODES="${NUM_MODES:-9}"
CPU_RESERVE="${CPU_RESERVE:-4}"
NPROC_TOTAL=$(nproc)
NJOBS_DEFAULT=$(( NPROC_TOTAL - CPU_RESERVE ))
(( NJOBS_DEFAULT < 1 )) && NJOBS_DEFAULT=1
NJOBS="${NJOBS:-$NJOBS_DEFAULT}"
CPU_PER_JOB="${CPU_PER_JOB:-1}"
SEED="${SEED:-42}"
STATUS_FILE="${STATUS_FILE:-screen.status}"
DETAIL_LOG="${DETAIL_LOG:-screen.detail.log}"

TOTAL_CPU_REQUEST=$(( NJOBS * CPU_PER_JOB ))
if (( TOTAL_CPU_REQUEST > NPROC_TOTAL )); then
    echo "ERROR: NJOBS ($NJOBS) x CPU_PER_JOB ($CPU_PER_JOB) = $TOTAL_CPU_REQUEST exceeds nproc ($NPROC_TOTAL)."
    exit 1
fi

mkdir -p "$OUT_DIR"

# ----- preflight checks ---------------------------------------------------
err=0
[[ -d "$LIGAND_DIR" ]] || { echo "ERROR: ligand dir '$LIGAND_DIR' not found"; err=1; }
[[ -f "$CONFIG" ]]     || { echo "ERROR: vina config '$CONFIG' not found"; err=1; }
command -v "$VINA_BIN" >/dev/null || { echo "ERROR: '$VINA_BIN' not on PATH"; err=1; }
RECEPTOR=$(awk -F= '/^[[:space:]]*receptor/{gsub(/[[:space:]]/,"",$2); print $2}' "$CONFIG" 2>/dev/null || true)
[[ -n "$RECEPTOR" && -f "$RECEPTOR" ]] || { echo "ERROR: receptor '$RECEPTOR' from $CONFIG not found"; err=1; }
(( err == 0 )) || exit 1

TOTAL=$(find "$LIGAND_DIR" -name "*.pdbqt" | wc -l)
(( TOTAL > 0 )) || { echo "ERROR: no PDBQT ligands in $LIGAND_DIR"; exit 1; }

START_TS=$(date +%s)
START_HUMAN=$(date '+%Y-%m-%d %H:%M:%S')

write_status() {
    local done=$1 fail=$2 skip=$3
    local now=$(date +%s)
    local elapsed=$(( now - START_TS ))
    local processed=$(( done + fail ))
    local rate="" eta_sec="" eta_human=""
    if (( processed > 0 && elapsed > 0 )); then
        rate=$(awk -v p=$processed -v e=$elapsed 'BEGIN{printf "%.2f", p/e*60}')
        local remain=$(( TOTAL - done - fail - skip ))
        if (( processed > 0 )); then
            eta_sec=$(awk -v r=$remain -v p=$processed -v e=$elapsed 'BEGIN{printf "%d", r*e/p}')
            eta_human=$(date -d "@$(( now + eta_sec ))" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "?")
        fi
    fi
    cat > "${STATUS_FILE}.tmp" <<EOF
start_time="$START_HUMAN"
pid="$$"
total="$TOTAL"
done="$done"
failed="$fail"
skipped="$skip"
remaining="$(( TOTAL - done - fail - skip ))"
elapsed_sec="$elapsed"
rate_per_min="${rate:-0}"
eta_finish="${eta_human:-unknown}"
ligand_dir="$LIGAND_DIR"
out_dir="$OUT_DIR"
config="$CONFIG"
njobs="$NJOBS"
cpu_per_job="$CPU_PER_JOB"
EOF
    mv -f "${STATUS_FILE}.tmp" "$STATUS_FILE"
}

echo "[$START_HUMAN] worker pid=$$  total=$TOTAL"
echo "  CPU plan: $NJOBS parallel jobs x $CPU_PER_JOB CPU = $TOTAL_CPU_REQUEST of $NPROC_TOTAL cores"
echo "  Reserved for system / other users: $(( NPROC_TOTAL - TOTAL_CPU_REQUEST )) cores"
echo "  Niceness of this process: $(nice)"
write_status 0 0 0

dock_one() {
    local lig="$1"
    local name
    name=$(basename "$lig" .pdbqt)
    local out="$OUT_DIR/${name}_out.pdbqt"
    local log="$OUT_DIR/${name}.vina.log"

    if [[ -f "$out" ]] && grep -q "REMARK VINA RESULT" "$out"; then
        echo "SKIP $name"
        return 0
    fi

    if "$VINA_BIN" \
            --config "$CONFIG" \
            --ligand "$lig" \
            --out "$out" \
            --cpu "$CPU_PER_JOB" \
            --exhaustiveness "$EXHAUSTIVENESS" \
            --num_modes "$NUM_MODES" \
            --seed "$SEED" \
            >"$log" 2>&1; then
        echo "OK   $name"
    else
        rm -f "$out"
        echo "FAIL $name"
    fi
}
export -f dock_one
export OUT_DIR CONFIG VINA_BIN EXHAUSTIVENESS NUM_MODES CPU_PER_JOB SEED

done=0; failed=0; skipped=0
while IFS= read -r line; do
    case "$line" in
        OK*)   done=$((done+1)) ;;
        FAIL*) failed=$((failed+1)) ;;
        SKIP*) skipped=$((skipped+1)); done=$((done+1)) ;;
    esac
    echo "$(date '+%H:%M:%S')  $line" >> "$DETAIL_LOG"
    if (( (done + failed) % 5 == 0 )); then
        write_status "$done" "$failed" "$skipped"
    fi
done < <(
    find "$LIGAND_DIR" -name "*.pdbqt" -print0 \
        | xargs -0 -P "$NJOBS" -I{} bash -c 'dock_one "$@"' _ {}
)

write_status "$done" "$failed" "$skipped"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] FINISHED  done=$done  failed=$failed  skipped=$skipped"
