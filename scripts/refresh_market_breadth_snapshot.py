from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from fetch_akshare_watchlist import fetch_market_breadth_profile


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    snapshot_path = root / "src" / "data" / "akshare-snapshot.json"

    if not snapshot_path.exists():
        raise FileNotFoundError(f"snapshot file not found: {snapshot_path}")

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    market_breadth = fetch_market_breadth_profile()

    market_radar = snapshot.setdefault("marketRadar", {})
    market_radar["marketBreadth"] = asdict(market_breadth)
    market_radar["updatedAt"] = market_breadth.updatedAt

    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"已刷新市场宽度到 {snapshot_path}")


if __name__ == "__main__":
    main()
