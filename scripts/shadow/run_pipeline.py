"""Run the full Stage 1 shadow validation pipeline."""

from __future__ import annotations

import argparse
import logging

from scripts.shadow.build_golden_dataset import build_golden_dataset
from scripts.shadow.fetch_videos import fetch_all
from scripts.shadow.validate_scoring import run_validation


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Shadow validation end-to-end pipeline")
    parser.add_argument("--skip-fetch", action="store_true", help="Reuse existing raw_videos.json")
    parser.add_argument("--videos-per-channel", type=int, default=12)
    parser.add_argument("--keyword-results", type=int, default=8)
    args = parser.parse_args()

    if not args.skip_fetch:
        fetch_all(
            videos_per_channel=args.videos_per_channel,
            keyword_results=args.keyword_results,
        )
    build_golden_dataset()
    run_validation()


if __name__ == "__main__":
    main()
