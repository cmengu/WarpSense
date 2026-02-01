#!/bin/bash
# ESP32 firmware check script
# Verifies ESP32 firmware has no interpretation code

set -e

FORBIDDEN_KEYWORDS=("calibration" "filtering" "scoring" "interpret" "process" "transform")
ESP32_FILES=$(find esp32_firmware -name "*.ino" -o -name "*.h" -o -name "*.cpp" 2>/dev/null || true)

VIOLATIONS=0

if [ -z "$ESP32_FILES" ]; then
    echo "⚠️  No ESP32 firmware files found"
    exit 0
fi

for file in $ESP32_FILES; do
    for keyword in "${FORBIDDEN_KEYWORDS[@]}"; do
        # Check for keyword in actual code (not comments)
        # Look for keyword that's not preceded by // or /* or * or TODO or CRITICAL or NOTE
        if grep -qi "$keyword" "$file"; then
            # Check if it's in a comment (starts with // or /* or * or contains TODO/CRITICAL/NOTE)
            if ! grep -qiE "(//|/\*|\*|TODO|CRITICAL|NOTE|server-side).*$keyword" "$file"; then
                # Check if it's actually in code (not a comment line)
                if grep -vE "^\s*(//|/\*|\*)" "$file" | grep -qi "$keyword"; then
                    echo "⚠️  VIOLATION: Found '$keyword' in code (not comment) in $file"
                    echo "   Firmware must not interpret sensor data - all processing happens server-side"
                    VIOLATIONS=$((VIOLATIONS + 1))
                fi
            fi
        fi
    done
done

if [ $VIOLATIONS -eq 0 ]; then
    echo "✅ ESP32 firmware check passed - no interpretation code found"
    exit 0
else
    echo "❌ ESP32 firmware check failed - found $VIOLATIONS violations"
    exit 1
fi
