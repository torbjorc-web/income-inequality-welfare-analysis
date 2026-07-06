from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMMIT_MESSAGE = "Update database snapshot and derived outputs"


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)}")


def stage_release_files() -> None:
    # Keep staging intentionally narrow to the DB and deterministic derived outputs.
    run(
        [
            "git",
            "add",
            "database/database.db",
            "data/processed",
            "outputs/tables",
        ]
    )


def has_staged_changes() -> bool:
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=str(ROOT),
    )
    return result.returncode != 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild DB artifacts and publish a consistent git snapshot.",
    )
    parser.add_argument(
        "--message",
        default=DEFAULT_COMMIT_MESSAGE,
        help="Commit message to use for the release snapshot.",
    )
    parser.add_argument(
        "--skip-push",
        action="store_true",
        help="Commit locally but do not push to origin/main.",
    )
    parser.add_argument(
        "--skip-charts",
        action="store_true",
        help="Skip scripts/make_charts.py.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    run([sys.executable, "setup_database.py"])
    run([sys.executable, "scripts/clean_data.py"])
    run([sys.executable, "scripts/analyze_data.py"])
    if not args.skip_charts:
        run([sys.executable, "scripts/make_charts.py"])

    stage_release_files()

    if not has_staged_changes():
        print("No staged changes detected after rebuild. Nothing to commit.")
        return

    run(["git", "commit", "-m", args.message])
    if not args.skip_push:
        run(["git", "push", "origin", "main"])

    print("Release snapshot complete.")


if __name__ == "__main__":
    main()
