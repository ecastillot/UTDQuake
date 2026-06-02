#!/bin/bash
#SBATCH -N 1
#SBATCH -n 64
#SBATCH -p normal
#SBATCH -J UTDQup
#SBATCH -o /groups/igonin/ecastillo/utdquake/test/upload/upload_zipbankdas_%j.out

set -euo pipefail

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

BASE="/groups/igonin/ecastillo/UTDQuake_DAS_upload"
BANK_DIR="${BASE}/banks_DAS"

MAX_ZIP_JOBS=20
HF_WORKERS=4

# echo "========================================"
# echo "Zipping DAS bank folders"
# echo "========================================"

# mapfile -t NETS < <(
#     find "$BANK_DIR" -mindepth 1 -maxdepth 1 -type d -printf "%f\n" | sort
# )

# running=0
# total=${#NETS[@]}
# count=0

# for net in "${NETS[@]}"; do
#     count=$((count+1))

#     (
#         src="${BANK_DIR}/${net}"
#         out="${BANK_DIR}/${net}.zip"

#         if [[ -f "$out" ]]; then
#             echo "[SKIP ${count}/${total}] ${net}.zip already exists"
#             exit 0
#         fi

#         echo "[ZIP  START] $net"

#         cd "$BANK_DIR"
#         zip -rq9 "$out" "$net"

#         echo "[ZIP  DONE ] $net"
#     ) &

#     running=$((running+1))

#     if (( running >= MAX_ZIP_JOBS )); then
#         wait -n
#         running=$((running-1))
#     fi
# done

# wait

# echo "All zip jobs finished."

echo "Uploading to HuggingFace..."

hf upload-large-folder ecastillot/UTDQuake \
    "$BASE" \
    --include "banks_DAS/*.zip" \
    --repo-type dataset \
    --num-workers "$HF_WORKERS"

echo "✅ DONE"