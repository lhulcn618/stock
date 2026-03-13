import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import akshare as ak
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WATCHLIST_PATH = ROOT / "watchlist_codes.txt"
OUTPUT_PATH = ROOT / "src" / "data" / "akshare-snapshot.json"

C_CODE = "\u4ee3\u7801"
C_NAME = "\u540d\u79f0"
C_LATEST = "\u6700\u65b0\u4ef7"
C_CHANGE = "\u6da8\u8dcc\u5e45"
C_VOLUME = "\u6210\u4ea4\u91cf"
C_CLOSE = "\u6536\u76d8"
C_INDUSTRY = "\u6240\u5904\u884c\u4e1a"

SH_MAIN = "\u4e3b\u677fA\u80a1"
STAR_BOARD = "\u79d1\u521b\u677f"
SZ_A_LIST = "A\u80a1\u5217\u8868"
SH_CODE_COL = "\u8bc1\u5238\u4ee3\u7801"
SH_NAME_COL = "\u8bc1\u5238\u7b80\u79f0"
SZ_CODE_COL = "A\u80a1\u4ee3\u7801"
SZ_NAME_COL = "A\u80a1\u7b80\u79f0"
BJ_CODE_COL = "\u8bc1\u5238\u4ee3\u7801"
BJ_NAME_COL = "\u8bc1\u5238\u7b80\u79f0"

NOTE_POOL = [
    "Watch whether the tape confirms the setup into the close.",
    "Keep this on radar for a stronger volume expansion day.",
    "Trend structure is constructive, but confirmation still matters.",
    "A clean follow-through day would improve confidence.",
    "Treat this as a tracking name until price and volume align.",
]

THESIS_POOL = [
    "Track whether sector strength is broadening around this name.",
    "Use daily structure and turnover to judge conviction.",
    "Focus on whether the current swing can hold above recent support.",
    "Keep this in the pool for momentum confirmation rather than prediction.",
    "A stronger close and cleaner breadth would upgrade the setup.",
]


@dataclass
class Signal:
    label: str
    value: str
    level: str


@dataclass
class WatchStock:
    symbol: str
    name: str
    market: str
    sector: str
    price: float
    changePct: float
    momentum: int
    volumeRatio: float
    note: str
    thesis: str
    sparkline: List[float]
    signals: List[Signal]


def read_codes() -> list[str]:
    return [line.strip().lstrip("\ufeff") for line in WATCHLIST_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalize_label(value: object) -> str:
    text = str(value).strip()
    try:
        repaired = text.encode("gbk").decode("utf-8")
        return repaired.strip() or text
    except UnicodeError:
        return text


def calc_signal_level(value: float, strong_threshold: float, watch_threshold: float) -> str:
    if value >= strong_threshold:
        return "strong"
    if value >= watch_threshold:
        return "watch"
    return "calm"


def _append_name_rows(name_map: dict[str, str], frame: pd.DataFrame, code_col: str, name_col: str) -> None:
    normalized = frame.copy()
    normalized[code_col] = normalized[code_col].astype(str).str.zfill(6)
    for _, row in normalized.iterrows():
        code = str(row[code_col]).zfill(6)
        name_map[code] = normalize_label(row[name_col])


def fetch_name_map(codes: list[str]) -> dict[str, str]:
    name_map: dict[str, str] = {}

    try:
        sh_df = ak.stock_info_sh_name_code(symbol=SH_MAIN)
        _append_name_rows(name_map, sh_df, SH_CODE_COL, SH_NAME_COL)
    except Exception as exc:
        print(f"Warning: failed to fetch SH name map: {exc}")

    try:
        kc_df = ak.stock_info_sh_name_code(symbol=STAR_BOARD)
        _append_name_rows(name_map, kc_df, SH_CODE_COL, SH_NAME_COL)
    except Exception as exc:
        print(f"Warning: failed to fetch STAR name map: {exc}")

    try:
        sz_df = ak.stock_info_sz_name_code(symbol=SZ_A_LIST)
        _append_name_rows(name_map, sz_df, SZ_CODE_COL, SZ_NAME_COL)
    except Exception as exc:
        print(f"Warning: failed to fetch SZ name map: {exc}")

    try:
        bj_df = ak.stock_info_bj_name_code()
        _append_name_rows(name_map, bj_df, BJ_CODE_COL, BJ_NAME_COL)
    except Exception as exc:
        print(f"Warning: failed to fetch BJ name map: {exc}")

    return {code: name_map[code] for code in codes if code in name_map}


def fetch_spot_map(codes: list[str]) -> dict[str, dict]:
    try:
        spot_df = ak.stock_zh_a_spot_em()
        spot_df[C_CODE] = spot_df[C_CODE].astype(str).str.zfill(6)
        filtered = spot_df[spot_df[C_CODE].isin(codes)].copy()
        return filtered.set_index(C_CODE).to_dict(orient="index")
    except Exception as exc:
        print(f"Warning: failed to fetch spot snapshot: {exc}")
        return {}


def fetch_hist(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    try:
        hist_df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
        )
    except Exception as exc:
        print(f"Warning: failed to fetch history for {symbol}: {exc}")
        return pd.DataFrame()

    if hist_df.empty:
        return hist_df

    hist_df = hist_df.copy()
    hist_df[C_CLOSE] = pd.to_numeric(hist_df[C_CLOSE], errors="coerce")
    hist_df[C_VOLUME] = pd.to_numeric(hist_df[C_VOLUME], errors="coerce")
    hist_df[C_CHANGE] = pd.to_numeric(hist_df[C_CHANGE], errors="coerce")
    hist_df = hist_df.dropna(subset=[C_CLOSE])
    return hist_df


def build_stock(
    code: str,
    index: int,
    name_map: dict[str, str],
    spot_map: dict[str, dict],
    start_date: str,
    end_date: str,
) -> WatchStock:
    hist_df = fetch_hist(code, start_date, end_date)
    spot = spot_map.get(code, {})

    if hist_df.empty:
        price = float(spot.get(C_LATEST, 0) or 0)
        change_pct = float(spot.get(C_CHANGE, 0) or 0)
        sparkline = [price] * 8 if price else [0.0] * 8
        momentum = 0
        volume_ratio = 0.0
    else:
        recent = hist_df.tail(8)
        last_close = float(recent.iloc[-1][C_CLOSE])
        prev_close = float(recent.iloc[-2][C_CLOSE]) if len(recent) > 1 else last_close
        hist_change = ((last_close - prev_close) / prev_close * 100) if prev_close else 0.0
        price = float(spot.get(C_LATEST, last_close) or last_close)
        change_pct = float(spot.get(C_CHANGE, hist_change) or hist_change)
        sparkline = [round(float(value), 2) for value in recent[C_CLOSE].tolist()]
        ma5 = recent[C_CLOSE].tail(5).mean()
        momentum = int(max(0, min(99, 50 + ((last_close - ma5) / ma5 * 400 if ma5 else 0))))
        recent_volume = recent[C_VOLUME].tail(5).mean()
        base_volume = hist_df[C_VOLUME].tail(20).mean()
        volume_ratio = round(float(recent_volume / base_volume), 2) if base_volume else 0.0

    name = normalize_label(spot.get(C_NAME) or name_map.get(code) or code)
    sector = normalize_label(spot.get(C_INDUSTRY) or "Watchlist")
    change_label = f"{change_pct:+.2f}%"

    signals = [
        Signal("Change", change_label, calc_signal_level(change_pct, 2.0, 0.0)),
        Signal("Momentum", str(momentum), calc_signal_level(momentum, 75, 55)),
        Signal("Volume", f"{volume_ratio:.2f}x", calc_signal_level(volume_ratio, 1.2, 1.0)),
    ]

    return WatchStock(
        symbol=code,
        name=name,
        market="CN",
        sector=sector,
        price=round(price, 2),
        changePct=round(change_pct, 2),
        momentum=momentum,
        volumeRatio=volume_ratio,
        note=NOTE_POOL[index % len(NOTE_POOL)],
        thesis=THESIS_POOL[index % len(THESIS_POOL)],
        sparkline=sparkline,
        signals=signals,
    )


def main() -> None:
    codes = read_codes()
    end = datetime.now()
    start = end - timedelta(days=45)
    start_date = start.strftime("%Y%m%d")
    end_date = end.strftime("%Y%m%d")

    name_map = fetch_name_map(codes)
    spot_map = fetch_spot_map(codes)
    stocks = [
        build_stock(code, index, name_map, spot_map, start_date, end_date)
        for index, code in enumerate(codes)
    ]
    avg_change = round(sum(stock.changePct for stock in stocks) / len(stocks), 2) if stocks else 0.0
    strong_signals = sum(1 for stock in stocks if any(signal.level == "strong" for signal in stock.signals))

    payload = {
        "syncTime": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "watchlistCount": len(stocks),
        "strongSignals": strong_signals,
        "avgChange": avg_change,
        "mood": "risk-on" if avg_change >= 0 else "mixed",
        "stocks": [
            {
                **{key: value for key, value in asdict(stock).items() if key != "signals"},
                "signals": [asdict(signal) for signal in stock.signals],
            }
            for stock in stocks
        ],
    }

    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote AkShare snapshot for {len(stocks)} symbols to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()