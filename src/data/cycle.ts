import embeddedCycleReport from "../../docs/cycles/watchlist-cycle-report.json";
import type { CycleAnalysis, CycleOpportunity, CyclePivot, CycleSwing, DashboardSnapshot, IndicatorTone, WatchStock } from "../types";

interface RawCycleEntry {
  symbol?: unknown;
  score?: unknown;
  level?: unknown;
  recommendation?: unknown;
  pivot_count?: unknown;
  swing_count?: unknown;
  avg_up_days?: unknown;
  avg_down_days?: unknown;
  avg_up_return_pct?: unknown;
  avg_down_return_pct?: unknown;
  duration_cv?: unknown;
  amplitude_cv?: unknown;
  latest_state?: unknown;
  chart_path?: unknown;
  opportunity?: unknown;
  pivots?: unknown;
  swings?: unknown;
}

interface RawCycleReport {
  generatedAt?: unknown;
  startDate?: unknown;
  endDate?: unknown;
  reports?: unknown;
}

function normalizeString(value: unknown, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function normalizeNumber(value: unknown, fallback = 0) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function normalizeTone(value: unknown): IndicatorTone {
  return value === "positive" || value === "negative" || value === "alert" ? value : "neutral";
}

function normalizePivot(value: unknown): CyclePivot {
  if (!value || typeof value !== "object") {
    return {
      kind: "low",
      index: 0,
      date: "",
      price: 0
    };
  }

  const candidate = value as Partial<CyclePivot>;
  return {
    kind: candidate.kind === "high" ? "high" : "low",
    index: normalizeNumber(candidate.index),
    date: normalizeString(candidate.date),
    price: normalizeNumber(candidate.price)
  };
}

function normalizeSwing(value: unknown): CycleSwing {
  if (!value || typeof value !== "object") {
    return {
      direction: "up",
      startDate: "",
      endDate: "",
      tradingDays: 0,
      returnPct: 0
    };
  }

  const candidate = value as Record<string, unknown>;
  return {
    direction: candidate.direction === "down" ? "down" : "up",
    startDate: normalizeString(candidate.start_date),
    endDate: normalizeString(candidate.end_date),
    tradingDays: normalizeNumber(candidate.trading_days),
    returnPct: normalizeNumber(candidate.return_pct)
  };
}

function normalizeOpportunity(value: unknown): CycleOpportunity {
  if (!value || typeof value !== "object") {
    return {
      currentPrice: 0,
      currentDate: "",
      phaseLabel: "待分析",
      actionLabel: "等待周期报告",
      tone: "neutral",
      summary: "暂无买点判断",
      supportPrice: 0,
      supportDate: "",
      resistancePrice: 0,
      resistanceDate: "",
      distanceToSupportPct: 0,
      distanceToResistancePct: 0,
      reboundFromSupportPct: 0,
      drawdownFromResistancePct: 0
    };
  }

  const candidate = value as Record<string, unknown>;
  return {
    currentPrice: normalizeNumber(candidate.current_price),
    currentDate: normalizeString(candidate.current_date),
    phaseLabel: normalizeString(candidate.phase_label, "待分析"),
    actionLabel: normalizeString(candidate.action_label, "等待周期报告"),
    tone: normalizeTone(candidate.tone),
    summary: normalizeString(candidate.summary, "暂无买点判断"),
    supportPrice: normalizeNumber(candidate.support_price),
    supportDate: normalizeString(candidate.support_date),
    resistancePrice: normalizeNumber(candidate.resistance_price),
    resistanceDate: normalizeString(candidate.resistance_date),
    distanceToSupportPct: normalizeNumber(candidate.distance_to_support_pct),
    distanceToResistancePct: normalizeNumber(candidate.distance_to_resistance_pct),
    reboundFromSupportPct: normalizeNumber(candidate.rebound_from_support_pct),
    drawdownFromResistancePct: normalizeNumber(candidate.drawdown_from_resistance_pct)
  };
}

function createFallbackCycleAnalysis(stock: WatchStock): CycleAnalysis {
  return {
    generatedAt: "",
    startDate: "",
    endDate: "",
    score: 0,
    level: "待分析",
    recommendation: "等待周期报告",
    pivotCount: 0,
    swingCount: 0,
    avgUpDays: 0,
    avgDownDays: 0,
    avgUpReturnPct: 0,
    avgDownReturnPct: 0,
    durationCv: 0,
    amplitudeCv: 0,
    latestState: `${stock.symbol} 暂无周期分析结果`,
    chartPath: "",
    opportunity: {
      currentPrice: stock.price,
      currentDate: "",
      phaseLabel: "待分析",
      actionLabel: "等待周期报告",
      tone: "neutral",
      summary: "暂无买点判断",
      supportPrice: 0,
      supportDate: "",
      resistancePrice: 0,
      resistanceDate: "",
      distanceToSupportPct: 0,
      distanceToResistancePct: 0,
      reboundFromSupportPct: 0,
      drawdownFromResistancePct: 0
    },
    pivots: [],
    swings: []
  };
}

function normalizeCycleReport(value: unknown) {
  const candidate = (value && typeof value === "object" ? value : {}) as RawCycleReport;
  const generatedAt = normalizeString(candidate.generatedAt);
  const startDate = normalizeString(candidate.startDate);
  const endDate = normalizeString(candidate.endDate);
  const reports = Array.isArray(candidate.reports) ? candidate.reports : [];

  const bySymbol = new Map<string, CycleAnalysis>();

  reports.forEach((entry) => {
    const raw = (entry && typeof entry === "object" ? entry : {}) as RawCycleEntry;
    const symbol = normalizeString(raw.symbol);
    if (!symbol) {
      return;
    }

    bySymbol.set(symbol, {
      generatedAt,
      startDate,
      endDate,
      score: normalizeNumber(raw.score),
      level: normalizeString(raw.level, "待分析"),
      recommendation: normalizeString(raw.recommendation, "等待周期报告"),
      pivotCount: normalizeNumber(raw.pivot_count),
      swingCount: normalizeNumber(raw.swing_count),
      avgUpDays: normalizeNumber(raw.avg_up_days),
      avgDownDays: normalizeNumber(raw.avg_down_days),
      avgUpReturnPct: normalizeNumber(raw.avg_up_return_pct),
      avgDownReturnPct: normalizeNumber(raw.avg_down_return_pct),
      durationCv: normalizeNumber(raw.duration_cv),
      amplitudeCv: normalizeNumber(raw.amplitude_cv),
      latestState: normalizeString(raw.latest_state),
      chartPath: normalizeString(raw.chart_path),
      opportunity: normalizeOpportunity(raw.opportunity),
      pivots: Array.isArray(raw.pivots) ? raw.pivots.map(normalizePivot) : [],
      swings: Array.isArray(raw.swings) ? raw.swings.map(normalizeSwing) : []
    });
  });

  return bySymbol;
}

export function getEmbeddedCycleReport(): unknown {
  return embeddedCycleReport;
}

export function applyCycleAnalysis(snapshot: DashboardSnapshot, cycleSource: unknown = embeddedCycleReport): DashboardSnapshot {
  const cycleIndex = normalizeCycleReport(cycleSource);

  return {
    ...snapshot,
    stocks: snapshot.stocks.map((stock) => ({
      ...stock,
      cycleAnalysis: cycleIndex.get(stock.symbol) ?? createFallbackCycleAnalysis(stock)
    }))
  };
}
