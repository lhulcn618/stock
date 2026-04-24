from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import fetch_akshare_watchlist as fw

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "docs" / "cycles"
STOCK_CHART_DIR = OUTPUT_DIR / "stocks"
SUMMARY_PATH = OUTPUT_DIR / "watchlist-cycle-summary.md"
GRID_PATH = OUTPUT_DIR / "watchlist-cycle-grid.png"
JSON_PATH = OUTPUT_DIR / "watchlist-cycle-report.json"

START_DATE = "20240201"
END_DATE = datetime.now().strftime("%Y%m%d")


@dataclass
class PivotPoint:
    kind: str
    index: int
    date: str
    price: float


@dataclass
class SwingSegment:
    direction: str
    start_date: str
    end_date: str
    trading_days: int
    return_pct: float


@dataclass
class CycleWindow:
    label: str
    direction: str
    start_date: str
    end_date: str
    trading_days: int
    return_pct: float
    status: str


@dataclass
class CycleOpportunity:
    current_price: float
    current_date: str
    phase_label: str
    action_label: str
    tone: str
    summary: str
    support_price: float
    support_date: str
    resistance_price: float
    resistance_date: str
    distance_to_support_pct: float
    distance_to_resistance_pct: float
    rebound_from_support_pct: float
    drawdown_from_resistance_pct: float


@dataclass
class CycleRegime:
    label: str
    action_label: str
    tone: str
    since_date: str
    range_low: float
    range_high: float
    current_position_pct: float
    amplitude_ratio: float
    liquidity_ratio: float
    path_efficiency: float
    recent_swing_count: int
    summary: str


@dataclass
class CycleSummary:
    symbol: str
    name: str
    score: int
    level: str
    recommendation: str
    pivot_count: int
    swing_count: int
    avg_up_days: float
    avg_down_days: float
    avg_up_return_pct: float
    avg_down_return_pct: float
    duration_cv: float
    amplitude_cv: float
    latest_state: str
    chart_path: str
    grid_path: str
    regime: CycleRegime
    opportunity: CycleOpportunity
    recent_cycles: list[CycleWindow]
    current_cycle: CycleWindow
    pivots: list[PivotPoint]
    swings: list[SwingSegment]


def ensure_output_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STOCK_CHART_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_float(value: float | int | None, digits: int = 2) -> float:
    number = float(value or 0.0)
    return round(number, digits) if math.isfinite(number) else 0.0


def cv(values: Iterable[float]) -> float:
    data = [float(value) for value in values if value is not None]
    if len(data) < 2:
        return 1.0
    mean_value = sum(data) / len(data)
    if mean_value == 0:
        return 1.0
    variance = sum((value - mean_value) ** 2 for value in data) / (len(data) - 1)
    return math.sqrt(variance) / abs(mean_value)


def score_consistency(raw_cv: float, scale: float) -> float:
    bounded = min(max(raw_cv, 0.0), scale)
    return max(0.0, 1.0 - bounded / scale)


def prepare_history_frame(symbol: str) -> pd.DataFrame:
    frame = fw.fetch_hist(symbol, START_DATE, END_DATE).copy()
    if frame.empty:
        return frame

    frame["date"] = pd.to_datetime(frame["date"])
    frame["close"] = pd.to_numeric(frame[fw.C_CLOSE], errors="coerce")
    frame["high"] = pd.to_numeric(frame.get(fw.C_HIGH), errors="coerce")
    frame["low"] = pd.to_numeric(frame.get(fw.C_LOW), errors="coerce")
    frame = frame.dropna(subset=["date", "close"]).reset_index(drop=True)
    frame["ma20"] = frame["close"].rolling(20).mean()
    frame["ma60"] = frame["close"].rolling(60).mean()
    return frame


def detect_cycle_pivots(frame: pd.DataFrame) -> list[PivotPoint]:
    if len(frame) < 60:
        return []

    close = frame["close"].reset_index(drop=True)
    dates = frame["date"].reset_index(drop=True)
    smooth = close.ewm(span=5, adjust=False).mean()
    daily_std = close.pct_change().std()
    min_move = max(0.08, min(0.18, float((daily_std if pd.notna(daily_std) else 0.03) * 2.8)))
    window = 11 if len(frame) >= 180 else 9
    min_gap = 12

    rolling_high = smooth.rolling(window, center=True, min_periods=window).max()
    rolling_low = smooth.rolling(window, center=True, min_periods=window).min()

    candidates: list[PivotPoint] = []
    half_window = window // 2
    for idx in range(half_window, len(frame) - half_window):
        if pd.isna(rolling_high.iloc[idx]) or pd.isna(rolling_low.iloc[idx]):
            continue
        smooth_price = float(smooth.iloc[idx])
        price = float(close.iloc[idx])
        if abs(smooth_price - float(rolling_high.iloc[idx])) < 1e-9:
            candidates.append(PivotPoint("high", idx, dates.iloc[idx].strftime("%Y-%m-%d"), price))
        if abs(smooth_price - float(rolling_low.iloc[idx])) < 1e-9:
            candidates.append(PivotPoint("low", idx, dates.iloc[idx].strftime("%Y-%m-%d"), price))

    candidates.sort(key=lambda item: item.index)
    if not candidates:
        return []

    merged: list[PivotPoint] = []
    for candidate in candidates:
        if not merged:
            merged.append(candidate)
            continue

        previous = merged[-1]
        same_kind = candidate.kind == previous.kind
        nearby = candidate.index - previous.index <= min_gap
        if same_kind and nearby:
            if (candidate.kind == "high" and candidate.price >= previous.price) or (
                candidate.kind == "low" and candidate.price <= previous.price
            ):
                merged[-1] = candidate
            continue

        merged.append(candidate)

    filtered: list[PivotPoint] = []
    for candidate in merged:
        if not filtered:
            filtered.append(candidate)
            continue

        previous = filtered[-1]
        if candidate.kind == previous.kind:
            if (candidate.kind == "high" and candidate.price >= previous.price) or (
                candidate.kind == "low" and candidate.price <= previous.price
            ):
                filtered[-1] = candidate
            continue

        move = abs(candidate.price / previous.price - 1)
        if move < min_move:
            continue
        filtered.append(candidate)

    while len(filtered) >= 2 and filtered[0].kind == filtered[1].kind:
        filtered.pop(0)
    return filtered


def build_swings(pivots: list[PivotPoint]) -> list[SwingSegment]:
    swings: list[SwingSegment] = []
    for left, right in zip(pivots, pivots[1:]):
        if left.kind == "low" and right.kind == "high":
            direction = "up"
        elif left.kind == "high" and right.kind == "low":
            direction = "down"
        else:
            continue

        trading_days = max(1, right.index - left.index)
        return_pct = (right.price / left.price - 1) * 100
        swings.append(
            SwingSegment(
                direction=direction,
                start_date=left.date,
                end_date=right.date,
                trading_days=trading_days,
                return_pct=sanitize_float(return_pct, 2),
            )
        )

    return swings


def build_cycle_windows(frame: pd.DataFrame, pivots: list[PivotPoint], swings: list[SwingSegment]) -> tuple[list[CycleWindow], CycleWindow]:
    recent_swings = swings[-2:]
    recent_cycles = [
        CycleWindow(
            label=f"完整周期 {index + 1}",
            direction=item.direction,
            start_date=item.start_date,
            end_date=item.end_date,
            trading_days=item.trading_days,
            return_pct=item.return_pct,
            status="completed",
        )
        for index, item in enumerate(recent_swings)
    ]

    if frame.empty:
        return recent_cycles, CycleWindow("当前周期", "up", "", "", 0, 0.0, "ongoing")

    current_date = frame["date"].iloc[-1].strftime("%Y-%m-%d")
    current_price = float(frame["close"].iloc[-1])
    if not pivots:
        base_price = float(frame["close"].iloc[0])
        trading_days = max(1, len(frame) - 1)
        return_pct = sanitize_float(((current_price / base_price) - 1) * 100, 2) if base_price else 0.0
        return recent_cycles, CycleWindow(
            label="当前周期",
            direction="up" if return_pct >= 0 else "down",
            start_date=frame["date"].iloc[0].strftime("%Y-%m-%d"),
            end_date=current_date,
            trading_days=trading_days,
            return_pct=return_pct,
            status="ongoing",
        )

    last_pivot = pivots[-1]
    start_index = max(0, min(last_pivot.index, len(frame) - 1))
    trading_days = max(1, len(frame) - 1 - start_index)
    if last_pivot.price:
        current_return_pct = sanitize_float(((current_price / last_pivot.price) - 1) * 100, 2)
    else:
        current_return_pct = 0.0
    current_direction = "up" if current_return_pct >= 0 else "down"

    return recent_cycles, CycleWindow(
        label="当前周期",
        direction=current_direction,
        start_date=last_pivot.date,
        end_date=current_date,
        trading_days=trading_days,
        return_pct=current_return_pct,
        status="ongoing",
    )


def build_recent_regime_metrics(frame: pd.DataFrame, pivots: list[PivotPoint]) -> dict[str, float | int | str | list[PivotPoint] | list[SwingSegment]]:
    if frame.empty:
        return {
            "recent_start_date": "",
            "recent_end_date": "",
            "range_low": 0.0,
            "range_high": 0.0,
            "current_position_pct": 0.0,
            "amplitude_ratio": 0.0,
            "liquidity_ratio": 0.0,
            "net_return_pct": 0.0,
            "path_efficiency": 0.0,
            "recent_pivots": [],
            "recent_swings": [],
            "recent_up_swings": 0,
            "recent_down_swings": 0,
            "breakout_up": False,
            "breakout_down": False,
        }

    lookback = 80
    recent = frame.tail(lookback).copy()
    prior = frame.iloc[-lookback * 2:-lookback].copy() if len(frame) >= lookback * 2 else frame.head(max(len(frame) - lookback, 1)).copy()

    recent["amp"] = (recent["high"] - recent["low"]) / recent["close"].shift(1) * 100
    prior["amp"] = (prior["high"] - prior["low"]) / prior["close"].shift(1) * 100

    recent_amp = float(recent["amp"].dropna().mean()) if recent["amp"].notna().any() else 0.0
    prior_amp = float(prior["amp"].dropna().mean()) if prior["amp"].notna().any() else 0.0
    amplitude_ratio = recent_amp / max(prior_amp, 0.01)

    recent_volume = float(recent[fw.C_VOLUME].mean()) if fw.C_VOLUME in recent.columns else 0.0
    prior_volume = float(prior[fw.C_VOLUME].mean()) if fw.C_VOLUME in prior.columns else 0.0
    liquidity_ratio = recent_volume / max(prior_volume, 1.0)

    range_low = float(recent["close"].min()) if not recent.empty else 0.0
    range_high = float(recent["close"].max()) if not recent.empty else 0.0
    current_price = float(recent["close"].iloc[-1]) if not recent.empty else 0.0
    current_position_pct = 0.0
    if range_high > range_low:
        current_position_pct = (current_price - range_low) / (range_high - range_low) * 100

    net_return_pct = 0.0
    if len(recent) >= 2 and float(recent["close"].iloc[0]) != 0:
        net_return_pct = (current_price / float(recent["close"].iloc[0]) - 1) * 100

    abs_path_pct = float(recent["close"].pct_change().abs().sum() * 100) if len(recent) >= 2 else 0.0
    path_efficiency = abs(net_return_pct) / max(abs_path_pct, 1e-9)

    recent_start_date = recent["date"].iloc[0].strftime("%Y-%m-%d")
    recent_end_date = recent["date"].iloc[-1].strftime("%Y-%m-%d")
    recent_pivots = [pivot for pivot in pivots if pivot.date >= recent_start_date]
    recent_swings = build_swings(recent_pivots)
    recent_up_swings = sum(1 for swing in recent_swings if swing.direction == "up")
    recent_down_swings = sum(1 for swing in recent_swings if swing.direction == "down")

    recent_high = float(frame["close"].tail(60).max()) if len(frame) >= 60 else current_price
    recent_low = float(frame["close"].tail(60).min()) if len(frame) >= 60 else current_price
    breakout_up = current_price >= recent_high * 0.985 if recent_high else False
    breakout_down = current_price <= recent_low * 1.015 if recent_low else False

    return {
        "recent_start_date": recent_start_date,
        "recent_end_date": recent_end_date,
        "range_low": sanitize_float(range_low, 2),
        "range_high": sanitize_float(range_high, 2),
        "current_position_pct": sanitize_float(current_position_pct, 1),
        "amplitude_ratio": sanitize_float(amplitude_ratio, 2),
        "liquidity_ratio": sanitize_float(liquidity_ratio, 2),
        "net_return_pct": sanitize_float(net_return_pct, 2),
        "path_efficiency": sanitize_float(path_efficiency, 2),
        "recent_pivots": recent_pivots,
        "recent_swings": recent_swings,
        "recent_up_swings": recent_up_swings,
        "recent_down_swings": recent_down_swings,
        "breakout_up": breakout_up,
        "breakout_down": breakout_down,
    }


def pick_regime_anchor_date(
    label: str,
    metrics: dict[str, float | int | str | list[PivotPoint] | list[SwingSegment]],
    pivots: list[PivotPoint],
) -> str:
    recent_start_date = str(metrics.get("recent_start_date") or "")
    recent_pivots = metrics.get("recent_pivots", [])
    if not isinstance(recent_pivots, list):
        recent_pivots = []

    if label == "活跃波段区" and recent_pivots:
        return recent_pivots[0].date

    current_position_pct = float(metrics.get("current_position_pct") or 0.0)
    if label == "趋势推进区":
        anchor_kind = "low" if current_position_pct >= 50 else "high"
        anchor = find_recent_pivot(pivots, anchor_kind)
        if anchor:
            return anchor.date

    if recent_pivots:
        return recent_pivots[0].date
    if pivots:
        return pivots[-1].date
    return recent_start_date


def build_cycle_regime(frame: pd.DataFrame, pivots: list[PivotPoint]) -> CycleRegime:
    if frame.empty:
        return CycleRegime(
            label="待识别",
            action_label="等待样本",
            tone="neutral",
            since_date="",
            range_low=0.0,
            range_high=0.0,
            current_position_pct=0.0,
            amplitude_ratio=0.0,
            liquidity_ratio=0.0,
            path_efficiency=0.0,
            recent_swing_count=0,
            summary="暂无足够样本识别当前属于区域还是趋势。",
        )

    metrics = build_recent_regime_metrics(frame, pivots)
    amplitude_ratio = float(metrics["amplitude_ratio"])
    liquidity_ratio = float(metrics["liquidity_ratio"])
    range_low = float(metrics["range_low"])
    range_high = float(metrics["range_high"])
    width_pct = (range_high / range_low - 1) * 100 if range_low else 0.0
    current_position_pct = float(metrics["current_position_pct"])
    net_return_pct = float(metrics["net_return_pct"])
    path_efficiency = float(metrics["path_efficiency"])
    recent_swing_count = len(metrics["recent_swings"]) if isinstance(metrics["recent_swings"], list) else 0
    recent_up_swings = int(metrics["recent_up_swings"])
    recent_down_swings = int(metrics["recent_down_swings"])
    breakout_up = bool(metrics["breakout_up"])
    breakout_down = bool(metrics["breakout_down"])

    label = "低迷整理区"
    action_label = "降级观察"
    tone = "negative"
    summary = "当前仍偏低迷整理，量能和振幅没有形成持续优势，交易价值一般。"

    is_active_range = (
        amplitude_ratio >= 1.25
        and liquidity_ratio >= 1.10
        and 25 <= width_pct <= 120
        and 20 <= current_position_pct <= 80
        and recent_swing_count >= 2
        and recent_up_swings >= 1
        and recent_down_swings >= 1
        and abs(net_return_pct) <= 45
        and path_efficiency <= 0.25
    )
    is_trend = (
        width_pct >= 45
        and (current_position_pct >= 82 or current_position_pct <= 18 or abs(net_return_pct) >= 55 or breakout_up or breakout_down)
        and (recent_swing_count <= 1 or recent_up_swings == 0 or recent_down_swings == 0)
    )
    is_transition = amplitude_ratio >= 1.15 and width_pct >= 20

    if is_active_range:
        label = "活跃波段区"
        action_label = "低买高抛"
        tone = "positive"
    elif is_trend:
        label = "趋势推进区"
        action_label = "顺势跟踪"
        tone = "alert"
    elif is_transition:
        label = "区域切换区"
        action_label = "等待新区域"
        tone = "neutral"

    since_date = pick_regime_anchor_date(label, metrics, pivots)
    scoped = frame[frame["date"] >= pd.Timestamp(since_date)].copy() if since_date else frame.tail(80).copy()
    if scoped.empty:
        scoped = frame.tail(80).copy()

    scoped_low = float(scoped["close"].min()) if not scoped.empty else range_low
    scoped_high = float(scoped["close"].max()) if not scoped.empty else range_high
    current_price = float(scoped["close"].iloc[-1]) if not scoped.empty else 0.0
    scoped_position_pct = 0.0
    if scoped_high > scoped_low:
        scoped_position_pct = (current_price - scoped_low) / (scoped_high - scoped_low) * 100

    if label == "活跃波段区":
        summary = (
            f"自 {since_date} 起量能与振幅明显抬升，价格在 {scoped_low:.2f}-{scoped_high:.2f} 区间内反复换手。"
            f"当前位于区间 {scoped_position_pct:.0f}% 附近，更适合按边界低买高抛。"
        )
    elif label == "趋势推进区":
        direction = "向上" if current_position_pct >= 50 else "向下"
        summary = (
            f"自 {since_date} 起股价仍在从前一区域向新区域{direction}推进，当前还没找到新的稳定箱体。"
            "这类票更适合顺势跟踪，不适合机械等完美回调。"
        )
    elif label == "区域切换区":
        summary = (
            f"自 {since_date} 起振幅或流动性开始抬升，但新区域边界还不稳定。"
            "先观察它会沉淀成活跃波段区，还是继续发展成趋势推进区。"
        )

    return CycleRegime(
        label=label,
        action_label=action_label,
        tone=tone,
        since_date=since_date,
        range_low=sanitize_float(scoped_low, 2),
        range_high=sanitize_float(scoped_high, 2),
        current_position_pct=sanitize_float(scoped_position_pct, 1),
        amplitude_ratio=sanitize_float(amplitude_ratio, 2),
        liquidity_ratio=sanitize_float(liquidity_ratio, 2),
        path_efficiency=sanitize_float(path_efficiency, 2),
        recent_swing_count=recent_swing_count,
        summary=summary,
    )


def classify_score(score: int) -> tuple[str, str]:
    if score >= 70:
        return "明显规律", "保留长期跟踪"
    if score >= 55:
        return "可跟踪规律", "继续观察"
    if score >= 40:
        return "弱规律", "观察后决定"
    return "规律不明显", "候选淘汰"


def level_label_for_chart(level: str) -> str:
    mapping = {
        "明显规律": "Clear",
        "可跟踪规律": "Usable",
        "弱规律": "Weak",
        "规律不明显": "Unclear",
    }
    return mapping.get(level, level)


def find_recent_pivot(pivots: list[PivotPoint], kind: str) -> PivotPoint | None:
    for pivot in reversed(pivots):
        if pivot.kind == kind:
            return pivot
    return None


def assess_cycle_opportunity(frame: pd.DataFrame, pivots: list[PivotPoint]) -> CycleOpportunity:
    current_price = float(frame["close"].iloc[-1])
    current_date = frame["date"].iloc[-1].strftime("%Y-%m-%d")
    recent_low = find_recent_pivot(pivots, "low")
    recent_high = find_recent_pivot(pivots, "high")

    support_price = recent_low.price if recent_low else current_price
    resistance_price = recent_high.price if recent_high else current_price
    support_date = recent_low.date if recent_low else ""
    resistance_date = recent_high.date if recent_high else ""

    rebound_from_support = (current_price / support_price - 1) * 100 if support_price else 0.0
    drawdown_from_resistance = (current_price / resistance_price - 1) * 100 if resistance_price else 0.0
    distance_to_support = rebound_from_support
    distance_to_resistance = (resistance_price / current_price - 1) * 100 if current_price else 0.0

    if len(pivots) < 2 or not recent_low or not recent_high:
        return CycleOpportunity(
            current_price=sanitize_float(current_price, 2),
            current_date=current_date,
            phase_label="样本不足",
            action_label="等待更多波段",
            tone="neutral",
            summary="当前历史波段数量不足，先观察后续是否形成稳定节奏。",
            support_price=sanitize_float(support_price, 2),
            support_date=support_date,
            resistance_price=sanitize_float(resistance_price, 2),
            resistance_date=resistance_date,
            distance_to_support_pct=sanitize_float(distance_to_support, 2),
            distance_to_resistance_pct=sanitize_float(distance_to_resistance, 2),
            rebound_from_support_pct=sanitize_float(rebound_from_support, 2),
            drawdown_from_resistance_pct=sanitize_float(drawdown_from_resistance, 2),
        )

    last_pivot = pivots[-1]
    phase_label = "区间中位"
    action_label = "等待方向"
    tone = "neutral"
    summary = "当前位于前低和前高之间，先观察资金是否选择方向。"

    if distance_to_resistance < 0:
        phase_label = "突破前高"
        action_label = "跟踪回踩确认"
        tone = "positive"
        summary = (
            f"现价已站上最近高点 {resistance_date} 的 {resistance_price:.2f}，"
            "更适合等回踩确认而不是追高。"
        )
    elif last_pivot.kind == "low":
        if rebound_from_support <= 10 and distance_to_resistance >= 10:
            phase_label = "低点反弹初段"
            action_label = "关注买点"
            tone = "positive"
            summary = (
                f"距离最近低点 {support_date} 仅反弹 {rebound_from_support:.1f}%，"
                f"离最近高点仍有 {distance_to_resistance:.1f}% 空间。"
            )
        elif rebound_from_support <= 20 and distance_to_resistance >= 5:
            phase_label = "低点反弹中段"
            action_label = "继续跟踪"
            tone = "neutral"
            summary = (
                f"自最近低点已反弹 {rebound_from_support:.1f}%，"
                f"距离前高仍有 {distance_to_resistance:.1f}% 空间，适合观察量价延续。"
            )
        else:
            phase_label = "接近前高压力"
            action_label = "不追高"
            tone = "alert"
            summary = (
                f"最近低点反弹已走出 {rebound_from_support:.1f}%，"
                f"距前高仅剩 {max(distance_to_resistance, 0.0):.1f}% 空间，性价比下降。"
            )
    else:
        if distance_to_support <= 5:
            phase_label = "回踩支撑附近"
            action_label = "观察企稳买点"
            tone = "positive"
            summary = (
                f"距离最近低点 {support_date} 仅高出 {distance_to_support:.1f}%，"
                "如果量能和强度修复，容易形成试错买点。"
            )
        elif drawdown_from_resistance >= -4:
            phase_label = "高点附近"
            action_label = "不追高"
            tone = "alert"
            summary = (
                f"现价距离最近高点 {resistance_date} 仅回撤 {abs(drawdown_from_resistance):.1f}%，"
                "更适合等回踩，不适合直接追价。"
            )
        elif distance_to_support <= 12:
            phase_label = "高位回落中段"
            action_label = "等支撑确认"
            tone = "neutral"
            summary = (
                f"距离最近低点仍有 {distance_to_support:.1f}% 缓冲，"
                "先看是否在支撑区止跌再考虑介入。"
            )
        else:
            phase_label = "高位回撤"
            action_label = "继续等待"
            tone = "negative"
            summary = (
                f"现价较最近高点回撤 {abs(drawdown_from_resistance):.1f}%，"
                f"但距离最近低点还有 {distance_to_support:.1f}% 空间，暂不着急。"
            )

    return CycleOpportunity(
        current_price=sanitize_float(current_price, 2),
        current_date=current_date,
        phase_label=phase_label,
        action_label=action_label,
        tone=tone,
        summary=summary,
        support_price=sanitize_float(support_price, 2),
        support_date=support_date,
        resistance_price=sanitize_float(resistance_price, 2),
        resistance_date=resistance_date,
        distance_to_support_pct=sanitize_float(distance_to_support, 2),
        distance_to_resistance_pct=sanitize_float(distance_to_resistance, 2),
        rebound_from_support_pct=sanitize_float(rebound_from_support, 2),
        drawdown_from_resistance_pct=sanitize_float(drawdown_from_resistance, 2),
    )


def describe_latest_state(frame: pd.DataFrame, pivots: list[PivotPoint]) -> str:
    current_price = float(frame["close"].iloc[-1])
    current_date = frame["date"].iloc[-1].strftime("%Y-%m-%d")
    if not pivots:
        return f"{current_date} 收于 {current_price:.2f}，暂无清晰波段"

    last_pivot = pivots[-1]
    delta_pct = (current_price / last_pivot.price - 1) * 100
    if last_pivot.kind == "high":
        return f"距最近高点 {last_pivot.date} 回撤 {delta_pct:.1f}%"
    return f"距最近低点 {last_pivot.date} 反弹 {delta_pct:.1f}%"


def build_cycle_summary(symbol: str, name: str, frame: pd.DataFrame) -> CycleSummary:
    pivots = detect_cycle_pivots(frame)
    swings = build_swings(pivots)
    recent_cycles, current_cycle = build_cycle_windows(frame, pivots, swings)
    up_swings = [segment for segment in swings if segment.direction == "up"]
    down_swings = [segment for segment in swings if segment.direction == "down"]
    regime = build_cycle_regime(frame, pivots)
    opportunity = assess_cycle_opportunity(frame, pivots)

    avg_up_days = sanitize_float(sum(item.trading_days for item in up_swings) / len(up_swings), 1) if up_swings else 0.0
    avg_down_days = sanitize_float(sum(item.trading_days for item in down_swings) / len(down_swings), 1) if down_swings else 0.0
    avg_up_return = sanitize_float(sum(item.return_pct for item in up_swings) / len(up_swings), 2) if up_swings else 0.0
    avg_down_return = sanitize_float(sum(item.return_pct for item in down_swings) / len(down_swings), 2) if down_swings else 0.0

    duration_cv = cv([segment.trading_days for segment in swings])
    amplitude_cv = cv([abs(segment.return_pct) for segment in swings])
    balance_ratio = min(len(up_swings), len(down_swings)) / max(len(up_swings), len(down_swings), 1)
    average_amplitude = sum(abs(segment.return_pct) for segment in swings) / len(swings) if swings else 0.0
    recent_active_swings = sum(1 for segment in swings if segment.end_date >= "2025-01-01")

    swing_score = min(len(swings) / 8, 1.0) * 25
    duration_score = score_consistency(duration_cv, 1.2) * 25
    amplitude_score = score_consistency(amplitude_cv, 1.0) * 20
    balance_score = balance_ratio * 10
    amplitude_window_score = 10 if 12 <= average_amplitude <= 60 else 4 if 8 <= average_amplitude <= 80 else 0
    recent_score = min(recent_active_swings / 5, 1.0) * 10

    score = round(swing_score + duration_score + amplitude_score + balance_score + amplitude_window_score + recent_score)
    level, recommendation = classify_score(score)

    chart_path = STOCK_CHART_DIR / f"{symbol}-cycle.png"
    return CycleSummary(
        symbol=symbol,
        name=name,
        score=score,
        level=level,
        recommendation=recommendation,
        pivot_count=len(pivots),
        swing_count=len(swings),
        avg_up_days=avg_up_days,
        avg_down_days=avg_down_days,
        avg_up_return_pct=avg_up_return,
        avg_down_return_pct=avg_down_return,
        duration_cv=sanitize_float(duration_cv, 2),
        amplitude_cv=sanitize_float(amplitude_cv, 2),
        latest_state=describe_latest_state(frame, pivots),
        chart_path=str(chart_path.relative_to(ROOT)).replace("\\", "/"),
        grid_path=str(GRID_PATH.relative_to(ROOT)).replace("\\", "/"),
        regime=regime,
        opportunity=opportunity,
        recent_cycles=recent_cycles,
        current_cycle=current_cycle,
        pivots=pivots,
        swings=swings,
    )


def render_single_chart(frame: pd.DataFrame, summary: CycleSummary) -> None:
    chart_path = ROOT / summary.chart_path
    recent_pivots = summary.pivots[-8:]

    fig, ax = plt.subplots(figsize=(14, 7), dpi=170)
    fig.patch.set_facecolor("#0a0d14")
    ax.set_facecolor("#11151f")

    ax.plot(frame["date"], frame["close"], color="#f5edd7", linewidth=2.1, label="Close")
    ax.plot(frame["date"], frame["ma60"], color="#73c5ff", linewidth=1.3, alpha=0.95, label="MA60")

    for pivot in recent_pivots:
        dt = pd.Timestamp(pivot.date)
        color = "#f56d70" if pivot.kind == "high" else "#4bd08a"
        prefix = "H" if pivot.kind == "high" else "L"
        ax.scatter([dt], [pivot.price], s=26, color=color, zorder=5)
        ax.annotate(
            f"{pivot.date}\n{prefix} {pivot.price:.2f}",
            xy=(dt, pivot.price),
            xytext=(dt, pivot.price + (0.9 if pivot.kind == "low" else -0.9)),
            fontsize=8,
            color=color,
            ha="center",
            va="bottom" if pivot.kind == "low" else "top",
            arrowprops=dict(arrowstyle="-", color=color, lw=0.75, alpha=0.75),
            bbox=dict(boxstyle="round,pad=0.18", fc="#11151f", ec=color, lw=0.6, alpha=0.82),
        )

    ax.set_title(
        f"{summary.symbol} | score {summary.score} | {level_label_for_chart(summary.level)}",
        color="#f5edd7",
        fontsize=15,
        pad=14,
    )
    ax.set_ylabel("Adjusted close", color="#d8cfb8")
    ax.tick_params(colors="#c9d3e5")
    for spine in ax.spines.values():
        spine.set_color("#2b3545")
    ax.grid(True, color="#2b3545", linestyle="--", linewidth=0.6, alpha=0.4)
    legend = ax.legend(facecolor="#11151f", edgecolor="#2b3545", labelcolor="#f5edd7")
    for text in legend.get_texts():
        text.set_color("#f5edd7")

    metrics = (
        f"Swings: {summary.swing_count}\n"
        f"Avg up: {summary.avg_up_days:.1f} td / {summary.avg_up_return_pct:.1f}%\n"
        f"Avg down: {summary.avg_down_days:.1f} td / {summary.avg_down_return_pct:.1f}%\n"
        f"Duration CV: {summary.duration_cv:.2f}\n"
        f"Amplitude CV: {summary.amplitude_cv:.2f}"
    )
    ax.text(
        0.013,
        0.03,
        metrics,
        transform=ax.transAxes,
        fontsize=9.2,
        color="#f5edd7",
        bbox=dict(boxstyle="round,pad=0.4", fc="#0d1117", ec="#2b3545", alpha=0.92),
    )

    plt.tight_layout()
    chart_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(chart_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def render_grid(reports: list[CycleSummary], frames: dict[str, pd.DataFrame]) -> None:
    columns = 5
    rows = math.ceil(len(reports) / columns)
    fig, axes = plt.subplots(rows, columns, figsize=(18, rows * 3.3), dpi=160)
    fig.patch.set_facecolor("#0a0d14")
    axes_list = list(axes.flat) if hasattr(axes, "flat") else [axes]

    for ax in axes_list:
        ax.set_facecolor("#11151f")

    for ax, report in zip(axes_list, reports):
        frame = frames[report.symbol]
        ax.plot(frame["date"], frame["close"], color="#f5edd7", linewidth=1.2)
        ax.plot(frame["date"], frame["ma60"], color="#73c5ff", linewidth=0.9, alpha=0.85)
        for pivot in report.pivots[-4:]:
            color = "#f56d70" if pivot.kind == "high" else "#4bd08a"
            ax.scatter([pd.Timestamp(pivot.date)], [pivot.price], s=10, color=color, zorder=4)

        title_color = "#4bd08a" if report.score >= 70 else "#f5b73a" if report.score >= 55 else "#f56d70"
        ax.set_title(f"{report.symbol} {report.score}", color=title_color, fontsize=9.5, pad=4)
        ax.tick_params(colors="#6f7a8c", labelsize=7)
        ax.grid(True, color="#2b3545", linestyle="--", linewidth=0.35, alpha=0.35)
        for spine in ax.spines.values():
            spine.set_color("#2b3545")
        ax.set_xticklabels([])
        ax.text(
            0.02,
            0.05,
            level_label_for_chart(report.level),
            transform=ax.transAxes,
            fontsize=7.5,
            color="#c9d3e5",
            bbox=dict(boxstyle="round,pad=0.15", fc="#0d1117", ec="#2b3545", alpha=0.8),
        )

    for ax in axes_list[len(reports):]:
        ax.axis("off")

    fig.suptitle("Watchlist Cycle Grid | 2024-02-01 to today", color="#f5edd7", fontsize=15)
    plt.tight_layout()
    fig.savefig(GRID_PATH, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def write_summary_markdown(reports: list[CycleSummary]) -> None:
    keep_list = [report for report in reports if report.score >= 55]
    watch_list = [report for report in reports if 40 <= report.score < 55]
    drop_list = [report for report in reports if report.score < 40]

    lines = [
        "# 自选池波峰波谷周期分析",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"观察区间：{START_DATE[:4]}-{START_DATE[4:6]}-{START_DATE[6:]} 至今",
        "",
        "## 解释口径",
        "",
        "- `score`：波段规律清晰度，越高越容易长期熟悉。",
        "- `明显规律 / 可跟踪规律`：更适合留在自选池长期观察。",
        "- `弱规律 / 规律不明显`：说明节奏散、波段不稳定，属于候选淘汰对象。",
        f"- 总览图：[{GRID_PATH.name}](./{GRID_PATH.name})",
        "",
        "## 建议保留",
        "",
        "| 代码 | 名称 | score | 周期判断 | 当前状态区 | 最新状态 | 图 |",
        "| --- | --- | ---: | --- | --- | --- | --- |",
    ]

    for report in keep_list:
        lines.append(
            f"| {report.symbol} | {report.name} | {report.score} | {report.level} | {report.regime.label} | {report.latest_state} | "
            f"[图](./stocks/{report.symbol}-cycle.png) |"
        )

    lines.extend(
        [
            "",
            "## 观察后决定",
            "",
            "| 代码 | 名称 | score | 周期判断 | 当前状态区 | 最新状态 | 图 |",
            "| --- | --- | ---: | --- | --- | --- | --- |",
        ]
    )
    for report in watch_list:
        lines.append(
            f"| {report.symbol} | {report.name} | {report.score} | {report.level} | {report.regime.label} | {report.latest_state} | "
            f"[图](./stocks/{report.symbol}-cycle.png) |"
        )

    lines.extend(
        [
            "",
            "## 候选淘汰",
            "",
            "| 代码 | 名称 | score | 周期判断 | 当前状态区 | 最新状态 | 图 |",
            "| --- | --- | ---: | --- | --- | --- | --- |",
        ]
    )
    for report in drop_list:
        lines.append(
            f"| {report.symbol} | {report.name} | {report.score} | {report.level} | {report.regime.label} | {report.latest_state} | "
            f"[图](./stocks/{report.symbol}-cycle.png) |"
        )

    lines.extend(
        [
            "",
            "## 全量明细",
            "",
            "| 代码 | 名称 | score | 当前状态区 | 波峰波谷数 | 波段数 | 平均上涨天数 | 平均下跌天数 | 平均上涨幅度 | 平均下跌幅度 | Duration CV | Amplitude CV | 建议 |",
            "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for report in reports:
        lines.append(
            f"| {report.symbol} | {report.name} | {report.score} | {report.regime.label} | {report.pivot_count} | {report.swing_count} | "
            f"{report.avg_up_days:.1f} | {report.avg_down_days:.1f} | {report.avg_up_return_pct:.1f}% | "
            f"{report.avg_down_return_pct:.1f}% | {report.duration_cv:.2f} | {report.amplitude_cv:.2f} | {report.recommendation} |"
        )

    SUMMARY_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_json_report(reports: list[CycleSummary]) -> None:
    payload = {
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "startDate": START_DATE,
        "endDate": END_DATE,
        "reports": [
            {
                **{key: value for key, value in asdict(report).items() if key not in {"pivots", "swings"}},
                "pivots": [asdict(item) for item in report.pivots],
                "swings": [asdict(item) for item in report.swings],
            }
            for report in reports
        ],
    }
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    ensure_output_dirs()
    codes = fw.read_codes()
    manual_name_map = fw.read_watchlist_name_map()
    snapshot_map = fw.load_snapshot_stock_map()
    try:
        fetched_name_map = fw.fetch_name_map(codes)
    except Exception:
        fetched_name_map = {}

    reports: list[CycleSummary] = []
    frames: dict[str, pd.DataFrame] = {}
    for code in codes:
        frame = prepare_history_frame(code)
        if frame.empty:
            continue

        frames[code] = frame
        name = (
            snapshot_map.get(code).name
            if code in snapshot_map
            else fetched_name_map.get(code) or manual_name_map.get(code, code)
        )
        report = build_cycle_summary(code, name, frame)
        reports.append(report)
        render_single_chart(frame, report)

    reports.sort(key=lambda item: item.score, reverse=True)
    render_grid(reports, frames)
    write_summary_markdown(reports)
    write_json_report(reports)

    print(f"周期分析已写入：{SUMMARY_PATH}")
    print(f"总览图：{GRID_PATH}")
    print(f"JSON 报告：{JSON_PATH}")


if __name__ == "__main__":
    main()
