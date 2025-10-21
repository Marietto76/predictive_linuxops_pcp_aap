#!/usr/bin/env bash
set -euo pipefail

# === CONFIG ===
DIR=/var/log/pcp/pmlogger/$(hostname)
METRIC=ds389.cn.opscompleted
OUT=/tmp/${METRIC//./_}_all_pmrep_final.csv
INTERVAL=1min
TZ_REGION="America/Guayaquil"   # o "UTC" si prefieres
#TZ_REGION="UTC"
# Rango: TODO el 7, 8 y 9 de octubre (incluye el 9 completo)
START="2025-10-07 00:00:00"
FINISH="2025-10-10 00:00:00"    # fin exclusivo (el día 10 a las 00:00)

# === INIT ===
echo "Time,${METRIC}" > "$OUT"

# === LISTA DE ARCHIVOS (basenames) ===
mapfile -t ARCHS < <(ls -1 "$DIR"/*.index 2>/dev/null | sed 's/\.index$//' | sort -u)
echo "Found ${#ARCHS[@]} PCP slices in $DIR"

# === LOOP ===
for B in "${ARCHS[@]}"; do
  echo "Processing: $B"
  if [[ -r "${B}.index" && -r "${B}.meta.xz" && -r "${B}.0.xz" ]]; then
    pmrep "$METRIC" \
      --archive "$B" \
      -t "$INTERVAL" \
      -Z "$TZ_REGION" \
      --start "$START" \
      --finish "$FINISH" \
      -o csv \
    | awk -F, -v s="$START" -v e="$FINISH" '
        NR==1 {next}           # quita cabecera de pmrep
        $2=="" {next}          # salta filas vacías
        ($1>=s && $1<e) {print $0}
      ' >> "$OUT"
  else
    echo "  ⚠️  Slice incomplete, skipping: $B"
  fi
done

# Ordena y dedup por timestamp
{ head -n1 "$OUT"; tail -n +2 "$OUT" | LC_ALL=C sort -t, -k1,1 -u; } > "${OUT}.tmp"
mv "${OUT}.tmp" "$OUT"

echo "✅ Combined CSV ready: $OUT"
head -n 20 "$OUT"
wc -l "$OUT"


