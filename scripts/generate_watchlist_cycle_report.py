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
    opportunity: CycleOpportunity
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
    up_swings = [segment for segment in swings if segment.direction == "up"]
    down_swings = [segment for segment in swings if segment.direction == "down"]
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
        opportunity=opportunity,
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
        "| 代码 | 名称 | score | 周期判断 | 最新状态 | 图 |",
        "| --- | --- | ---: | --- | --- | --- |",
    ]

    for report in keep_list:
        lines.append(
            f"| {report.symbol} | {report.name} | {report.score} | {report.level} | {report.latest_state} | "
            f"[图](./stocks/{report.symbol}-cycle.png) |"
        )

    lines.extend(
        [
            "",
            "## 观察后决定",
            "",
            "| 代码 | 名称 | score | 周期判断 | 最新状态 | 图 |",
            "| --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for report in watch_list:
        lines.append(
            f"| {report.symbol} | {report.name} | {report.score} | {report.level} | {report.latest_state} | "
            f"[图](./stocks/{report.symbol}-cycle.png) |"
        )

    lines.extend(
        [
            "",
            "## 候选淘汰",
            "",
            "| 代码 | 名称 | score | 周期判断 | 最新状态 | 图 |",
            "| --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for report in drop_list:
        lines.append(
            f"| {report.symbol} | {report.name} | {report.score} | {report.level} | {report.latest_state} | "
            f"[图](./stocks/{report.symbol}-cycle.png) |"
        )

    lines.extend(
        [
            "",
            "## 全量明细",
            "",
            "| 代码 | 名称 | score | 波峰波谷数 | 波段数 | 平均上涨天数 | 平均下跌天数 | 平均上涨幅度 | 平均下跌幅度 | Duration CV | Amplitude CV | 建议 |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for report in reports:
        lines.append(
            f"| {report.symbol} | {report.name} | {report.score} | {report.pivot_count} | {report.swing_count} | "
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
