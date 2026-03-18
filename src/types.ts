export type SignalLevel = "calm" | "watch" | "strong";

export interface WatchSignal {
  label: string;
  value: string;
  level: SignalLevel;
}

export interface PriceDistributionBand {
  index: number;
  lower: number;
  upper: number;
  closeCount: number;
  ratio: number;
  rangeLabel: string;
}

export interface PriceDistributionProfile {
  yearHigh: number;
  yearLow: number;
  sampleSize: number;
  currentBand: number;
  dominantBand: number;
  currentPositionPct: number;
  bands: PriceDistributionBand[];
}

export interface AmplitudeDistributionProfile {
  boardType: string;
  marketCapYi: number;
  marketCapBucket: string;
  amplitudeCap: number;
  currentAmplitude: number;
  sampleSize: number;
  currentBand: number;
  dominantBand: number;
  bands: PriceDistributionBand[];
}

export interface StockMetadata {
  officialWebsite: string;
  websiteSource: string;
}

export type IndicatorTone = "positive" | "negative" | "neutral" | "alert";

export interface AccountingBusinessSegment {
  name: string;
  revenueYi: number;
  revenueRatio: number;
  profitYi: number;
  profitRatio: number;
  grossMargin: number;
}

export interface AccountingBusinessInsight {
  reportDate: string;
  classification: string;
  summary: string;
  segments: AccountingBusinessSegment[];
}

export interface OfficialBusinessInsight {
  companyName: string;
  industry: string;
  mainBusiness: string;
  businessScope: string;
  companyIntro: string;
}

export interface NewsInsightItem {
  title: string;
  publishTime: string;
  source: string;
  url: string;
  excerpt: string;
  matchedKeywords: string[];
}

export interface NewsSensitivityInsight {
  score: number;
  level: string;
  summary: string;
  matchedKeywords: string[];
  items: NewsInsightItem[];
}

export interface ResearchInsightItem {
  date: string;
  institution: string;
  rating: string;
  title: string;
  industry: string;
  reportUrl: string;
}

export interface ResearchFocusInsight {
  monthlyReportCount: number;
  summary: string;
  focusKeywords: string[];
  items: ResearchInsightItem[];
}

export interface CompanyInsight {
  updatedAt: string;
  accountingBusiness: AccountingBusinessInsight;
  officialBusiness: OfficialBusinessInsight;
  newsSensitivity: NewsSensitivityInsight;
  researchFocus: ResearchFocusInsight;
}

export interface MacdIndicator {
  dif: number;
  dea: number;
  histogram: number;
  signalLabel: string;
  biasLabel: string;
  tone: IndicatorTone;
}

export interface RsiIndicator {
  period: number;
  value: number;
  signalLabel: string;
  biasLabel: string;
  tone: IndicatorTone;
}

export interface TechnicalIndicators {
  macd: MacdIndicator;
  rsi14: RsiIndicator;
}

export interface CyclePivot {
  kind: "high" | "low";
  index: number;
  date: string;
  price: number;
}

export interface CycleSwing {
  direction: "up" | "down";
  startDate: string;
  endDate: string;
  tradingDays: number;
  returnPct: number;
}

export interface CycleOpportunity {
  currentPrice: number;
  currentDate: string;
  phaseLabel: string;
  actionLabel: string;
  tone: IndicatorTone;
  summary: string;
  supportPrice: number;
  supportDate: string;
  resistancePrice: number;
  resistanceDate: string;
  distanceToSupportPct: number;
  distanceToResistancePct: number;
  reboundFromSupportPct: number;
  drawdownFromResistancePct: number;
}

export interface CycleAnalysis {
  generatedAt: string;
  startDate: string;
  endDate: string;
  score: number;
  level: string;
  recommendation: string;
  pivotCount: number;
  swingCount: number;
  avgUpDays: number;
  avgDownDays: number;
  avgUpReturnPct: number;
  avgDownReturnPct: number;
  durationCv: number;
  amplitudeCv: number;
  latestState: string;
  chartPath: string;
  opportunity: CycleOpportunity;
  pivots: CyclePivot[];
  swings: CycleSwing[];
}

export interface ScoreFactor {
  key: string;
  label: string;
  score: number;
  maxScore: number;
  tone: IndicatorTone;
  summary: string;
}

export interface SelectionScore {
  total: number;
  maxScore: number;
  grade: string;
  summary: string;
  factors: ScoreFactor[];
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
  metadata: StockMetadata;
  companyInsight?: CompanyInsight;
  technicals: TechnicalIndicators;
  selectionScore: SelectionScore;
  cycleAnalysis?: CycleAnalysis;
  priceDistribution: PriceDistributionProfile;
  amplitudeDistribution: AmplitudeDistributionProfile;
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
