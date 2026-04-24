import akshareSnapshot from "./akshare-snapshot.json";
import { applyCycleAnalysis } from "./cycle";
import { watchlistSeeds } from "./watchlist";
import type {
  AccountingBusinessInsight,
  BollingerPoint,
  BollingerProfile,
  ChipDistributionBand,
  ChipControlEvidence,
  ChipDistributionProfile,
  CompanyInsight,
  AmplitudeDistributionProfile,
  CandlePoint,
  DashboardSnapshot,
  IndicatorTone,
  LimitUpSignalProfile,
  MacdIndicator,
  MarketBreadthPoint,
  MarketBreadthProfile,
  MarketRadar,
  NewsSensitivityInsight,
  OfficialBusinessInsight,
  PriceDistributionBand,
  PriceDistributionProfile,
  ResearchFocusInsight,
  RsiIndicator,
  ScoreFactor,
  SelectionScore,
  StockThemeLinkage,
  StockMetadata,
  TechnicalIndicators,
  ThemeHotspot,
  UsFocusItem,
  UsMarketPulse,
  WatchStock
} from "../types";

const notePool = [
  "收盘前观察盘口是否确认当前形态。",
  "继续跟踪，等待更强的放量日。",
  "趋势结构尚可，但仍需进一步确认。",
  "若出现干净的延续日，信号可信度会更高。",
  "在价量重新共振前，先作为跟踪标的。"
];

const thesisPool = [
  "观察该股周边板块强度是否继续扩散。",
  "结合日线结构与换手强度判断资金共识。",
  "重点看当前波段能否站稳近期支撑。",
  "保留在自选池中，等待动能确认，而不是提前预判。",
  "若收盘更强、板块扩散更清晰，可上调关注级别。"
];

function normalizeStockMetadata(value: unknown): StockMetadata {
  if (!value || typeof value !== "object") {
    return {
      officialWebsite: "",
      websiteSource: ""
    };
  }

  const candidate = value as Partial<StockMetadata>;
  return {
    officialWebsite: typeof candidate.officialWebsite === "string" ? candidate.officialWebsite : "",
    websiteSource: typeof candidate.websiteSource === "string" ? candidate.websiteSource : ""
  };
}

function createDefaultAccountingBusinessInsight(): AccountingBusinessInsight {
  return {
    reportDate: "",
    classification: "",
    summary: "暂无会计主营拆分数据",
    segments: []
  };
}

function createDefaultOfficialBusinessInsight(): OfficialBusinessInsight {
  return {
    companyName: "",
    industry: "",
    mainBusiness: "",
    businessScope: "",
    companyIntro: ""
  };
}

function createDefaultNewsSensitivityInsight(): NewsSensitivityInsight {
  return {
    score: 0,
    level: "低",
    summary: "暂无新闻与政策敏感度样本",
    matchedKeywords: [],
    items: []
  };
}

function createDefaultResearchFocusInsight(): ResearchFocusInsight {
  return {
    monthlyReportCount: 0,
    summary: "暂无券商研报样本",
    focusKeywords: [],
    items: []
  };
}

function createDefaultCompanyInsight(): CompanyInsight {
  return {
    updatedAt: "",
    accountingBusiness: createDefaultAccountingBusinessInsight(),
    officialBusiness: createDefaultOfficialBusinessInsight(),
    newsSensitivity: createDefaultNewsSensitivityInsight(),
    researchFocus: createDefaultResearchFocusInsight()
  };
}

function createDefaultTechnicals(): TechnicalIndicators {
  return {
    macd: {
      dif: 0,
      dea: 0,
      histogram: 0,
      signalLabel: "无数据",
      biasLabel: "等待样本",
      tone: "neutral"
    },
    rsi14: {
      period: 9,
      value: 50,
      signalLabel: "无数据",
      biasLabel: "等待样本",
      tone: "neutral"
    }
  };
}

function createDefaultBollinger(): BollingerProfile {
  return {
    period: 30,
    stdMultiplier: 2,
    points: []
  };
}

function createDefaultChipDistribution(currentPrice = 0): ChipDistributionProfile {
  const price = Number(currentPrice.toFixed(2));
  return {
    algorithm: "turnover_decay_v1",
    bucketSize: 0.1,
    sampleSize: 0,
    tradeDate: "",
    mainCost: price,
    mainCostZoneLow: price,
    mainCostZoneHigh: price,
    mainCostZoneWidthPct: 0,
    averageCost: price,
    winnerRatio: 0,
    dominantRatio: 0,
    concentration70Low: price,
    concentration70High: price,
    concentration90Low: price,
    concentration90High: price,
    currentPriceBiasPct: 0,
    shapeLabel: "筹码待观察",
    stageLabel: "等待样本",
    riskLabel: "暂无主力成本区样本",
    tone: "neutral",
    summary: "暂无筹码分布样本",
    controlEvidence: [],
    bands: []
  };
}

function createDefaultSelectionScore(): SelectionScore {
  return {
    total: 0,
    maxScore: 100,
    grade: "D",
    summary: "等待更多信号",
    factors: []
  };
}

function createDefaultThemeHotspot(): ThemeHotspot {
  return {
    boardType: "concept",
    name: "",
    code: "",
    rank: 0,
    changePct: 0,
    riseCount: 0,
    fallCount: 0,
    leaderName: "",
    leaderCode: "",
    leaderChangePct: 0,
    matchReason: ""
  };
}

function createDefaultStockThemeLinkage(): StockThemeLinkage {
  return {
    updatedAt: "",
    industry: "",
    concepts: [],
    matchedKeywords: [],
    hotBoards: [],
    relatedEtfs: [],
    summary: "暂无板块联动结果"
  };
}

function createDefaultLimitUpSignal(): LimitUpSignalProfile {
  return {
    recentLimitUpCount10: 0,
    isHoldingAboveOpen: false,
    anchorDate: "",
    anchorOpen: 0,
    anchorClose: 0,
    holdDays: 0,
    currentBiasPct: 0,
    tone: "neutral",
    summary: "暂无涨停守开信号"
  };
}

function createDefaultUsFocusItem(): UsFocusItem {
  return {
    key: "",
    name: "",
    symbol: "",
    category: "",
    lastTradeDate: "",
    close: 0,
    prevClose: 0,
    changePct: 0,
    high: 0,
    low: 0,
    volume: 0,
    tone: "neutral",
    summary: "暂无隔夜摘要",
    news: []
  };
}

function createDefaultUsMarketPulse(): UsMarketPulse {
  return {
    updatedAt: "",
    tradeDate: "",
    summary: "暂无隔夜美股晨报",
    items: []
  };
}

function createDefaultMarketBreadthPoint(): MarketBreadthPoint {
  return {
    timestamp: "",
    totalUp: 0,
    totalDown: 0,
    limitUp: 0,
    limitDown: 0,
    flatCount: 0,
    netAdvance: 0
  };
}

function createDefaultMarketBreadth(): MarketBreadthProfile {
  return {
    updatedAt: "",
    tradeDate: "",
    activityPct: 0,
    upCount: 0,
    downCount: 0,
    flatCount: 0,
    limitUpCount: 0,
    limitDownCount: 0,
    netAdvance: 0,
    advanceDeclineRatio: 0,
    breadthLow: 0,
    breadthHigh: 0,
    tone: "neutral",
    signalLabel: "鏆傛棤甯傚満瀹藉害鏍锋湰",
    summary: "鏆傛棤涓婃定/涓嬭穼瀹舵暟鏇茬嚎",
    trendPoints: []
  };
}

function createDefaultMarketRadar(): MarketRadar {
  return {
    updatedAt: "",
    hottestBoards: [],
    hottestEtfs: [],
    usMarketPulse: createDefaultUsMarketPulse(),
    marketBreadth: createDefaultMarketBreadth()
  };
}

function normalizeTone(value: unknown): IndicatorTone {
  return value === "positive" || value === "negative" || value === "alert" ? value : "neutral";
}

function normalizeMacd(value: unknown): MacdIndicator {
  if (!value || typeof value !== "object") {
    return createDefaultTechnicals().macd;
  }

  const candidate = value as Partial<MacdIndicator>;
  return {
    dif: typeof candidate.dif === "number" ? candidate.dif : 0,
    dea: typeof candidate.dea === "number" ? candidate.dea : 0,
    histogram: typeof candidate.histogram === "number" ? candidate.histogram : 0,
    signalLabel: typeof candidate.signalLabel === "string" ? candidate.signalLabel : "无数据",
    biasLabel: typeof candidate.biasLabel === "string" ? candidate.biasLabel : "等待样本",
    tone: normalizeTone(candidate.tone)
  };
}

function normalizeRsi(value: unknown): RsiIndicator {
  if (!value || typeof value !== "object") {
    return createDefaultTechnicals().rsi14;
  }

  const candidate = value as Partial<RsiIndicator>;
  return {
    period: typeof candidate.period === "number" ? candidate.period : 9,
    value: typeof candidate.value === "number" ? candidate.value : 50,
    signalLabel: typeof candidate.signalLabel === "string" ? candidate.signalLabel : "无数据",
    biasLabel: typeof candidate.biasLabel === "string" ? candidate.biasLabel : "等待样本",
    tone: normalizeTone(candidate.tone)
  };
}

function normalizeTechnicals(value: unknown): TechnicalIndicators {
  if (!value || typeof value !== "object") {
    return createDefaultTechnicals();
  }

  const candidate = value as Partial<TechnicalIndicators>;
  return {
    macd: normalizeMacd(candidate.macd),
    rsi14: normalizeRsi(candidate.rsi14)
  };
}

function normalizeScoreFactor(value: unknown): ScoreFactor {
  if (!value || typeof value !== "object") {
    return {
      key: "unknown",
      label: "未知",
      score: 0,
      maxScore: 0,
      tone: "neutral",
      summary: "无数据"
    };
  }

  const candidate = value as Partial<ScoreFactor>;
  return {
    key: typeof candidate.key === "string" ? candidate.key : "unknown",
    label: typeof candidate.label === "string" ? candidate.label : "未知",
    score: typeof candidate.score === "number" ? candidate.score : 0,
    maxScore: typeof candidate.maxScore === "number" ? candidate.maxScore : 0,
    tone: normalizeTone(candidate.tone),
    summary: typeof candidate.summary === "string" ? candidate.summary : "无数据"
  };
}

function normalizeSelectionScore(value: unknown): SelectionScore {
  if (!value || typeof value !== "object") {
    return createDefaultSelectionScore();
  }

  const candidate = value as Partial<SelectionScore>;
  return {
    total: typeof candidate.total === "number" ? candidate.total : 0,
    maxScore: typeof candidate.maxScore === "number" ? candidate.maxScore : 100,
    grade: typeof candidate.grade === "string" ? candidate.grade : "D",
    summary: typeof candidate.summary === "string" ? candidate.summary : "等待更多信号",
    factors: Array.isArray(candidate.factors) ? candidate.factors.map(normalizeScoreFactor) : []
  };
}

function normalizeCompanyInsight(value: unknown): CompanyInsight {
  if (!value || typeof value !== "object") {
    return createDefaultCompanyInsight();
  }

  const candidate = value as Partial<CompanyInsight>;
  const accounting = candidate.accountingBusiness;
  const official = candidate.officialBusiness;
  const news = candidate.newsSensitivity;
  const research = candidate.researchFocus;

  return {
    updatedAt: typeof candidate.updatedAt === "string" ? candidate.updatedAt : "",
    accountingBusiness: {
      reportDate: accounting && typeof accounting.reportDate === "string" ? accounting.reportDate : "",
      classification: accounting && typeof accounting.classification === "string" ? accounting.classification : "",
      summary: accounting && typeof accounting.summary === "string" ? accounting.summary : "暂无会计主营拆分数据",
      segments: accounting && Array.isArray(accounting.segments)
        ? accounting.segments.map((segment) => ({
            name: typeof segment?.name === "string" ? segment.name : "",
            revenueYi: typeof segment?.revenueYi === "number" ? segment.revenueYi : 0,
            revenueRatio: typeof segment?.revenueRatio === "number" ? segment.revenueRatio : 0,
            profitYi: typeof segment?.profitYi === "number" ? segment.profitYi : 0,
            profitRatio: typeof segment?.profitRatio === "number" ? segment.profitRatio : 0,
            grossMargin: typeof segment?.grossMargin === "number" ? segment.grossMargin : 0
          }))
        : []
    },
    officialBusiness: {
      companyName: official && typeof official.companyName === "string" ? official.companyName : "",
      industry: official && typeof official.industry === "string" ? official.industry : "",
      mainBusiness: official && typeof official.mainBusiness === "string" ? official.mainBusiness : "",
      businessScope: official && typeof official.businessScope === "string" ? official.businessScope : "",
      companyIntro: official && typeof official.companyIntro === "string" ? official.companyIntro : ""
    },
    newsSensitivity: {
      score: news && typeof news.score === "number" ? news.score : 0,
      level: news && typeof news.level === "string" ? news.level : "低",
      summary: news && typeof news.summary === "string" ? news.summary : "暂无新闻与政策敏感度样本",
      matchedKeywords: news && Array.isArray(news.matchedKeywords)
        ? news.matchedKeywords.filter((keyword): keyword is string => typeof keyword === "string")
        : [],
      items: news && Array.isArray(news.items)
        ? news.items.map((item) => ({
            title: typeof item?.title === "string" ? item.title : "",
            publishTime: typeof item?.publishTime === "string" ? item.publishTime : "",
            source: typeof item?.source === "string" ? item.source : "",
            url: typeof item?.url === "string" ? item.url : "",
            excerpt: typeof item?.excerpt === "string" ? item.excerpt : "",
            matchedKeywords: Array.isArray(item?.matchedKeywords)
              ? item.matchedKeywords.filter((keyword): keyword is string => typeof keyword === "string")
              : []
          }))
        : []
    },
    researchFocus: {
      monthlyReportCount: research && typeof research.monthlyReportCount === "number" ? research.monthlyReportCount : 0,
      summary: research && typeof research.summary === "string" ? research.summary : "暂无券商研报样本",
      focusKeywords: research && Array.isArray(research.focusKeywords)
        ? research.focusKeywords.filter((keyword): keyword is string => typeof keyword === "string")
        : [],
      items: research && Array.isArray(research.items)
        ? research.items.map((item) => ({
            date: typeof item?.date === "string" ? item.date : "",
            institution: typeof item?.institution === "string" ? item.institution : "",
            rating: typeof item?.rating === "string" ? item.rating : "",
            title: typeof item?.title === "string" ? item.title : "",
            industry: typeof item?.industry === "string" ? item.industry : "",
            reportUrl: typeof item?.reportUrl === "string" ? item.reportUrl : ""
          }))
        : []
    }
  };
}

function normalizeImportedStock(stock: WatchStock): WatchStock {
  const normalizedCandles = normalizeCandlePoints(
    (stock as WatchStock & { candles?: unknown }).candles,
    stock.sparkline
  );

  return {
    ...stock,
    candles: normalizedCandles,
    limitUpSignal: normalizeLimitUpSignal((stock as WatchStock & { limitUpSignal?: unknown }).limitUpSignal),
    bollinger: normalizeBollingerProfile(
      (stock as WatchStock & { bollinger?: unknown }).bollinger,
      normalizedCandles
    ),
    chipDistribution: normalizeChipDistribution(
      (stock as WatchStock & { chipDistribution?: unknown }).chipDistribution,
      normalizedCandles,
      stock.price
    ),
    metadata: normalizeStockMetadata((stock as WatchStock & { metadata?: unknown }).metadata),
    companyInsight: normalizeCompanyInsight((stock as WatchStock & { companyInsight?: unknown }).companyInsight),
    technicals: normalizeTechnicals((stock as WatchStock & { technicals?: unknown }).technicals),
    selectionScore: normalizeSelectionScore((stock as WatchStock & { selectionScore?: unknown }).selectionScore),
    themeLinkage: normalizeStockThemeLinkage((stock as WatchStock & { themeLinkage?: unknown }).themeLinkage)
  };
}

function normalizeBollingerPoint(value: unknown): BollingerPoint {
  if (!value || typeof value !== "object") {
    return {
      date: "",
      middle: 0,
      upper: 0,
      lower: 0
    };
  }

  const candidate = value as Partial<BollingerPoint>;
  return {
    date: typeof candidate.date === "string" ? candidate.date : "",
    middle: typeof candidate.middle === "number" ? candidate.middle : 0,
    upper: typeof candidate.upper === "number" ? candidate.upper : 0,
    lower: typeof candidate.lower === "number" ? candidate.lower : 0
  };
}

function deriveBollingerFromCandles(source: CandlePoint[]): BollingerProfile {
  const closes = source.map((item) => item.close);
  const period = 30;
  const stdMultiplier = 2;
  const points = source.map((item, index) => {
    const windowStart = Math.max(0, index - period + 1);
    const window = closes.slice(windowStart, index + 1);
    const mean = window.reduce((sum, value) => sum + value, 0) / window.length;
    const variance = window.reduce((sum, value) => sum + ((value - mean) ** 2), 0) / window.length;
    const deviation = Math.sqrt(variance);
    return {
      date: item.date,
      middle: Number(mean.toFixed(2)),
      upper: Number((mean + deviation * stdMultiplier).toFixed(2)),
      lower: Number((mean - deviation * stdMultiplier).toFixed(2))
    };
  });

  return {
    period,
    stdMultiplier,
    points
  };
}

function normalizeBollingerProfile(value: unknown, fallbackCandles: CandlePoint[]): BollingerProfile {
  if (!value || typeof value !== "object") {
    return deriveBollingerFromCandles(fallbackCandles);
  }

  const candidate = value as Partial<BollingerProfile>;
  const points = Array.isArray(candidate.points) ? candidate.points.map((item) => normalizeBollingerPoint(item)) : [];
  if (points.length === 0) {
    return deriveBollingerFromCandles(fallbackCandles);
  }

  return {
    period: typeof candidate.period === "number" ? candidate.period : 30,
    stdMultiplier: typeof candidate.stdMultiplier === "number" ? candidate.stdMultiplier : 2,
    points
  };
}

function normalizeChipBand(value: unknown): ChipDistributionBand {
  if (!value || typeof value !== "object") {
    return { price: 0, ratio: 0 };
  }

  const candidate = value as Partial<ChipDistributionBand>;
  return {
    price: typeof candidate.price === "number" ? candidate.price : 0,
    ratio: typeof candidate.ratio === "number" ? candidate.ratio : 0
  };
}

function normalizeChipControlEvidence(value: unknown): ChipControlEvidence {
  if (!value || typeof value !== "object") {
    return {
      key: "",
      label: "",
      value: "",
      tone: "neutral",
      summary: ""
    };
  }

  const candidate = value as Partial<ChipControlEvidence>;
  return {
    key: typeof candidate.key === "string" ? candidate.key : "",
    label: typeof candidate.label === "string" ? candidate.label : "",
    value: typeof candidate.value === "string" ? candidate.value : "",
    tone: candidate.tone === "positive" || candidate.tone === "negative" || candidate.tone === "alert" ? candidate.tone : "neutral",
    summary: typeof candidate.summary === "string" ? candidate.summary : ""
  };
}

function deriveChipInsights(
  bands: ChipDistributionBand[],
  currentPrice: number,
  bucketSize: number,
  mainCost: number,
  dominantRatio: number,
  concentration90Low: number,
  concentration90High: number,
  winnerRatio: number
) {
  const dominantIndex = Math.max(0, bands.findIndex((item) => item.price === mainCost));
  const threshold = Math.max(dominantRatio * 0.35, 0.02);
  let start = dominantIndex;
  let end = dominantIndex;

  while (start > 0 && (bands[start - 1]?.ratio ?? 0) >= threshold) {
    start -= 1;
  }
  while (end < bands.length - 1 && (bands[end + 1]?.ratio ?? 0) >= threshold) {
    end += 1;
  }

  const zoneLow = Number((bands[start]?.price ?? mainCost ?? currentPrice).toFixed(2));
  const zoneHigh = Number((bands[end]?.price ?? mainCost ?? currentPrice).toFixed(2));
  const zoneWidthPct = mainCost > 0 ? Number((((zoneHigh - zoneLow) / mainCost) * 100).toFixed(2)) : 0;
  const span = Math.max(concentration90High - concentration90Low, bucketSize);
  const zoneMid = (zoneLow + zoneHigh) / 2;
  const zonePosition = span > 0 ? (zoneMid - concentration90Low) / span : 0.5;

  let shapeLabel = "筹码密集";
  let stageLabel = "震荡换手";
  let riskLabel = "筹码集中但方向未完全展开";
  let tone: IndicatorTone = "neutral";

  if (currentPrice >= zoneHigh * 1.08 && winnerRatio >= 0.68) {
    shapeLabel = "向上发散";
    stageLabel = "拉升展开";
    riskLabel = "已经脱离主力成本区，趋势在走，但不宜追高";
    tone = "positive";
  } else if (currentPrice <= zoneLow * 0.92 && winnerRatio <= 0.35) {
    shapeLabel = "向下发散";
    stageLabel = "下行出清";
    riskLabel = "价格落在主力成本区下方，筹码承压明显";
    tone = "negative";
  } else if (zoneWidthPct <= 12 && zonePosition <= 0.35) {
    shapeLabel = "低位密集";
    stageLabel = "吸筹蓄势";
    riskLabel = "低位换手较充分，等待放量确认";
    tone = "positive";
  } else if (zoneWidthPct <= 12 && zonePosition >= 0.65) {
    shapeLabel = "高位密集";
    stageLabel = "高位博弈";
    riskLabel = "高位筹码堆积，优先防派发风险";
    tone = "alert";
  } else if (zoneWidthPct > 18) {
    shapeLabel = "宽幅发散";
    stageLabel = "筹码分散";
    riskLabel = "持仓成本差异较大，控盘轮廓不够清晰";
  }

  const controlEvidence: ChipControlEvidence[] = [
    {
      key: "cost_zone",
      label: "成本区位置",
      value: currentPrice > zoneHigh ? `高于成本区 ${(((currentPrice / zoneHigh) - 1) * 100).toFixed(1)}%` : currentPrice < zoneLow ? `低于成本区 ${((1 - (currentPrice / zoneLow)) * 100).toFixed(1)}%` : "处于成本区内",
      tone: currentPrice > zoneHigh ? "alert" : currentPrice < zoneLow ? "negative" : "positive",
      summary: "用于判断当前价格是否仍围绕主力成本区运行。"
    },
    {
      key: "winner_lock",
      label: "90比3",
      value: `获利 ${(winnerRatio * 100).toFixed(1)}%`,
      tone: winnerRatio >= 0.9 ? "positive" : winnerRatio >= 0.75 ? "neutral" : "negative",
      summary: winnerRatio >= 0.9 ? "已接近或满足 90 比 3。" : "仅作为 fallback 估算，等待真实快照覆盖。"
    }
  ];

  return {
    zoneLow,
    zoneHigh,
    zoneWidthPct,
    shapeLabel,
    stageLabel,
    riskLabel,
    tone,
    controlEvidence
  };
}

function deriveChipDistributionFromCandles(source: CandlePoint[], currentPrice: number): ChipDistributionProfile {
  if (source.length === 0) {
    return createDefaultChipDistribution(currentPrice);
  }

  const bucketSize = currentPrice >= 100 ? 0.2 : 0.1;
  const buckets = new Map<number, number>();
  source.forEach((item) => {
    const bucket = Number((Math.round(item.close / bucketSize) * bucketSize).toFixed(2));
    buckets.set(bucket, (buckets.get(bucket) ?? 0) + 1);
  });

  const sampleSize = source.length;
  const bands = [...buckets.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([price, count]) => ({
      price,
      ratio: Number((count / sampleSize).toFixed(6))
    }));

  const mainBand = [...bands].sort((a, b) => b.ratio - a.ratio)[0] ?? { price: currentPrice, ratio: 0 };
  const averageCost = bands.reduce((sum, item) => sum + item.price * item.ratio, 0);
  const winnerRatio = bands.filter((item) => item.price <= currentPrice).reduce((sum, item) => sum + item.ratio, 0);
  const prices = bands.map((item) => item.price);
  const low70Index = Math.max(0, Math.floor((prices.length - 1) * 0.15));
  const high70Index = Math.max(low70Index, Math.floor((prices.length - 1) * 0.85));
  const low90Index = Math.max(0, Math.floor((prices.length - 1) * 0.05));
  const high90Index = Math.max(low90Index, Math.floor((prices.length - 1) * 0.95));
  const mainCost = mainBand.price || currentPrice;
  const concentration90Low = Number((prices[low90Index] ?? currentPrice).toFixed(2));
  const concentration90High = Number((prices[high90Index] ?? currentPrice).toFixed(2));
  const insight = deriveChipInsights(
    bands,
    currentPrice,
    bucketSize,
    mainCost,
    mainBand.ratio,
    concentration90Low,
    concentration90High,
    winnerRatio
  );

  return {
    algorithm: "turnover_decay_v1",
    bucketSize,
    sampleSize,
    tradeDate: source[source.length - 1]?.date ?? "",
    mainCost: Number(mainCost.toFixed(2)),
    mainCostZoneLow: insight.zoneLow,
    mainCostZoneHigh: insight.zoneHigh,
    mainCostZoneWidthPct: insight.zoneWidthPct,
    averageCost: Number(averageCost.toFixed(2)),
    winnerRatio: Number(winnerRatio.toFixed(6)),
    dominantRatio: Number(mainBand.ratio.toFixed(6)),
    concentration70Low: Number((prices[low70Index] ?? currentPrice).toFixed(2)),
    concentration70High: Number((prices[high70Index] ?? currentPrice).toFixed(2)),
    concentration90Low,
    concentration90High,
    currentPriceBiasPct: mainCost ? Number((((currentPrice / mainCost) - 1) * 100).toFixed(2)) : 0,
    shapeLabel: insight.shapeLabel,
    stageLabel: insight.stageLabel,
    riskLabel: insight.riskLabel,
    tone: insight.tone,
    summary: `${insight.shapeLabel}，主力成本区 ${insight.zoneLow.toFixed(2)}-${insight.zoneHigh.toFixed(2)}，获利盘 ${(winnerRatio * 100).toFixed(1)}%。${insight.riskLabel}`,
    controlEvidence: insight.controlEvidence,
    bands
  };
}

function normalizeChipDistribution(
  value: unknown,
  fallbackCandles: CandlePoint[],
  currentPrice: number
): ChipDistributionProfile {
  if (!value || typeof value !== "object") {
    return deriveChipDistributionFromCandles(fallbackCandles, currentPrice);
  }

  const candidate = value as Partial<ChipDistributionProfile>;
  const bands = Array.isArray(candidate.bands) ? candidate.bands.map((item) => normalizeChipBand(item)) : [];
  if (bands.length === 0) {
    return deriveChipDistributionFromCandles(fallbackCandles, currentPrice);
  }
  const mainCost = typeof candidate.mainCost === "number" ? candidate.mainCost : currentPrice;
  const bucketSize = typeof candidate.bucketSize === "number" ? candidate.bucketSize : 0.1;
  const dominantRatio = typeof candidate.dominantRatio === "number" ? candidate.dominantRatio : 0;
  const concentration90Low = typeof candidate.concentration90Low === "number" ? candidate.concentration90Low : currentPrice;
  const concentration90High = typeof candidate.concentration90High === "number" ? candidate.concentration90High : currentPrice;
  const winnerRatio = typeof candidate.winnerRatio === "number" ? candidate.winnerRatio : 0;
  const derivedInsight = deriveChipInsights(
    bands,
    currentPrice,
    bucketSize,
    mainCost,
    dominantRatio,
    concentration90Low,
    concentration90High,
    winnerRatio
  );
  const controlEvidence = Array.isArray(candidate.controlEvidence)
    ? candidate.controlEvidence.map((item) => normalizeChipControlEvidence(item)).filter((item) => item.label)
    : [];

  return {
    algorithm: typeof candidate.algorithm === "string" ? candidate.algorithm : "turnover_decay_v1",
    bucketSize,
    sampleSize: typeof candidate.sampleSize === "number" ? candidate.sampleSize : fallbackCandles.length,
    tradeDate: typeof candidate.tradeDate === "string" ? candidate.tradeDate : "",
    mainCost,
    mainCostZoneLow: typeof candidate.mainCostZoneLow === "number" ? candidate.mainCostZoneLow : derivedInsight.zoneLow,
    mainCostZoneHigh: typeof candidate.mainCostZoneHigh === "number" ? candidate.mainCostZoneHigh : derivedInsight.zoneHigh,
    mainCostZoneWidthPct: typeof candidate.mainCostZoneWidthPct === "number" ? candidate.mainCostZoneWidthPct : derivedInsight.zoneWidthPct,
    averageCost: typeof candidate.averageCost === "number" ? candidate.averageCost : currentPrice,
    winnerRatio,
    dominantRatio,
    concentration70Low: typeof candidate.concentration70Low === "number" ? candidate.concentration70Low : currentPrice,
    concentration70High: typeof candidate.concentration70High === "number" ? candidate.concentration70High : currentPrice,
    concentration90Low,
    concentration90High,
    currentPriceBiasPct: typeof candidate.currentPriceBiasPct === "number" ? candidate.currentPriceBiasPct : 0,
    shapeLabel: typeof candidate.shapeLabel === "string" ? candidate.shapeLabel : derivedInsight.shapeLabel,
    stageLabel: typeof candidate.stageLabel === "string" ? candidate.stageLabel : derivedInsight.stageLabel,
    riskLabel: typeof candidate.riskLabel === "string" ? candidate.riskLabel : derivedInsight.riskLabel,
    tone: candidate.tone === "positive" || candidate.tone === "negative" || candidate.tone === "alert" ? candidate.tone : derivedInsight.tone,
    summary: typeof candidate.summary === "string" ? candidate.summary : `${derivedInsight.shapeLabel}，等待真实快照刷新`,
    controlEvidence: controlEvidence.length > 0 ? controlEvidence : derivedInsight.controlEvidence,
    bands
  };
}

function normalizeCandlePoint(value: unknown, index: number, fallbackClose: number): CandlePoint {
  if (!value || typeof value !== "object") {
    return {
      date: "",
      open: fallbackClose,
      high: fallbackClose,
      low: fallbackClose,
      close: fallbackClose,
      isLimitUpClose: false
    };
  }

  const candidate = value as Partial<CandlePoint>;
  const close = typeof candidate.close === "number" ? candidate.close : fallbackClose;
  const open = typeof candidate.open === "number" ? candidate.open : close;
  const high = typeof candidate.high === "number" ? candidate.high : Math.max(open, close);
  const low = typeof candidate.low === "number" ? candidate.low : Math.min(open, close);

  return {
    date: typeof candidate.date === "string" ? candidate.date : `D${index + 1}`,
    open,
    high,
    low,
    close,
    isLimitUpClose: candidate.isLimitUpClose === true
  };
}

function deriveCandlesFromCloses(source: number[]): CandlePoint[] {
  return source.slice(-12).map((close, index, list) => {
    const prevClose = index > 0 ? list[index - 1] : close;
    const open = Number(((prevClose + close) / 2).toFixed(2));
    const high = Number((Math.max(open, close) * 1.01).toFixed(2));
    const low = Number((Math.min(open, close) * 0.99).toFixed(2));
    return {
      date: `D${index + 1}`,
      open,
      high,
      low,
      close: Number(close.toFixed(2)),
      isLimitUpClose: false
    };
  });
}

function normalizeCandlePoints(value: unknown, fallbackSource: number[]): CandlePoint[] {
  if (!Array.isArray(value) || value.length === 0) {
    return deriveCandlesFromCloses(fallbackSource);
  }

  return value.map((item, index) => {
    const fallbackClose = fallbackSource[index] ?? fallbackSource[fallbackSource.length - 1] ?? 0;
    return normalizeCandlePoint(item, index, fallbackClose);
  });
}

function normalizeThemeHotspot(value: unknown): ThemeHotspot {
  if (!value || typeof value !== "object") {
    return createDefaultThemeHotspot();
  }

  const candidate = value as Partial<ThemeHotspot>;
  return {
    boardType: candidate.boardType === "industry" || candidate.boardType === "etf" ? candidate.boardType : "concept",
    name: typeof candidate.name === "string" ? candidate.name : "",
    code: typeof candidate.code === "string" ? candidate.code : "",
    rank: typeof candidate.rank === "number" ? candidate.rank : 0,
    changePct: typeof candidate.changePct === "number" ? candidate.changePct : 0,
    riseCount: typeof candidate.riseCount === "number" ? candidate.riseCount : 0,
    fallCount: typeof candidate.fallCount === "number" ? candidate.fallCount : 0,
    leaderName: typeof candidate.leaderName === "string" ? candidate.leaderName : "",
    leaderCode: typeof candidate.leaderCode === "string" ? candidate.leaderCode : "",
    leaderChangePct: typeof candidate.leaderChangePct === "number" ? candidate.leaderChangePct : 0,
    matchReason: typeof candidate.matchReason === "string" ? candidate.matchReason : ""
  };
}

function normalizeStockThemeLinkage(value: unknown): StockThemeLinkage {
  if (!value || typeof value !== "object") {
    return createDefaultStockThemeLinkage();
  }

  const candidate = value as Partial<StockThemeLinkage>;
  return {
    updatedAt: typeof candidate.updatedAt === "string" ? candidate.updatedAt : "",
    industry: typeof candidate.industry === "string" ? candidate.industry : "",
    concepts: Array.isArray(candidate.concepts) ? candidate.concepts.filter((item): item is string => typeof item === "string") : [],
    matchedKeywords: Array.isArray(candidate.matchedKeywords)
      ? candidate.matchedKeywords.filter((item): item is string => typeof item === "string")
      : [],
    hotBoards: Array.isArray(candidate.hotBoards) ? candidate.hotBoards.map((item) => normalizeThemeHotspot(item)) : [],
    relatedEtfs: Array.isArray(candidate.relatedEtfs) ? candidate.relatedEtfs.map((item) => normalizeThemeHotspot(item)) : [],
    summary: typeof candidate.summary === "string" ? candidate.summary : "暂无板块联动结果"
  };
}

function normalizeLimitUpSignal(value: unknown): LimitUpSignalProfile {
  if (!value || typeof value !== "object") {
    return createDefaultLimitUpSignal();
  }

  const candidate = value as Partial<LimitUpSignalProfile>;
  return {
    recentLimitUpCount10: typeof candidate.recentLimitUpCount10 === "number" ? candidate.recentLimitUpCount10 : 0,
    isHoldingAboveOpen: candidate.isHoldingAboveOpen === true,
    anchorDate: typeof candidate.anchorDate === "string" ? candidate.anchorDate : "",
    anchorOpen: typeof candidate.anchorOpen === "number" ? candidate.anchorOpen : 0,
    anchorClose: typeof candidate.anchorClose === "number" ? candidate.anchorClose : 0,
    holdDays: typeof candidate.holdDays === "number" ? candidate.holdDays : 0,
    currentBiasPct: typeof candidate.currentBiasPct === "number" ? candidate.currentBiasPct : 0,
    tone: normalizeTone(candidate.tone),
    summary: typeof candidate.summary === "string" ? candidate.summary : "暂无涨停守开信号"
  };
}

function normalizeUsFocusItem(value: unknown): UsFocusItem {
  if (!value || typeof value !== "object") {
    return createDefaultUsFocusItem();
  }

  const candidate = value as Partial<UsFocusItem>;
  return {
    key: typeof candidate.key === "string" ? candidate.key : "",
    name: typeof candidate.name === "string" ? candidate.name : "",
    symbol: typeof candidate.symbol === "string" ? candidate.symbol : "",
    category: typeof candidate.category === "string" ? candidate.category : "",
    lastTradeDate: typeof candidate.lastTradeDate === "string" ? candidate.lastTradeDate : "",
    close: typeof candidate.close === "number" ? candidate.close : 0,
    prevClose: typeof candidate.prevClose === "number" ? candidate.prevClose : 0,
    changePct: typeof candidate.changePct === "number" ? candidate.changePct : 0,
    high: typeof candidate.high === "number" ? candidate.high : 0,
    low: typeof candidate.low === "number" ? candidate.low : 0,
    volume: typeof candidate.volume === "number" ? candidate.volume : 0,
    tone: candidate.tone === "positive" || candidate.tone === "negative" || candidate.tone === "alert" ? candidate.tone : "neutral",
    summary: typeof candidate.summary === "string" ? candidate.summary : "暂无隔夜摘要",
    news: Array.isArray(candidate.news) ? candidate.news.filter((item) => !!item && typeof item === "object") as UsFocusItem["news"] : []
  };
}

function normalizeMarketBreadthPoint(value: unknown): MarketBreadthPoint {
  if (!value || typeof value !== "object") {
    return createDefaultMarketBreadthPoint();
  }

  const candidate = value as Partial<MarketBreadthPoint>;
  return {
    timestamp: typeof candidate.timestamp === "string" ? candidate.timestamp : "",
    totalUp: typeof candidate.totalUp === "number" ? candidate.totalUp : 0,
    totalDown: typeof candidate.totalDown === "number" ? candidate.totalDown : 0,
    limitUp: typeof candidate.limitUp === "number" ? candidate.limitUp : 0,
    limitDown: typeof candidate.limitDown === "number" ? candidate.limitDown : 0,
    flatCount: typeof candidate.flatCount === "number" ? candidate.flatCount : 0,
    netAdvance: typeof candidate.netAdvance === "number" ? candidate.netAdvance : 0
  };
}

function normalizeMarketBreadth(value: unknown): MarketBreadthProfile {
  if (!value || typeof value !== "object") {
    return createDefaultMarketBreadth();
  }

  const candidate = value as Partial<MarketBreadthProfile>;
  return {
    updatedAt: typeof candidate.updatedAt === "string" ? candidate.updatedAt : "",
    tradeDate: typeof candidate.tradeDate === "string" ? candidate.tradeDate : "",
    activityPct: typeof candidate.activityPct === "number" ? candidate.activityPct : 0,
    upCount: typeof candidate.upCount === "number" ? candidate.upCount : 0,
    downCount: typeof candidate.downCount === "number" ? candidate.downCount : 0,
    flatCount: typeof candidate.flatCount === "number" ? candidate.flatCount : 0,
    limitUpCount: typeof candidate.limitUpCount === "number" ? candidate.limitUpCount : 0,
    limitDownCount: typeof candidate.limitDownCount === "number" ? candidate.limitDownCount : 0,
    netAdvance: typeof candidate.netAdvance === "number" ? candidate.netAdvance : 0,
    advanceDeclineRatio: typeof candidate.advanceDeclineRatio === "number" ? candidate.advanceDeclineRatio : 0,
    breadthLow: typeof candidate.breadthLow === "number" ? candidate.breadthLow : 0,
    breadthHigh: typeof candidate.breadthHigh === "number" ? candidate.breadthHigh : 0,
    tone: normalizeTone(candidate.tone),
    signalLabel: typeof candidate.signalLabel === "string" ? candidate.signalLabel : "鏆傛棤甯傚満瀹藉害鏍锋湰",
    summary: typeof candidate.summary === "string" ? candidate.summary : "鏆傛棤涓婃定/涓嬭穼瀹舵暟鏇茬嚎",
    trendPoints: Array.isArray(candidate.trendPoints) ? candidate.trendPoints.map((item) => normalizeMarketBreadthPoint(item)) : []
  };
}

function normalizeMarketRadar(value: unknown): MarketRadar {
  if (!value || typeof value !== "object") {
    return createDefaultMarketRadar();
  }

  const candidate = value as Partial<MarketRadar>;
  const usPulse = candidate.usMarketPulse && typeof candidate.usMarketPulse === "object" ? candidate.usMarketPulse : undefined;
  return {
    updatedAt: typeof candidate.updatedAt === "string" ? candidate.updatedAt : "",
    hottestBoards: Array.isArray(candidate.hottestBoards) ? candidate.hottestBoards.map((item) => normalizeThemeHotspot(item)) : [],
    hottestEtfs: Array.isArray(candidate.hottestEtfs) ? candidate.hottestEtfs.map((item) => normalizeThemeHotspot(item)) : [],
    marketBreadth: normalizeMarketBreadth(candidate.marketBreadth),
    usMarketPulse: {
      updatedAt: typeof usPulse?.updatedAt === "string" ? usPulse.updatedAt : "",
      tradeDate: typeof usPulse?.tradeDate === "string" ? usPulse.tradeDate : "",
      summary: typeof usPulse?.summary === "string" ? usPulse.summary : "暂无隔夜美股晨报",
      items: Array.isArray(usPulse?.items) ? usPulse.items.map((item) => normalizeUsFocusItem(item)) : []
    }
  };
}

export function normalizeDashboardSnapshot(value: DashboardSnapshot): DashboardSnapshot {
  return {
    ...value,
    marketRadar: normalizeMarketRadar(value.marketRadar),
    stocks: (value.stocks ?? []).map((stock) => normalizeImportedStock(stock as WatchStock))
  };
}

const snapshot = applyCycleAnalysis(normalizeDashboardSnapshot(akshareSnapshot as DashboardSnapshot));

function createSparkline(seed: number) {
  return Array.from({ length: 8 }, (_, index) => {
    const base = 6 + (seed % 9) * 0.35;
    const slope = index * (0.22 + (seed % 5) * 0.04);
    const wobble = ((seed + index * 3) % 4) * 0.08;
    return Number((base + slope + wobble).toFixed(2));
  });
}

function createCandles(seed: number, price: number) {
  const closes = createCloseSeries(seed, price).slice(-12);
  return closes.map((close, index, list) => {
    const prevClose = index > 0 ? list[index - 1] : close - ((seed % 5) - 2) * 0.14;
    const open = Number((prevClose + ((seed + index) % 3 - 1) * 0.18).toFixed(2));
    const closePrice = Number(close.toFixed(2));
    const high = Number((Math.max(open, closePrice) + 0.18 + ((seed + index) % 4) * 0.07).toFixed(2));
    const low = Number((Math.min(open, closePrice) - 0.18 - ((seed + index) % 3) * 0.05).toFixed(2));
    return {
      date: `D${index + 1}`,
      open,
      high,
      low: Number(Math.max(0.01, low).toFixed(2)),
      close: closePrice,
      isLimitUpClose: false
    };
  });
}

function createBollinger(seed: number, price: number) {
  return deriveBollingerFromCandles(createCandles(seed, price));
}

function createCloseSeries(seed: number, price: number) {
  return Array.from({ length: 180 }, (_, index) => {
    const wave = Math.sin((index + seed) / 11) * (0.7 + (seed % 6) * 0.08);
    const drift = ((index / 180) * ((seed % 9) - 4)) / 3;
    const wobble = (((seed + index * 7) % 13) - 6) * 0.05;
    return Number((price + wave + drift + wobble).toFixed(2));
  });
}

function createAmplitudeSeries(code: string, seed: number, price: number) {
  const boardCap = codeLooksLikeGrowthBoard(code) ? 40 : 20;
  return Array.from({ length: 180 }, (_, index) => {
    const swing = ((((seed + index * 5) % 17) + 1) / 17) * (boardCap * 0.42);
    const pulse = ((index + seed) % 9 === 0 ? boardCap * 0.12 : 0);
    return Number(Math.min(boardCap * 0.95, swing + pulse).toFixed(2));
  });
}

function createDefaultMacd(): MacdIndicator {
  return createDefaultTechnicals().macd;
}

function createDefaultRsi(): RsiIndicator {
  return createDefaultTechnicals().rsi14;
}

function clamp(value: number, low: number, high: number) {
  return Math.max(low, Math.min(high, value));
}

function codeLooksLikeGrowthBoard(code: string) {
  return code.startsWith("300") || code.startsWith("301") || code.startsWith("688");
}

function resolveAmplitudeTemplate(code: string, marketCapYi: number) {
  const boardType = codeLooksLikeGrowthBoard(code) ? "创业成长板" : "沪深主板";

  if (boardType === "创业成长板") {
    if (marketCapYi >= 1000) {
      return { boardType, marketCapBucket: "千亿以上", amplitudeCap: 40, edges: [0, 0.8, 1.5, 3, 5, 8, 40] };
    }
    if (marketCapYi >= 500) {
      return { boardType, marketCapBucket: "500-1000亿", amplitudeCap: 40, edges: [0, 1, 2, 4, 6, 10, 40] };
    }
    if (marketCapYi >= 100) {
      return { boardType, marketCapBucket: "100-500亿", amplitudeCap: 40, edges: [0, 1, 5, 10, 15, 25, 40] };
    }
    return { boardType, marketCapBucket: "100亿以下", amplitudeCap: 40, edges: [0, 2, 5, 10, 18, 28, 40] };
  }

  if (marketCapYi >= 1000) {
    return { boardType, marketCapBucket: "千亿以上", amplitudeCap: 20, edges: [0, 0.5, 1, 2, 3, 5, 20] };
  }
  if (marketCapYi >= 500) {
    return { boardType, marketCapBucket: "500-1000亿", amplitudeCap: 20, edges: [0, 0.8, 1.5, 3, 5, 8, 20] };
  }
  if (marketCapYi >= 100) {
    return { boardType, marketCapBucket: "100-500亿", amplitudeCap: 20, edges: [0, 1, 3, 5, 10, 15, 20] };
  }
  return { boardType, marketCapBucket: "100亿以下", amplitudeCap: 20, edges: [0, 1.5, 3, 5, 8, 12, 20] };
}

function buildPriceDistribution(closeSeries: number[], currentPrice: number): PriceDistributionProfile {
  const source = closeSeries.length > 0 ? closeSeries : [currentPrice || 0];
  const yearLow = Number(Math.min(...source).toFixed(2));
  const yearHigh = Number(Math.max(...source).toFixed(2));
  const sampleSize = source.length;

  if (yearHigh <= yearLow) {
    const stableBand = 2;
    const bands: PriceDistributionBand[] = Array.from({ length: 6 }, (_, index) => ({
      index,
      lower: yearLow,
      upper: yearHigh,
      closeCount: index === stableBand ? sampleSize : 0,
      ratio: Number((index === stableBand ? 1 : 0).toFixed(4)),
      rangeLabel: `${yearLow.toFixed(2)}-${yearHigh.toFixed(2)}`
    }));

    return {
      yearHigh,
      yearLow,
      sampleSize,
      currentBand: stableBand,
      dominantBand: stableBand,
      currentPositionPct: 0.5,
      bands
    };
  }

  const bandWidth = (yearHigh - yearLow) / 6;
  const counts = Array.from({ length: 6 }, () => 0);
  const resolveBand = (price: number) => Math.max(0, Math.min(5, Math.floor((price - yearLow) / bandWidth)));

  source.forEach((closePrice) => {
    counts[resolveBand(closePrice)] += 1;
  });

  const boundedPrice = clamp(currentPrice, yearLow, yearHigh);
  const currentBand = resolveBand(boundedPrice);
  const dominantBand = counts.reduce((bestIndex, count, index) => (
    count > counts[bestIndex] ? index : bestIndex
  ), 0);

  const bands: PriceDistributionBand[] = Array.from({ length: 6 }, (_, index) => {
    const lower = yearLow + index * bandWidth;
    const upper = index === 5 ? yearHigh : yearLow + (index + 1) * bandWidth;
    return {
      index,
      lower: Number(lower.toFixed(2)),
      upper: Number(upper.toFixed(2)),
      closeCount: counts[index],
      ratio: Number((counts[index] / sampleSize).toFixed(4)),
      rangeLabel: `${lower.toFixed(2)}-${upper.toFixed(2)}`
    };
  });

  return {
    yearHigh,
    yearLow,
    sampleSize,
    currentBand,
    dominantBand,
    currentPositionPct: Number((((boundedPrice - yearLow) / (yearHigh - yearLow)) || 0).toFixed(4)),
    bands
  };
}

function buildAmplitudeDistribution(
  code: string,
  amplitudeSeries: number[],
  currentAmplitude: number,
  marketCapYi: number
): AmplitudeDistributionProfile {
  const template = resolveAmplitudeTemplate(code, marketCapYi);
  const source = amplitudeSeries.length > 0 ? amplitudeSeries : [currentAmplitude || 0];
  const counts = Array.from({ length: template.edges.length - 1 }, () => 0);
  const sampleSize = source.length;

  const resolveBand = (value: number) => {
    const boundedValue = clamp(value, 0, template.amplitudeCap);
    for (let index = 0; index < template.edges.length - 1; index += 1) {
      const lower = template.edges[index];
      const upper = template.edges[index + 1];
      if (index === template.edges.length - 2) {
        if (boundedValue >= lower && boundedValue <= upper) {
          return index;
        }
      } else if (boundedValue >= lower && boundedValue < upper) {
        return index;
      }
    }
    return template.edges.length - 2;
  };

  source.forEach((value) => {
    counts[resolveBand(value)] += 1;
  });

  const currentBand = resolveBand(currentAmplitude);
  const dominantBand = counts.reduce((bestIndex, count, index) => (
    count > counts[bestIndex] ? index : bestIndex
  ), 0);

  const bands: PriceDistributionBand[] = counts.map((count, index) => ({
    index,
    lower: template.edges[index],
    upper: template.edges[index + 1],
    closeCount: count,
    ratio: Number((count / sampleSize).toFixed(4)),
    rangeLabel: `${template.edges[index].toFixed(1)}%-${template.edges[index + 1].toFixed(1)}%`
  }));

  return {
    boardType: template.boardType,
    marketCapYi: Number(marketCapYi.toFixed(2)),
    marketCapBucket: template.marketCapBucket,
    amplitudeCap: template.amplitudeCap,
    currentAmplitude: Number(currentAmplitude.toFixed(2)),
    sampleSize,
    currentBand,
    dominantBand,
    bands
  };
}

function buildMacdIndicator(closeSeries: number[]): MacdIndicator {
  if (closeSeries.length < 2) {
    return createDefaultMacd();
  }

  const smoothing = (period: number) => 2 / (period + 1);
  let ema10 = closeSeries[0];
  let ema200 = closeSeries[0];
  let dea = 0;
  let prevDif = 0;
  let prevDea = 0;

  closeSeries.forEach((price, index) => {
    if (index === 0) {
      return;
    }

    prevDif = ema10 - ema200;
    prevDea = dea;
    ema10 = price * smoothing(10) + ema10 * (1 - smoothing(10));
    ema200 = price * smoothing(200) + ema200 * (1 - smoothing(200));
    const dif = ema10 - ema200;
    dea = dif * smoothing(7) + dea * (1 - smoothing(7));
  });

  const dif = ema10 - ema200;
  const histogram = (dif - dea) * 2;

  if (prevDif < prevDea && dif >= dea) {
    return {
      dif: Number(dif.toFixed(3)),
      dea: Number(dea.toFixed(3)),
      histogram: Number(histogram.toFixed(3)),
      signalLabel: "MACD 金叉",
      biasLabel: "短中期转强，关注跟随",
      tone: "positive"
    };
  }

  if (prevDif > prevDea && dif <= dea) {
    return {
      dif: Number(dif.toFixed(3)),
      dea: Number(dea.toFixed(3)),
      histogram: Number(histogram.toFixed(3)),
      signalLabel: "MACD 死叉",
      biasLabel: "趋势转弱，谨慎追高",
      tone: "negative"
    };
  }

  if (dif >= dea && dif >= 0) {
    return {
      dif: Number(dif.toFixed(3)),
      dea: Number(dea.toFixed(3)),
      histogram: Number(histogram.toFixed(3)),
      signalLabel: "长周期多头",
      biasLabel: "站上长周期均线",
      tone: "positive"
    };
  }

  if (dif >= dea) {
    return {
      dif: Number(dif.toFixed(3)),
      dea: Number(dea.toFixed(3)),
      histogram: Number(histogram.toFixed(3)),
      signalLabel: "长周期修复",
      biasLabel: "空头背景下修复观察",
      tone: "neutral"
    };
  }

  if (dif <= 0) {
    return {
      dif: Number(dif.toFixed(3)),
      dea: Number(dea.toFixed(3)),
      histogram: Number(histogram.toFixed(3)),
      signalLabel: "长周期空头",
      biasLabel: "远离 200 日均线",
      tone: "negative"
    };
  }

  return {
    dif: Number(dif.toFixed(3)),
    dea: Number(dea.toFixed(3)),
    histogram: Number(histogram.toFixed(3)),
    signalLabel: "长周期回落",
    biasLabel: "多头回踩，防止走弱",
    tone: "alert"
  };
}

function buildRsiIndicator(closeSeries: number[], period = 9): RsiIndicator {
  if (closeSeries.length <= period) {
    return createDefaultRsi();
  }

  const deltas = closeSeries.slice(1).map((price, index) => price - closeSeries[index]);
  let averageGain = 0;
  let averageLoss = 0;

  deltas.slice(0, period).forEach((delta) => {
    averageGain += delta > 0 ? delta : 0;
    averageLoss += delta < 0 ? Math.abs(delta) : 0;
  });

  averageGain /= period;
  averageLoss /= period;

  deltas.slice(period).forEach((delta) => {
    const gain = delta > 0 ? delta : 0;
    const loss = delta < 0 ? Math.abs(delta) : 0;
    averageGain = ((averageGain * (period - 1)) + gain) / period;
    averageLoss = ((averageLoss * (period - 1)) + loss) / period;
  });

  const rs = averageLoss === 0 ? 100 : averageGain / averageLoss;
  const value = 100 - (100 / (1 + rs));
  const previousDeltas = deltas.slice(0, -1);
  let prevAverageGain = 0;
  let prevAverageLoss = 0;

  if (previousDeltas.length >= period) {
    previousDeltas.slice(0, period).forEach((delta) => {
      prevAverageGain += delta > 0 ? delta : 0;
      prevAverageLoss += delta < 0 ? Math.abs(delta) : 0;
    });

    prevAverageGain /= period;
    prevAverageLoss /= period;

    previousDeltas.slice(period).forEach((delta) => {
      const gain = delta > 0 ? delta : 0;
      const loss = delta < 0 ? Math.abs(delta) : 0;
      prevAverageGain = ((prevAverageGain * (period - 1)) + gain) / period;
      prevAverageLoss = ((prevAverageLoss * (period - 1)) + loss) / period;
    });
  }

  const prevRs = prevAverageLoss === 0 ? 100 : prevAverageGain / prevAverageLoss;
  const prevValue = previousDeltas.length >= period ? 100 - (100 / (1 + prevRs)) : value;

  if (value >= 80) {
    return { period, value: Number(value.toFixed(2)), signalLabel: "RSI 高风险", biasLabel: "建议卖出或减仓", tone: "alert" };
  }
  if (prevValue < 50 && value >= 50) {
    return { period, value: Number(value.toFixed(2)), signalLabel: "RSI 上穿50", biasLabel: "重点关注买入", tone: "positive" };
  }
  if (value >= 50) {
    return { period, value: Number(value.toFixed(2)), signalLabel: "RSI 强势区", biasLabel: "多头主导，持有观察", tone: "positive" };
  }
  if (prevValue >= 50 && value < 50) {
    return { period, value: Number(value.toFixed(2)), signalLabel: "RSI 跌破50", biasLabel: "强势失守，转弱观察", tone: "negative" };
  }
  if (value >= 30) {
    return { period, value: Number(value.toFixed(2)), signalLabel: "RSI 观察区", biasLabel: "等待重新站上50", tone: "neutral" };
  }

  return { period, value: Number(value.toFixed(2)), signalLabel: "RSI 弱势区", biasLabel: "低于30，先等修复", tone: "negative" };
}

function buildTechnicalIndicators(closeSeries: number[]): TechnicalIndicators {
  if (closeSeries.length === 0) {
    return createDefaultTechnicals();
  }

  return {
    macd: buildMacdIndicator(closeSeries),
    rsi14: buildRsiIndicator(closeSeries)
  };
}

function gradeFromTotalScore(totalScore: number) {
  if (totalScore >= 85) {
    return "A";
  }
  if (totalScore >= 75) {
    return "B+";
  }
  if (totalScore >= 65) {
    return "B";
  }
  if (totalScore >= 55) {
    return "C";
  }
  return "D";
}

function buildSelectionScore(
  priceDistribution: PriceDistributionProfile,
  amplitudeDistribution: AmplitudeDistributionProfile,
  volumeRatio: number,
  technicals: TechnicalIndicators
): SelectionScore {
  const factors: ScoreFactor[] = [];

  let positionScore = 2;
  let positionSummary = "年内高位，价格优势有限";
  let positionTone: IndicatorTone = "negative";
  if (priceDistribution.currentPositionPct <= 0.2) {
    positionScore = 20;
    positionSummary = "年内低位，价格周期占优";
    positionTone = "positive";
  } else if (priceDistribution.currentPositionPct <= 0.4) {
    positionScore = 17;
    positionSummary = "年内中低位，具备位置优势";
    positionTone = "positive";
  } else if (priceDistribution.currentPositionPct <= 0.6) {
    positionScore = 12;
    positionSummary = "年内中位，性价比中性";
    positionTone = "neutral";
  } else if (priceDistribution.currentPositionPct <= 0.8) {
    positionScore = 7;
    positionSummary = "年内偏高位，注意追涨风险";
    positionTone = "alert";
  }
  factors.push({
    key: "price_cycle",
    label: "价格周期",
    score: positionScore,
    maxScore: 20,
    tone: positionTone,
    summary: positionSummary
  });

  const bandGap = amplitudeDistribution.currentBand - amplitudeDistribution.dominantBand;
  let amplitudeScore = 6;
  let amplitudeSummary = "振幅过热，警惕波动放大";
  let amplitudeTone: IndicatorTone = "alert";
  if (bandGap === 1) {
    amplitudeScore = 18;
    amplitudeSummary = "振幅略强于常态，活跃度理想";
    amplitudeTone = "positive";
  } else if (bandGap === 0) {
    amplitudeScore = 16;
    amplitudeSummary = "振幅处于常态活跃区";
    amplitudeTone = "positive";
  } else if (bandGap < 0) {
    amplitudeScore = 10;
    amplitudeSummary = "振幅偏弱，等待波动放大";
    amplitudeTone = "neutral";
  } else if (bandGap >= 2) {
    amplitudeScore = 4;
    amplitudeSummary = "振幅明显过热，先控风险";
    amplitudeTone = "negative";
  }
  factors.push({
    key: "amplitude_strength",
    label: "振幅强度",
    score: amplitudeScore,
    maxScore: 20,
    tone: amplitudeTone,
    summary: amplitudeSummary
  });

  let volumeScore = 2;
  let volumeSummary = "量能不足，资金关注度弱";
  let volumeTone: IndicatorTone = "negative";
  if (volumeRatio >= 2.0) {
    volumeScore = 20;
    volumeSummary = "量能显著放大，资金参与强";
    volumeTone = "positive";
  } else if (volumeRatio >= 1.5) {
    volumeScore = 17;
    volumeSummary = "量能活跃，具备跟随价值";
    volumeTone = "positive";
  } else if (volumeRatio >= 1.2) {
    volumeScore = 14;
    volumeSummary = "量能温和放大，关注延续";
    volumeTone = "positive";
  } else if (volumeRatio >= 1.0) {
    volumeScore = 10;
    volumeSummary = "量能中性，等待放量确认";
    volumeTone = "neutral";
  } else if (volumeRatio >= 0.8) {
    volumeScore = 6;
    volumeSummary = "量能偏淡，尚未形成共振";
    volumeTone = "neutral";
  }
  factors.push({
    key: "volume_strength",
    label: "量能",
    score: volumeScore,
    maxScore: 20,
    tone: volumeTone,
    summary: volumeSummary
  });

  const rsi = technicals.rsi14;
  let rsiScore = 3;
  let rsiSummary = "RSI 弱势区，先等修复";
  let rsiTone: IndicatorTone = "negative";
  if (rsi.signalLabel === "RSI 上穿50") {
    rsiScore = 20;
    rsiSummary = "RSI 从30-50上穿50，重点关注买入";
    rsiTone = "positive";
  } else if (rsi.signalLabel === "RSI 强势区") {
    rsiScore = 17;
    rsiSummary = "RSI 位于50-80强势区";
    rsiTone = "positive";
  } else if (rsi.signalLabel === "RSI 观察区") {
    rsiScore = 10;
    rsiSummary = "RSI 位于30-50观察区";
    rsiTone = "neutral";
  } else if (rsi.signalLabel === "RSI 跌破50") {
    rsiScore = 5;
    rsiSummary = "RSI 跌破50，强势失守";
    rsiTone = "negative";
  } else if (rsi.signalLabel === "RSI 高风险") {
    rsiScore = 1;
    rsiSummary = "RSI 超过80，高风险区";
    rsiTone = "alert";
  }
  factors.push({
    key: "rsi_signal",
    label: "RSI",
    score: rsiScore,
    maxScore: 20,
    tone: rsiTone,
    summary: rsiSummary
  });

  const macd = technicals.macd;
  let macdScore = 4;
  let macdSummary = "长周期空头，趋势拖累";
  let macdTone: IndicatorTone = "negative";
  if (macd.signalLabel === "MACD 金叉") {
    macdScore = 20;
    macdSummary = "MACD 金叉，趋势扭转信号强";
    macdTone = "positive";
  } else if (macd.signalLabel === "长周期多头") {
    macdScore = 17;
    macdSummary = "长周期多头，趋势保持完整";
    macdTone = "positive";
  } else if (macd.signalLabel === "长周期修复") {
    macdScore = 12;
    macdSummary = "长周期修复，等待进一步确认";
    macdTone = "neutral";
  } else if (macd.signalLabel === "长周期回落") {
    macdScore = 8;
    macdSummary = "长周期回落，关注是否再度走弱";
    macdTone = "alert";
  } else if (macd.signalLabel === "MACD 死叉") {
    macdScore = 3;
    macdSummary = "MACD 死叉，短中期偏弱";
    macdTone = "negative";
  }
  factors.push({
    key: "macd_trend",
    label: "MACD趋势",
    score: macdScore,
    maxScore: 20,
    tone: macdTone,
    summary: macdSummary
  });

  const total = factors.reduce((sum, factor) => sum + factor.score, 0);
  const leading = [...factors]
    .sort((a, b) => b.score - a.score)
    .filter((factor, index) => index < 2)
    .map((factor) => factor.summary);

  return {
    total,
    maxScore: 100,
    grade: gradeFromTotalScore(total),
    summary: leading.join("；"),
    factors
  };
}

function buildFallbackStock(code: string, index: number): WatchStock {
  const numericSeed = Number(code.slice(-3)) || index * 17 + 11;
  const changePct = Number((((numericSeed % 17) - 6) * 0.43).toFixed(2));
  const price = Number((12 + (numericSeed % 220) * 1.17).toFixed(2));
  const momentum = 48 + (numericSeed % 44);
  const volumeRatio = Number((0.78 + (numericSeed % 9) * 0.11).toFixed(2));
  const signalLevel = changePct >= 2 ? "strong" : changePct >= 0 ? "watch" : "calm";
  const closeSeries = createCloseSeries(numericSeed, price);
  const amplitudeSeries = createAmplitudeSeries(code, numericSeed, price);
  const marketCapYi = Number((80 + (numericSeed % 1500)).toFixed(2));
  const currentAmplitude = amplitudeSeries[amplitudeSeries.length - 1] ?? 0;
  const technicals = buildTechnicalIndicators(closeSeries);
  const priceDistribution = buildPriceDistribution(closeSeries, price);
  const amplitudeDistribution = buildAmplitudeDistribution(code, amplitudeSeries, currentAmplitude, marketCapYi);
  const selectionScore = buildSelectionScore(priceDistribution, amplitudeDistribution, volumeRatio, technicals);

  return {
    symbol: code,
    name: code,
    market: "A股",
    sector: "自选池",
    price,
    changePct,
    momentum,
    volumeRatio,
    note: notePool[index % notePool.length],
    thesis: thesisPool[index % thesisPool.length],
    sparkline: createSparkline(numericSeed),
    candles: createCandles(numericSeed, price),
    limitUpSignal: createDefaultLimitUpSignal(),
    bollinger: createBollinger(numericSeed, price),
    chipDistribution: deriveChipDistributionFromCandles(createCandles(numericSeed, price), price),
    signals: [
      { label: "涨跌", value: `${changePct >= 0 ? "+" : ""}${changePct.toFixed(2)}%`, level: signalLevel },
      { label: "动能", value: String(momentum), level: momentum >= 75 ? "strong" : "watch" },
      { label: "量比", value: `${volumeRatio.toFixed(2)}倍`, level: volumeRatio >= 1.2 ? "strong" : "calm" }
    ],
    metadata: {
      officialWebsite: "",
      websiteSource: ""
    },
    companyInsight: createDefaultCompanyInsight(),
    technicals,
    selectionScore,
    priceDistribution,
    amplitudeDistribution,
    themeLinkage: createDefaultStockThemeLinkage()
  };
}

export function getFallbackSnapshot(): DashboardSnapshot {
  const stocks = watchlistSeeds.map((item, index) => buildFallbackStock(item.code, index));
  const averageChange = stocks.reduce((sum, stock) => sum + stock.changePct, 0) / stocks.length;

  return applyCycleAnalysis({
    syncTime: "2026-03-12 16:30",
    watchlistCount: stocks.length,
    strongSignals: stocks.filter((stock) => stock.signals.some((signal) => signal.level === "strong")).length,
    avgChange: Number(averageChange.toFixed(2)),
    mood: averageChange >= 0 ? "偏强" : "分化",
    marketRadar: createDefaultMarketRadar(),
    stocks
  });
}

export function getInitialSnapshot(): DashboardSnapshot {
  return snapshot.stocks.length > 0 ? snapshot : getFallbackSnapshot();
}
