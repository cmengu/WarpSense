#!/usr/bin/env python3
"""
Phase 3 pre-flight: Verify WELDERS in page.tsx matches WELDER_ARCHETYPES.

Run from project root: PYTHONPATH=backend python backend/scripts/verify_welder_sync.py

Prints welder IDs and session counts. Manually compare with:
  - my-app/src/app/seagull/page.tsx (WELDERS)
  - my-app/src/app/seagull/welder/[id]/page.tsx (WELDER_SESSION_COUNT, WELDER_DISPLAY_NAMES)
"""

import sys
from pathlib import Path

backend = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend))

from data.mock_welders import WELDER_ARCHETYPES


def main():
    print("WELDER_ARCHETYPES (source of truth):")
    print("-" * 50)
    for arch in WELDER_ARCHETYPES:
        print(f"  {arch['welder_id']}: sessionCount={arch['sessions']}, name={arch['name']}")
    print()
    print("Compare with WELDERS in seagull/page.tsx and WELDER_SESSION_COUNT in welder/[id]/page.tsx")
    return 0


if __name__ == "__main__":
    sys.exit(main())
