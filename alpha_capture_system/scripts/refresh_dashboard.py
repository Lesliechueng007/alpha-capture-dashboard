from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_step(cmd: list[str]) -> None:
    print(f"Running: {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    py = sys.executable
    run_step([py, "scripts/update_alpha_watchlist.py"])
    run_step([py, "scripts/build_web_dashboard.py"])
    print("Dashboard refreshed.")


if __name__ == "__main__":
    main()
