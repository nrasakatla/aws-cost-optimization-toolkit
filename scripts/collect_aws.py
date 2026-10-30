#!/usr/bin/env python3
"""Optional live AWS collection — READ-ONLY, explicit opt-in only.

This script is a *stub/guard*. It will refuse to run unless BOTH:
  - COSTTK_COLLECTOR=live and COSTTK_READ_ONLY=1 are set in the environment, AND
  - you pass --yes-i-know on the command line.

Even then, it only invokes read-only boto3 APIs. It never creates, stops,
modifies, resizes, or deletes any AWS resource.

Default (and the only path used by the demo/tests) is the synthetic provider.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from costtk.config import load_settings  # noqa: E402


def main() -> int:
    settings = load_settings()
    if "--yes-i-know" not in sys.argv or not settings.live_collection_enabled:
        print(
            "Refusing to run live collection. This triggers boto3 read-only calls.\n"
            "To enable (future, opt-in only):\n"
            "  COSTTK_COLLECTOR=live COSTTK_READ_ONLY=1 python scripts/collect_aws.py --yes-i-know\n"
            "No AWS collection performed.",
            file=sys.stderr,
        )
        return 1

    # NOTE: live collectors are stubs in this project. No AWS API is called here.
    print("Live collection not implemented (stubbed collectors only). Nothing to do.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
