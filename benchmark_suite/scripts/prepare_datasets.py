"""Windows-friendly entry point for explicit acquisition and frozen manifests."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main() -> int:
    from benchmark_suite import dataset_preparation as preparation
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Acquire approved pinned primary sources only")
    parser.add_argument("--build", action="store_true", help="Validate references and publish immutable manifests")
    parser.add_argument("--validate-only", action="store_true", help="Rehash frozen local data; no network access")
    parser.add_argument("--verify-downloads", action="store_true", help="Rehash downloaded originals without reference decoding")
    args = parser.parse_args()
    suite = Path(__file__).resolve().parents[1]
    if not any([args.download, args.build, args.validate_only, args.verify_downloads]):
        parser.error("Select an explicit download, build or verification mode.")
    try:
        if args.download:
            preparation.acquire(suite)
        if args.build:
            preparation.build(suite)
        if args.verify_downloads:
            preparation.verify_downloads(suite)
        if args.validate_only:
            preparation.validate(suite)
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(1, f"Dataset preparation stopped: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
