export type SignalLevel = "calm" | "watch" | "strong";

export interface WatchSignal {
  label: string;
  value: string;
  level: SignalLevel;
}

export interface WatchStock {
  symbol: string;
  name: string;
  market: string;
  sector: string;
  price: number;
  changePct: number;
  momentum: number;
  volumeRatio: number;
  note: string;
  thesis: string;
  sparkline: number[];
  signals: WatchSignal[];
}

export interface MarketSummary {
  syncTime: string;
  watchlistCount: number;
  strongSignals: number;
  avgChange: number;
  mood: string;
}

export interface DashboardSnapshot extends MarketSummary {
  stocks: WatchStock[];
}
