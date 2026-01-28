#!/bin/bash
#SBATCH -N 1
#SBATCH -n 64
#SBATCH -p normal
#SBATCH -J UTDQZIPUP
#SBATCH -o /groups/igonin/ecastillo/utdquake/upload/upload_pro_%j.out

set -euo pipefail

# --------------------------------------------
# Defaults
# --------------------------------------------
NETWORKS="all"
PICKS=false

# --------------------------------------------
# Help message
# --------------------------------------------
usage() {
cat << EOF
Usage: $(basename "$0") [OPTIONS]

Zip UTDQuake event networks and upload to HuggingFace.

OPTIONS:
  -n, --networks LIST     Networks to process (comma-separated),
                          or 'all' (default: all)

      --with-picks        Include .picks.db files (heavy)
      --no-picks          Exclude .picks.db files (default)

  -h, --help              Show this help message and exit

EXAMPLES:
  Zip all networks WITHOUT picks (default):
    $(basename "$0")

  Zip all networks WITH picks:
    $(basename "$0") --with-picks

  Zip specific networks without picks:
    $(basename "$0") -n RSNC,TX,ABC

  Zip specific networks with picks:
    $(basename "$0") -n RSNC,TX --with-picks
EOF
}

# --------------------------------------------
# Parse arguments
# --------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    -n|--networks)
      NETWORKS="$2"
      shift 2
      ;;
    --with-picks)
      PICKS=true
      shift
      ;;
    --no-picks)
      PICKS=false
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown option '$1'"
      echo ""
      usage
      exit 1
      ;;
  esac
done

# --------------------------------------------
# Environment setup
# --------------------------------------------
source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

BASE="/groups/igonin/ecastillo/UTDQuake"
EVENTS_SRC="${BASE}/events"

STAGE="${BASE}/_hf_stage"
EVENTS_STAGE="${STAGE}/bank"

mkdir -p "$EVENTS_STAGE"

# Max parallel zip jobs
MAX_ZIP_JOBS=20

# Workers for HF upload threads
HF_WORKERS=4

echo "========================================"
echo "UTDQuake zip+upload"
echo "Node: $(hostname)"
echo "Cores allocated: ${SLURM_NTASKS:-unknown}"
echo "Networks: $NETWORKS"
echo "Include .picks.db: $PICKS"
echo "MAX_ZIP_JOBS=$MAX_ZIP_JOBS"
echo "HF_WORKERS=$HF_WORKERS"
echo "========================================"
echo ""

# --------------------------------------------
# Resolve network list
# --------------------------------------------
if [[ "$NETWORKS" == "all" ]]; then
    mapfile -t NETS < <(
        find "$EVENTS_SRC" -mindepth 1 -maxdepth 1 -type d -printf "%f\n" | sort
    )
else
    IFS=',' read -r -a NETS <<< "$NETWORKS"
fi

TOTAL=${#NETS[@]}

echo "Processing $TOTAL networks:"
printf "  - %s\n" "${NETS[@]}"
echo ""

# --------------------------------------------
# Step 1) Zipping networks
# --------------------------------------------
echo "Step 1) Zipping networks into: $EVENTS_STAGE"
echo "----------------------------------------"

done_count=0
running=0

for net in "${NETS[@]}"; do
  outzip="${EVENTS_STAGE}/${net}.zip"

  # Resume support
  if [[ -f "$outzip" ]]; then
    done_count=$((done_count+1))
    echo "[SKIP ${done_count}/${TOTAL}] ${net}.zip already exists"
    continue
  fi

  (
    echo "[ZIP  START] $net"
    cd "$EVENTS_SRC"

    if [[ "$PICKS" == "true" ]]; then
        zip -rq9 "$outzip" "$net"
    else
        zip -rq9 "$outzip" "$net" -x "$net/.picks.db"
    fi

    echo "[ZIP  DONE ] $net"
  ) &

  running=$((running+1))

  # Throttle parallel jobs
  if (( running >= MAX_ZIP_JOBS )); then
    wait -n
    running=$((running-1))
  fi
done

wait
echo "All zip jobs finished."
echo ""

# --------------------------------------------
# Step 2) Uploading zips to HuggingFace
# --------------------------------------------
echo "Step 2) Uploading zips to HuggingFace as events/*.zip"
echo "----------------------------------------"

hf upload-large-folder ecastillot/UTDQuake "$STAGE" \
  --include "events/*.zip" \
  --repo-type dataset \
  --num-workers "$HF_WORKERS"

echo "✅ DONE"
