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

export interface BollingerPoint {
  date: string;
  middle: number;
  upper: number;
  lower: number;
}

export interface BollingerProfile {
  period: number;
  stdMultiplier: number;
  points: BollingerPoint[];
}

export interface ChipDistributionBand {
  price: number;
  ratio: number;
}

export interface ChipControlEvidence {
  key: string;
  label: string;
  value: string;
  tone: IndicatorTone;
  summary: string;
}

export interface ChipDistributionProfile {
  algorithm: string;
  bucketSize: number;
  sampleSize: number;
  tradeDate: string;
  mainCost: number;
  mainCostZoneLow: number;
  mainCostZoneHigh: number;
  mainCostZoneWidthPct: number;
  averageCost: number;
  winnerRatio: number;
  dominantRatio: number;
  concentration70Low: number;
  concentration70High: number;
  concentration90Low: number;
  concentration90High: number;
  currentPriceBiasPct: number;
  shapeLabel: string;
  stageLabel: string;
  riskLabel: string;
  tone: IndicatorTone;
  summary: string;
  controlEvidence: ChipControlEvidence[];
  bands: ChipDistributionBand[];
}

export interface ThemeHotspot {
  boardType: "industry" | "concept" | "etf";
  name: string;
  code: string;
  rank: number;
  changePct: number;
  riseCount: number;
  fallCount: number;
  leaderName: string;
  leaderCode: string;
  leaderChangePct: number;
  matchReason: string;
}

export interface StockThemeLinkage {
  updatedAt: string;
  industry: string;
  concepts: string[];
  matchedKeywords: string[];
  hotBoards: ThemeHotspot[];
  relatedEtfs: ThemeHotspot[];
  summary: string;
}

export interface UsFocusItem {
  key: string;
  name: string;
  symbol: string;
  category: string;
  lastTradeDate: string;
  close: number;
  prevClose: number;
  changePct: number;
  high: number;
  low: number;
  volume: number;
  tone: IndicatorTone;
  summary: string;
  news: NewsInsightItem[];
}

export interface UsMarketPulse {
  updatedAt: string;
  tradeDate: string;
  summary: string;
  items: UsFocusItem[];
}

export interface MarketBreadthPoint {
  timestamp: string;
  totalUp: number;
  totalDown: number;
  limitUp: number;
  limitDown: number;
  flatCount: number;
  netAdvance: number;
}

export interface MarketBreadthProfile {
  updatedAt: string;
  tradeDate: string;
  activityPct: number;
  upCount: number;
  downCount: number;
  flatCount: number;
  limitUpCount: number;
  limitDownCount: number;
  netAdvance: number;
  advanceDeclineRatio: number;
  breadthLow: number;
  breadthHigh: number;
  tone: IndicatorTone;
  signalLabel: string;
  summary: string;
  trendPoints: MarketBreadthPoint[];
}

export interface MarketRadar {
  updatedAt: string;
  hottestBoards: ThemeHotspot[];
  hottestEtfs: ThemeHotspot[];
  usMarketPulse: UsMarketPulse;
  marketBreadth: MarketBreadthProfile;
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

export interface CycleWindow {
  label: string;
  direction: "up" | "down";
  startDate: string;
  endDate: string;
  tradingDays: number;
  returnPct: number;
  status: "completed" | "ongoing";
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

export interface CycleRegime {
  label: string;
  actionLabel: string;
  tone: IndicatorTone;
  sinceDate: string;
  rangeLow: number;
  rangeHigh: number;
  currentPositionPct: number;
  amplitudeRatio: number;
  liquidityRatio: number;
  pathEfficiency: number;
  recentSwingCount: number;
  summary: string;
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
  regime: CycleRegime;
  opportunity: CycleOpportunity;
  recentCycles: CycleWindow[];
  currentCycle: CycleWindow;
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

export interface CandlePoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  isLimitUpClose: boolean;
}

export interface LimitUpSignalProfile {
  recentLimitUpCount10: number;
  isHoldingAboveOpen: boolean;
  anchorDate: string;
  anchorOpen: number;
  anchorClose: number;
  holdDays: number;
  currentBiasPct: number;
  tone: IndicatorTone;
  summary: string;
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
  candles: CandlePoint[];
  limitUpSignal: LimitUpSignalProfile;
  bollinger: BollingerProfile;
  chipDistribution: ChipDistributionProfile;
  signals: WatchSignal[];
  metadata: StockMetadata;
  companyInsight?: CompanyInsight;
  technicals: TechnicalIndicators;
  selectionScore: SelectionScore;
  cycleAnalysis?: CycleAnalysis;
  priceDistribution: PriceDistributionProfile;
  amplitudeDistribution: AmplitudeDistributionProfile;
  themeLinkage?: StockThemeLinkage;
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
  marketRadar?: MarketRadar;
}
