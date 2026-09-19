#!/usr/bin/env bash
# DoD mínimo PROPOMI — fallar el cambio si esto falla.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "== pytest =="
cd "$ROOT/apps/api"
if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate 2>/dev/null || true
fi
python -m pytest -q

echo "== tsc =="
cd "$ROOT/apps/web"
npx tsc --noEmit

echo "== use client guard =="
# Evita el fallo de comilla comida al copiar archivos
while IFS= read -r -d '' f; do
  first=$(head -n 1 "$f" | tr -d '\r')
  if [[ "$first" == "use client;" ]]; then
    echo "BROKEN directive (missing quote): $f"
    exit 1
  fi
done < <(find "$ROOT/apps/web" -name '*.tsx' -print0)

echo "== next build =="
cd "$ROOT/apps/web"
npm run build

echo "OK — checklist verde"
