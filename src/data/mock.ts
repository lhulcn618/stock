import akshareSnapshot from "./akshare-snapshot.json";
import { watchlistSeeds } from "./watchlist";
import type { DashboardSnapshot, WatchStock } from "../types";

const notePool = [
  "Watch whether the tape confirms the setup into the close.",
  "Keep this on radar for a stronger volume expansion day.",
  "Trend structure is constructive, but confirmation still matters.",
  "A clean follow-through day would improve confidence.",
  "Treat this as a tracking name until price and volume align."
];

const thesisPool = [
  "Track whether sector strength is broadening around this name.",
  "Use daily structure and turnover to judge conviction.",
  "Focus on whether the current swing can hold above recent support.",
  "Keep this in the pool for momentum confirmation rather than prediction.",
  "A stronger close and cleaner breadth would upgrade the setup."
];

const snapshot = akshareSnapshot as DashboardSnapshot;

function createSparkline(seed: number) {
  return Array.from({ length: 8 }, (_, index) => {
    const base = 6 + (seed % 9) * 0.35;
    const slope = index * (0.22 + (seed % 5) * 0.04);
    const wobble = ((seed + index * 3) % 4) * 0.08;
    return Number((base + slope + wobble).toFixed(2));
  });
}

function buildFallbackStock(code: string, index: number): WatchStock {
  const numericSeed = Number(code.slice(-3)) || index * 17 + 11;
  const changePct = Number((((numericSeed % 17) - 6) * 0.43).toFixed(2));
  const price = Number((12 + (numericSeed % 220) * 1.17).toFixed(2));
  const momentum = 48 + (numericSeed % 44);
  const volumeRatio = Number((0.78 + (numericSeed % 9) * 0.11).toFixed(2));
  const signalLevel = changePct >= 2 ? "strong" : changePct >= 0 ? "watch" : "calm";

  return {
    symbol: code,
    name: code,
    market: "CN",
    sector: "Watchlist",
    price,
    changePct,
    momentum,
    volumeRatio,
    note: notePool[index % notePool.length],
    thesis: thesisPool[index % thesisPool.length],
    sparkline: createSparkline(numericSeed),
    signals: [
      { label: "Change", value: `${changePct >= 0 ? "+" : ""}${changePct.toFixed(2)}%`, level: signalLevel },
      { label: "Momentum", value: String(momentum), level: momentum >= 75 ? "strong" : "watch" },
      { label: "Volume", value: `${volumeRatio.toFixed(2)}x`, level: volumeRatio >= 1.2 ? "strong" : "calm" }
    ]
  };
}

export function getFallbackSnapshot(): DashboardSnapshot {
  const stocks = watchlistSeeds.map((item, index) => buildFallbackStock(item.code, index));
  const averageChange = stocks.reduce((sum, stock) => sum + stock.changePct, 0) / stocks.length;

  return {
    syncTime: "2026-03-12 16:30",
    watchlistCount: stocks.length,
    strongSignals: stocks.filter((stock) => stock.signals.some((signal) => signal.level === "strong")).length,
    avgChange: Number(averageChange.toFixed(2)),
    mood: averageChange >= 0 ? "risk-on" : "mixed",
    stocks
  };
}

export function getInitialSnapshot(): DashboardSnapshot {
  return snapshot.stocks.length > 0 ? snapshot : getFallbackSnapshot();
}
