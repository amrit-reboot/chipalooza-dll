#!/usr/bin/env bash
# Runs INSIDE the IIC-OSIC-TOOLS container. Records verified tool and PDK facts.
# Invoke from the host with:
#   .\scripts\iic.ps1 bash /foss/designs/scripts/verify_container.sh
# or
#   bash scripts/iic.sh bash /foss/designs/scripts/verify_container.sh
#
# Read-only: inspects versions, PDK paths and corner section names. Installs nothing.

echo "=== container identity ==="
cat /etc/os-release 2>/dev/null | grep PRETTY_NAME
[ -f /etc/iic-osic-tools-release ] && cat /etc/iic-osic-tools-release || true

echo
echo "=== tool versions ==="
printf 'ngspice: %s\n' "$(ngspice --version 2>&1 | head -1)"
printf 'xschem:  %s\n' "$(xschem --version 2>&1 | head -1)"
printf 'python3: %s\n' "$(python3 --version 2>&1)"
printf 'magic:   %s\n' "$(magic --version 2>&1 | head -1)"
printf 'netgen:  %s\n' "$(netgen -batch lvs 2>&1 | head -1)"

echo
echo "=== ngspice build features (noise / monte carlo hints) ==="
ngspice --version 2>&1 | head -6

echo
echo "=== PDK environment ==="
echo "PDK_ROOT=${PDK_ROOT:-<unset>}"
echo "PDK=${PDK:-<unset>}"

echo
echo "=== PDK tree ==="
for d in "${PDK_ROOT:-/foss/pdks}"/*; do
  [ -d "$d" ] && echo "  $d"
done

echo
echo "=== ngspice model directories ==="
find "${PDK_ROOT:-/foss/pdks}" -maxdepth 4 -type d -name ngspice 2>/dev/null

echo
echo "=== sky130 model .lib files ==="
find "${PDK_ROOT:-/foss/pdks}" -maxdepth 4 -name "*.lib.spice" 2>/dev/null

echo
echo "=== corner sections declared in sky130.lib.spice ==="
libfile=$(find "${PDK_ROOT:-/foss/pdks}" -maxdepth 4 -name "sky130.lib.spice" 2>/dev/null | head -1)
if [ -n "$libfile" ]; then
  echo "file: $libfile"
  grep -nE "^[[:space:]]*\.lib[[:space:]]" "$libfile" | head -40
else
  echo "sky130.lib.spice NOT FOUND"
fi

echo
echo "=== available device models (sample) ==="
cornerdir=$(dirname "$(find "${PDK_ROOT:-/foss/pdks}" -maxdepth 4 -name "sky130.lib.spice" 2>/dev/null | head -1)")
[ -n "$cornerdir" ] && ls "$cornerdir" | head -30

echo
echo "=== MiM capacitor model presence ==="
find "${PDK_ROOT:-/foss/pdks}" -maxdepth 5 -iname "*mim*" 2>/dev/null | head -10
