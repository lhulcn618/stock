import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta
import math
from pathlib import Path
import re
import time

import akshare as ak
import baostock as bs
import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
WATCHLIST_TS_PATH = ROOT / "src" / "data" / "watchlist.ts"
WATCHLIST_PATH = ROOT / "watchlist_codes.txt"
OUTPUT_PATH = ROOT / "src" / "data" / "akshare-snapshot.json"
CACHE_ROOT = ROOT / ".cache" / "akshare"
HIST_CACHE_DIR = CACHE_ROOT / "hist"
STOCK_CACHE_DIR = CACHE_ROOT / "stocks"
CAP_CACHE_DIR = CACHE_ROOT / "cap"
META_CACHE_DIR = CACHE_ROOT / "meta"
NAME_CACHE_PATH = CACHE_ROOT / "name-map.json"
SPOT_CACHE_PATH = CACHE_ROOT / "spot-snapshot.json"
BOARD_CACHE_DIR = CACHE_ROOT / "boards"
BOARD_LIST_CACHE_DIR = BOARD_CACHE_DIR / "lists"
BOARD_MEMBER_CACHE_DIR = BOARD_CACHE_DIR / "members"
ETF_DAILY_CACHE_PATH = CACHE_ROOT / "etf-daily.json"
US_CACHE_DIR = CACHE_ROOT / "us"
MARKET_BREADTH_CACHE_PATH = CACHE_ROOT / "market-breadth.json"

C_CODE = "代码"
C_NAME = "名称"
C_LATEST = "最新价"
C_CHANGE = "涨跌幅"
C_VOLUME = "成交量"
C_CLOSE = "收盘"
C_HIGH = "最高"
C_LOW = "最低"
C_INDUSTRY = "所处行业"
C_WEBSITE = "官方网站"

SH_MAIN = "主板A股"
STAR_BOARD = "科创板"
SZ_A_LIST = "A股列表"
SH_CODE_COL = "证券代码"
SH_NAME_COL = "证券简称"
SZ_CODE_COL = "A股代码"
SZ_NAME_COL = "A股简称"
BJ_CODE_COL = "证券代码"
BJ_NAME_COL = "证券简称"

NAME_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
SPOT_CACHE_TTL_SECONDS = 10 * 60
HIST_CACHE_TTL_SECONDS = 24 * 60 * 60
CAP_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
META_CACHE_TTL_SECONDS = 30 * 24 * 60 * 60
STOCK_CACHE_VERSION = 16
BOARD_LIST_CACHE_TTL_SECONDS = 6 * 60 * 60
BOARD_MEMBER_CACHE_TTL_SECONDS = 12 * 60 * 60
ETF_DAILY_CACHE_TTL_SECONDS = 12 * 60 * 60
US_DAILY_CACHE_TTL_SECONDS = 12 * 60 * 60
MARKET_BREADTH_CACHE_TTL_SECONDS = 5 * 60
WATCHLIST_ENTRY_PATTERN = re.compile(
    r'\{\s*code:\s*["\'](?P<code>\d{6})["\']\s*,\s*name:\s*["\'](?P<name>[^"\']*)["\']\s*\}'
)

BAOSTOCK_DAILY_FIELDS = "date,open,high,low,close,preclose,volume,amount,pctChg"
BAOSTOCK_CHIP_FIELDS = "date,close,preclose,volume,amount,turn"
_BAOSTOCK_LOGGED_IN = False

HOT_INDUSTRY_SCAN_LIMIT = 18
HOT_CONCEPT_SCAN_LIMIT = 36
MAX_STOCK_HOT_BOARDS = 6
MAX_STOCK_ETFS = 3
MAX_GLOBAL_BOARDS = 8
MAX_GLOBAL_ETFS = 8

LEGU_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

US_FOCUS_DEFINITIONS = [
    {"key": "AAPL", "name": "Apple", "symbol": "AAPL", "category": "七姐妹", "newsSymbol": "AAPL"},
    {"key": "MSFT", "name": "Microsoft", "symbol": "MSFT", "category": "七姐妹", "newsSymbol": "MSFT"},
    {"key": "NVDA", "name": "NVIDIA", "symbol": "NVDA", "category": "七姐妹", "newsSymbol": "NVDA"},
    {"key": "AMZN", "name": "Amazon", "symbol": "AMZN", "category": "七姐妹", "newsSymbol": "AMZN"},
    {"key": "GOOGL", "name": "Alphabet", "symbol": "GOOGL", "category": "七姐妹", "newsSymbol": "GOOGL"},
    {"key": "META", "name": "Meta", "symbol": "META", "category": "七姐妹", "newsSymbol": "META"},
    {"key": "TSLA", "name": "Tesla / 马斯克", "symbol": "TSLA", "category": "七姐妹", "newsSymbol": "TSLA"},
    {"key": "OPENAI", "name": "OpenAI", "symbol": "", "category": "AI 公司", "newsSymbol": "OpenAI"},
]

NOTE_POOL = [
    "收盘前观察盘口是否确认当前形态。",
    "继续跟踪，等待更强的放量日。",
    "趋势结构尚可，但仍需进一步确认。",
    "若出现干净的延续日，信号可信度会更高。",
    "在价量重新共振前，先作为跟踪标的。",
]

THESIS_POOL = [
    "观察该股周边板块强度是否继续扩散。",
    "结合日线结构与换手强度判断资金共识。",
    "重点看当前波段能否站稳近期支撑。",
    "保留在自选池中，等待动能确认，而不是提前预判。",
    "若收盘更强、板块扩散更清晰，可上调关注级别。",
]


THEME_KEYWORDS = [
    "人工智能",
    "AI",
    "算力",
    "数据要素",
    "机器人",
    "低空经济",
    "脑机接口",
    "半导体",
    "国产替代",
    "军工",
    "卫星互联网",
    "商业航天",
    "光模块",
    "激光",
    "铜缆高速连接",
    "新能源",
    "储能",
    "充电桩",
    "特高压",
    "电网",
    "风电",
    "光伏",
    "核电",
    "海工装备",
    "油气",
    "化工",
    "稀土",
    "新材料",
    "固态电池",
    "锂电",
    "创新药",
    "医疗器械",
    "脑科学",
    "消费电子",
    "信创",
    "东数西算",
    "国企改革",
    "并购重组",
]

POLICY_KEYWORDS = [
    "政策",
    "规划",
    "方案",
    "试点",
    "工作报告",
    "补贴",
    "招标",
    "指南",
    "审批",
    "医保",
    "集采",
    "监管",
    "工信部",
    "国家发改委",
    "国务院",
    "证监会",
    "卫健委",
    "药监局",
    "商务部",
    "财政部",
    "两会",
    "国常会",
    "十四五",
]

BOARD_NOISE_KEYWORDS = {
    "政策",
    "规划",
    "方案",
    "试点",
    "工作报告",
    "补贴",
    "指南",
    "审批",
    "医保",
    "监管",
    "工信部",
    "国家发改委",
    "国务院",
    "证监会",
    "卫健委",
    "药监局",
    "商务部",
    "财政部",
    "两会",
    "国常会",
    "十四五",
}


@dataclass
class Signal:
    label: str
    value: str
    level: str


@dataclass
class StockMetadata:
    officialWebsite: str
    websiteSource: str


@dataclass
class AccountingBusinessSegment:
    name: str
    revenueYi: float
    revenueRatio: float
    profitYi: float
    profitRatio: float
    grossMargin: float


@dataclass
class AccountingBusinessInsight:
    reportDate: str
    classification: str
    summary: str
    segments: list[AccountingBusinessSegment]


@dataclass
class OfficialBusinessInsight:
    companyName: str
    industry: str
    mainBusiness: str
    businessScope: str
    companyIntro: str


@dataclass
class NewsInsightItem:
    title: str
    publishTime: str
    source: str
    url: str
    excerpt: str
    matchedKeywords: list[str]


@dataclass
class NewsSensitivityInsight:
    score: int
    level: str
    summary: str
    matchedKeywords: list[str]
    items: list[NewsInsightItem]


@dataclass
class ResearchInsightItem:
    date: str
    institution: str
    rating: str
    title: str
    industry: str
    reportUrl: str


@dataclass
class ResearchFocusInsight:
    monthlyReportCount: int
    summary: str
    focusKeywords: list[str]
    items: list[ResearchInsightItem]


@dataclass
class CompanyInsight:
    updatedAt: str
    accountingBusiness: AccountingBusinessInsight
    officialBusiness: OfficialBusinessInsight
    newsSensitivity: NewsSensitivityInsight
    researchFocus: ResearchFocusInsight


@dataclass
class MacdIndicator:
    dif: float
    dea: float
    histogram: float
    signalLabel: str
    biasLabel: str
    tone: str


@dataclass
class RsiIndicator:
    period: int
    value: float
    signalLabel: str
    biasLabel: str
    tone: str


@dataclass
class TechnicalIndicators:
    macd: MacdIndicator
    rsi14: RsiIndicator


@dataclass
class BollingerPoint:
    date: str
    middle: float
    upper: float
    lower: float


@dataclass
class BollingerProfile:
    period: int
    stdMultiplier: float
    points: list[BollingerPoint]


@dataclass
class ChipDistributionBand:
    price: float
    ratio: float


@dataclass
class ChipControlEvidence:
    key: str
    label: str
    value: str
    tone: str
    summary: str


@dataclass
class ChipDistributionProfile:
    algorithm: str
    bucketSize: float
    sampleSize: int
    tradeDate: str
    mainCost: float
    mainCostZoneLow: float
    mainCostZoneHigh: float
    mainCostZoneWidthPct: float
    averageCost: float
    winnerRatio: float
    dominantRatio: float
    concentration70Low: float
    concentration70High: float
    concentration90Low: float
    concentration90High: float
    currentPriceBiasPct: float
    shapeLabel: str
    stageLabel: str
    riskLabel: str
    tone: str
    summary: str
    controlEvidence: list[ChipControlEvidence]
    bands: list[ChipDistributionBand]


@dataclass
class ScoreFactor:
    key: str
    label: str
    score: int
    maxScore: int
    tone: str
    summary: str


@dataclass
class SelectionScore:
    total: int
    maxScore: int
    grade: str
    summary: str
    factors: list[ScoreFactor]


@dataclass
class PriceDistributionBand:
    index: int
    lower: float
    upper: float
    closeCount: int
    ratio: float
    rangeLabel: str


@dataclass
class PriceDistributionProfile:
    yearHigh: float
    yearLow: float
    sampleSize: int
    currentBand: int
    dominantBand: int
    currentPositionPct: float
    bands: list[PriceDistributionBand]


@dataclass
class AmplitudeDistributionProfile:
    boardType: str
    marketCapYi: float
    marketCapBucket: str
    amplitudeCap: float
    currentAmplitude: float
    sampleSize: int
    currentBand: int
    dominantBand: int
    bands: list[PriceDistributionBand]


@dataclass
class ThemeHotspot:
    boardType: str
    name: str
    code: str
    rank: int
    changePct: float
    riseCount: int
    fallCount: int
    leaderName: str
    leaderCode: str
    leaderChangePct: float
    matchReason: str


@dataclass
class StockThemeLinkage:
    updatedAt: str
    industry: str
    concepts: list[str]
    matchedKeywords: list[str]
    hotBoards: list[ThemeHotspot]
    relatedEtfs: list[ThemeHotspot]
    summary: str


@dataclass
class UsFocusItem:
    key: str
    name: str
    symbol: str
    category: str
    lastTradeDate: str
    close: float
    prevClose: float
    changePct: float
    high: float
    low: float
    volume: float
    tone: str
    summary: str
    news: list[NewsInsightItem]


@dataclass
class UsMarketPulse:
    updatedAt: str
    tradeDate: str
    summary: str
    items: list[UsFocusItem]


@dataclass
class MarketBreadthPoint:
    timestamp: str
    totalUp: int
    totalDown: int
    limitUp: int
    limitDown: int
    flatCount: int
    netAdvance: int


@dataclass
class MarketBreadthProfile:
    updatedAt: str
    tradeDate: str
    activityPct: float
    upCount: int
    downCount: int
    flatCount: int
    limitUpCount: int
    limitDownCount: int
    netAdvance: int
    advanceDeclineRatio: float
    breadthLow: int
    breadthHigh: int
    tone: str
    signalLabel: str
    summary: str
    trendPoints: list[MarketBreadthPoint]


@dataclass
class MarketRadar:
    updatedAt: str
    hottestBoards: list[ThemeHotspot]
    hottestEtfs: list[ThemeHotspot]
    usMarketPulse: UsMarketPulse
    marketBreadth: MarketBreadthProfile


@dataclass
class CandlePoint:
    date: str
    open: float
    high: float
    low: float
    close: float
    isLimitUpClose: bool


@dataclass
class LimitUpSignalProfile:
    recentLimitUpCount10: int
    isHoldingAboveOpen: bool
    anchorDate: str
    anchorOpen: float
    anchorClose: float
    holdDays: int
    currentBiasPct: float
    tone: str
    summary: str


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
    sparkline: list[float]
    candles: list[CandlePoint]
    limitUpSignal: LimitUpSignalProfile
    bollinger: BollingerProfile
    chipDistribution: ChipDistributionProfile
    signals: list[Signal]
    metadata: StockMetadata
    companyInsight: CompanyInsight
    technicals: TechnicalIndicators
    selectionScore: SelectionScore
    priceDistribution: PriceDistributionProfile
    amplitudeDistribution: AmplitudeDistributionProfile
    themeLinkage: StockThemeLinkage


def band_from_dict(data: dict) -> PriceDistributionBand:
    return PriceDistributionBand(
        index=int(data.get("index", 0)),
        lower=float(data.get("lower", 0.0)),
        upper=float(data.get("upper", 0.0)),
        closeCount=int(data.get("closeCount", 0)),
        ratio=float(data.get("ratio", 0.0)),
        rangeLabel=str(data.get("rangeLabel", "0.00-0.00")),
    )


def distribution_from_dict(data: dict) -> PriceDistributionProfile:
    raw_bands = data.get("bands", []) if isinstance(data, dict) else []
    bands = [band_from_dict(item) for item in raw_bands if isinstance(item, dict)]
    return PriceDistributionProfile(
        yearHigh=float(data.get("yearHigh", 0.0)),
        yearLow=float(data.get("yearLow", 0.0)),
        sampleSize=int(data.get("sampleSize", 0)),
        currentBand=int(data.get("currentBand", 0)),
        dominantBand=int(data.get("dominantBand", 0)),
        currentPositionPct=float(data.get("currentPositionPct", 0.0)),
        bands=bands,
    )


def amplitude_distribution_from_dict(data: dict) -> AmplitudeDistributionProfile:
    raw_bands = data.get("bands", []) if isinstance(data, dict) else []
    bands = [band_from_dict(item) for item in raw_bands if isinstance(item, dict)]
    return AmplitudeDistributionProfile(
        boardType=str(data.get("boardType", "")),
        marketCapYi=float(data.get("marketCapYi", 0.0)),
        marketCapBucket=str(data.get("marketCapBucket", "")),
        amplitudeCap=float(data.get("amplitudeCap", 0.0)),
        currentAmplitude=float(data.get("currentAmplitude", 0.0)),
        sampleSize=int(data.get("sampleSize", 0)),
        currentBand=int(data.get("currentBand", 0)),
        dominantBand=int(data.get("dominantBand", 0)),
        bands=bands,
    )


def chip_band_from_dict(data: dict) -> ChipDistributionBand:
    return ChipDistributionBand(
        price=float(data.get("price", 0.0)),
        ratio=float(data.get("ratio", 0.0)),
    )


def chip_control_evidence_from_dict(data: dict) -> ChipControlEvidence:
    if not isinstance(data, dict):
        return ChipControlEvidence("", "", "", "neutral", "")

    return ChipControlEvidence(
        key=str(data.get("key", "")),
        label=str(data.get("label", "")),
        value=str(data.get("value", "")),
        tone=str(data.get("tone", "neutral")),
        summary=str(data.get("summary", "")),
    )


def chip_distribution_from_dict(data: dict) -> ChipDistributionProfile:
    if not isinstance(data, dict):
        return default_chip_distribution()

    raw_bands = data.get("bands", [])
    bands = [chip_band_from_dict(item) for item in raw_bands if isinstance(item, dict)]
    raw_evidence = data.get("controlEvidence", [])
    control_evidence = [chip_control_evidence_from_dict(item) for item in raw_evidence if isinstance(item, dict)]
    return ChipDistributionProfile(
        algorithm=str(data.get("algorithm", "turnover_decay_v1")),
        bucketSize=float(data.get("bucketSize", 0.1)),
        sampleSize=int(data.get("sampleSize", 0)),
        tradeDate=str(data.get("tradeDate", "")),
        mainCost=float(data.get("mainCost", 0.0)),
        mainCostZoneLow=float(data.get("mainCostZoneLow", data.get("mainCost", 0.0))),
        mainCostZoneHigh=float(data.get("mainCostZoneHigh", data.get("mainCost", 0.0))),
        mainCostZoneWidthPct=float(data.get("mainCostZoneWidthPct", 0.0)),
        averageCost=float(data.get("averageCost", 0.0)),
        winnerRatio=float(data.get("winnerRatio", 0.0)),
        dominantRatio=float(data.get("dominantRatio", 0.0)),
        concentration70Low=float(data.get("concentration70Low", 0.0)),
        concentration70High=float(data.get("concentration70High", 0.0)),
        concentration90Low=float(data.get("concentration90Low", 0.0)),
        concentration90High=float(data.get("concentration90High", 0.0)),
        currentPriceBiasPct=float(data.get("currentPriceBiasPct", 0.0)),
        shapeLabel=str(data.get("shapeLabel", "筹码待观察")),
        stageLabel=str(data.get("stageLabel", "等待样本")),
        riskLabel=str(data.get("riskLabel", "等待刷新")),
        tone=str(data.get("tone", "neutral")),
        summary=str(data.get("summary", "暂无筹码分布样本")),
        controlEvidence=control_evidence,
        bands=bands,
    )


def theme_hotspot_from_dict(data: dict) -> ThemeHotspot:
    if not isinstance(data, dict):
        return ThemeHotspot("concept", "", "", 0, 0.0, 0, 0, "", "", 0.0, "")

    return ThemeHotspot(
        boardType=str(data.get("boardType", "concept")),
        name=str(data.get("name", "")),
        code=str(data.get("code", "")),
        rank=int(data.get("rank", 0)),
        changePct=float(data.get("changePct", 0.0)),
        riseCount=int(data.get("riseCount", 0)),
        fallCount=int(data.get("fallCount", 0)),
        leaderName=str(data.get("leaderName", "")),
        leaderCode=str(data.get("leaderCode", "")),
        leaderChangePct=float(data.get("leaderChangePct", 0.0)),
        matchReason=str(data.get("matchReason", "")),
    )


def market_breadth_point_from_dict(data: dict) -> MarketBreadthPoint:
    if not isinstance(data, dict):
        return MarketBreadthPoint("", 0, 0, 0, 0, 0, 0)

    return MarketBreadthPoint(
        timestamp=str(data.get("timestamp", "")),
        totalUp=int(data.get("totalUp", 0)),
        totalDown=int(data.get("totalDown", 0)),
        limitUp=int(data.get("limitUp", 0)),
        limitDown=int(data.get("limitDown", 0)),
        flatCount=int(data.get("flatCount", 0)),
        netAdvance=int(data.get("netAdvance", 0)),
    )


def market_breadth_from_dict(data: dict) -> MarketBreadthProfile:
    if not isinstance(data, dict):
        return default_market_breadth()

    trend_points = [
        market_breadth_point_from_dict(item)
        for item in data.get("trendPoints", [])
        if isinstance(item, dict)
    ]
    return MarketBreadthProfile(
        updatedAt=str(data.get("updatedAt", "")),
        tradeDate=str(data.get("tradeDate", "")),
        activityPct=float(data.get("activityPct", 0.0)),
        upCount=int(data.get("upCount", 0)),
        downCount=int(data.get("downCount", 0)),
        flatCount=int(data.get("flatCount", 0)),
        limitUpCount=int(data.get("limitUpCount", 0)),
        limitDownCount=int(data.get("limitDownCount", 0)),
        netAdvance=int(data.get("netAdvance", 0)),
        advanceDeclineRatio=float(data.get("advanceDeclineRatio", 0.0)),
        breadthLow=int(data.get("breadthLow", 0)),
        breadthHigh=int(data.get("breadthHigh", 0)),
        tone=str(data.get("tone", "neutral")),
        signalLabel=str(data.get("signalLabel", "鏆傛棤甯傚満瀹藉害鏍锋湰")),
        summary=str(data.get("summary", "鏆傛棤涓婃定/涓嬭穼瀹舵暟鏇茬嚎")),
        trendPoints=trend_points,
    )


def stock_theme_linkage_from_dict(data: dict) -> StockThemeLinkage:
    if not isinstance(data, dict):
        return default_stock_theme_linkage()

    raw_hot_boards = data.get("hotBoards", [])
    raw_related_etfs = data.get("relatedEtfs", [])
    hot_boards = [theme_hotspot_from_dict(item) for item in raw_hot_boards if isinstance(item, dict)]
    related_etfs = [theme_hotspot_from_dict(item) for item in raw_related_etfs if isinstance(item, dict)]
    concepts = [str(item) for item in data.get("concepts", []) if isinstance(item, str)]
    matched_keywords = [str(item) for item in data.get("matchedKeywords", []) if isinstance(item, str)]
    return StockThemeLinkage(
        updatedAt=str(data.get("updatedAt", "")),
        industry=str(data.get("industry", "")),
        concepts=concepts,
        matchedKeywords=matched_keywords,
        hotBoards=hot_boards,
        relatedEtfs=related_etfs,
        summary=str(data.get("summary", "暂无板块联动结果")),
    )


def limit_up_signal_from_dict(data: dict) -> LimitUpSignalProfile:
    if not isinstance(data, dict):
        return default_limit_up_signal()

    return LimitUpSignalProfile(
        recentLimitUpCount10=int(data.get("recentLimitUpCount10", 0)),
        isHoldingAboveOpen=bool(data.get("isHoldingAboveOpen", False)),
        anchorDate=str(data.get("anchorDate", "")),
        anchorOpen=float(data.get("anchorOpen", 0.0)),
        anchorClose=float(data.get("anchorClose", 0.0)),
        holdDays=int(data.get("holdDays", 0)),
        currentBiasPct=float(data.get("currentBiasPct", 0.0)),
        tone=str(data.get("tone", "neutral")),
        summary=str(data.get("summary", "暂无涨停守开信号")),
    )


def metadata_from_dict(data: dict) -> StockMetadata:
    if not isinstance(data, dict):
        return StockMetadata(officialWebsite="", websiteSource="")

    return StockMetadata(
        officialWebsite=str(data.get("officialWebsite", "")),
        websiteSource=str(data.get("websiteSource", "")),
    )


def accounting_segment_from_dict(data: dict) -> AccountingBusinessSegment:
    if not isinstance(data, dict):
        return AccountingBusinessSegment("", 0.0, 0.0, 0.0, 0.0, 0.0)

    return AccountingBusinessSegment(
        name=str(data.get("name", "")),
        revenueYi=float(data.get("revenueYi", 0.0)),
        revenueRatio=float(data.get("revenueRatio", 0.0)),
        profitYi=float(data.get("profitYi", 0.0)),
        profitRatio=float(data.get("profitRatio", 0.0)),
        grossMargin=float(data.get("grossMargin", 0.0)),
    )


def accounting_business_from_dict(data: dict) -> AccountingBusinessInsight:
    if not isinstance(data, dict):
        return default_company_insight().accountingBusiness

    raw_segments = data.get("segments", [])
    segments = [accounting_segment_from_dict(item) for item in raw_segments if isinstance(item, dict)]
    return AccountingBusinessInsight(
        reportDate=str(data.get("reportDate", "")),
        classification=str(data.get("classification", "")),
        summary=str(data.get("summary", "暂无会计主营拆分数据")),
        segments=segments,
    )


def official_business_from_dict(data: dict) -> OfficialBusinessInsight:
    if not isinstance(data, dict):
        return default_company_insight().officialBusiness

    return OfficialBusinessInsight(
        companyName=str(data.get("companyName", "")),
        industry=str(data.get("industry", "")),
        mainBusiness=str(data.get("mainBusiness", "")),
        businessScope=str(data.get("businessScope", "")),
        companyIntro=str(data.get("companyIntro", "")),
    )


def news_item_from_dict(data: dict) -> NewsInsightItem:
    if not isinstance(data, dict):
        return NewsInsightItem("", "", "", "", "", [])

    raw_keywords = data.get("matchedKeywords", [])
    matched_keywords = [str(item) for item in raw_keywords if isinstance(item, str)]
    return NewsInsightItem(
        title=str(data.get("title", "")),
        publishTime=str(data.get("publishTime", "")),
        source=str(data.get("source", "")),
        url=str(data.get("url", "")),
        excerpt=str(data.get("excerpt", "")),
        matchedKeywords=matched_keywords,
    )


def news_sensitivity_from_dict(data: dict) -> NewsSensitivityInsight:
    if not isinstance(data, dict):
        return default_company_insight().newsSensitivity

    raw_items = data.get("items", [])
    items = [news_item_from_dict(item) for item in raw_items if isinstance(item, dict)]
    raw_keywords = data.get("matchedKeywords", [])
    matched_keywords = [str(item) for item in raw_keywords if isinstance(item, str)]
    return NewsSensitivityInsight(
        score=int(data.get("score", 0)),
        level=str(data.get("level", "低")),
        summary=str(data.get("summary", "暂无新闻与政策敏感度样本")),
        matchedKeywords=matched_keywords,
        items=items,
    )


def research_item_from_dict(data: dict) -> ResearchInsightItem:
    if not isinstance(data, dict):
        return ResearchInsightItem("", "", "", "", "", "")

    return ResearchInsightItem(
        date=str(data.get("date", "")),
        institution=str(data.get("institution", "")),
        rating=str(data.get("rating", "")),
        title=str(data.get("title", "")),
        industry=str(data.get("industry", "")),
        reportUrl=str(data.get("reportUrl", "")),
    )


def research_focus_from_dict(data: dict) -> ResearchFocusInsight:
    if not isinstance(data, dict):
        return default_company_insight().researchFocus

    raw_items = data.get("items", [])
    items = [research_item_from_dict(item) for item in raw_items if isinstance(item, dict)]
    raw_keywords = data.get("focusKeywords", [])
    focus_keywords = [str(item) for item in raw_keywords if isinstance(item, str)]
    return ResearchFocusInsight(
        monthlyReportCount=int(data.get("monthlyReportCount", 0)),
        summary=str(data.get("summary", "暂无券商研报样本")),
        focusKeywords=focus_keywords,
        items=items,
    )


def company_insight_from_dict(data: dict) -> CompanyInsight:
    if not isinstance(data, dict):
        return default_company_insight()

    return CompanyInsight(
        updatedAt=str(data.get("updatedAt", "")),
        accountingBusiness=accounting_business_from_dict(data.get("accountingBusiness", {})),
        officialBusiness=official_business_from_dict(data.get("officialBusiness", {})),
        newsSensitivity=news_sensitivity_from_dict(data.get("newsSensitivity", {})),
        researchFocus=research_focus_from_dict(data.get("researchFocus", {})),
    )


def macd_from_dict(data: dict) -> MacdIndicator:
    if not isinstance(data, dict):
        return MacdIndicator(0.0, 0.0, 0.0, "无数据", "等待样本", "neutral")

    return MacdIndicator(
        dif=float(data.get("dif", 0.0)),
        dea=float(data.get("dea", 0.0)),
        histogram=float(data.get("histogram", 0.0)),
        signalLabel=str(data.get("signalLabel", "无数据")),
        biasLabel=str(data.get("biasLabel", "等待样本")),
        tone=str(data.get("tone", "neutral")),
    )


def rsi_from_dict(data: dict) -> RsiIndicator:
    if not isinstance(data, dict):
        return RsiIndicator(9, 50.0, "无数据", "等待样本", "neutral")

    return RsiIndicator(
        period=int(data.get("period", 9)),
        value=float(data.get("value", 50.0)),
        signalLabel=str(data.get("signalLabel", "无数据")),
        biasLabel=str(data.get("biasLabel", "等待样本")),
        tone=str(data.get("tone", "neutral")),
    )


def technicals_from_dict(data: dict) -> TechnicalIndicators:
    if not isinstance(data, dict):
        return TechnicalIndicators(
            macd=MacdIndicator(0.0, 0.0, 0.0, "无数据", "等待样本", "neutral"),
            rsi14=RsiIndicator(9, 50.0, "无数据", "等待样本", "neutral"),
        )

    return TechnicalIndicators(
        macd=macd_from_dict(data.get("macd", {})),
        rsi14=rsi_from_dict(data.get("rsi14", {})),
    )


def bollinger_from_dict(data: dict) -> BollingerProfile:
    if not isinstance(data, dict):
        return default_bollinger()

    raw_points = data.get("points", [])
    points = [
        BollingerPoint(
            date=str(item.get("date", "")),
            middle=float(item.get("middle", 0.0)),
            upper=float(item.get("upper", 0.0)),
            lower=float(item.get("lower", 0.0)),
        )
        for item in raw_points
        if isinstance(item, dict)
    ]
    return BollingerProfile(
        period=int(data.get("period", 30)),
        stdMultiplier=float(data.get("stdMultiplier", 2.0)),
        points=points,
    )


def score_factor_from_dict(data: dict) -> ScoreFactor:
    if not isinstance(data, dict):
        return ScoreFactor("unknown", "未知", 0, 0, "neutral", "无数据")

    return ScoreFactor(
        key=str(data.get("key", "unknown")),
        label=str(data.get("label", "未知")),
        score=int(data.get("score", 0)),
        maxScore=int(data.get("maxScore", 0)),
        tone=str(data.get("tone", "neutral")),
        summary=str(data.get("summary", "无数据")),
    )


def selection_score_from_dict(data: dict) -> SelectionScore:
    if not isinstance(data, dict):
        return default_selection_score()

    raw_factors = data.get("factors", [])
    factors = [score_factor_from_dict(item) for item in raw_factors if isinstance(item, dict)]
    return SelectionScore(
        total=int(data.get("total", 0)),
        maxScore=int(data.get("maxScore", 100)),
        grade=str(data.get("grade", "D")),
        summary=str(data.get("summary", "等待更多信号")),
        factors=factors,
    )


def stock_from_dict(data: dict) -> WatchStock:
    raw_signals = data.get("signals", []) if isinstance(data, dict) else []
    signals = [
        Signal(
            label=str(item.get("label", "")),
            value=str(item.get("value", "")),
            level=str(item.get("level", "calm")),
        )
        for item in raw_signals
        if isinstance(item, dict)
    ]
    raw_candles = data.get("candles", []) if isinstance(data, dict) else []
    candles = [
        CandlePoint(
            date=str(item.get("date", "")),
            open=float(item.get("open", 0.0)),
            high=float(item.get("high", 0.0)),
            low=float(item.get("low", 0.0)),
            close=float(item.get("close", 0.0)),
            isLimitUpClose=bool(item.get("isLimitUpClose", False)),
        )
        for item in raw_candles
        if isinstance(item, dict)
    ]
    return WatchStock(
        symbol=str(data.get("symbol", "")),
        name=str(data.get("name", "")),
        market=str(data.get("market", "")),
        sector=str(data.get("sector", "")),
        price=float(data.get("price", 0.0)),
        changePct=float(data.get("changePct", 0.0)),
        momentum=int(data.get("momentum", 0)),
        volumeRatio=float(data.get("volumeRatio", 0.0)),
        note=str(data.get("note", "")),
        thesis=str(data.get("thesis", "")),
        sparkline=[float(value) for value in data.get("sparkline", [])],
        candles=candles,
        limitUpSignal=limit_up_signal_from_dict(data.get("limitUpSignal", {})),
        bollinger=bollinger_from_dict(data.get("bollinger", {})),
        chipDistribution=chip_distribution_from_dict(data.get("chipDistribution", {})),
        signals=signals,
        metadata=metadata_from_dict(data.get("metadata", {})),
        companyInsight=company_insight_from_dict(data.get("companyInsight", {})),
        technicals=technicals_from_dict(data.get("technicals", {})),
        selectionScore=selection_score_from_dict(data.get("selectionScore", {})),
        priceDistribution=distribution_from_dict(data.get("priceDistribution", {})),
        amplitudeDistribution=amplitude_distribution_from_dict(data.get("amplitudeDistribution", {})),
        themeLinkage=stock_theme_linkage_from_dict(data.get("themeLinkage", {})),
    )


def ensure_cache_dirs() -> None:
    HIST_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    STOCK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CAP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    META_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    BOARD_LIST_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    BOARD_MEMBER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    US_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def read_watchlist_entries() -> list[dict[str, str]]:
    if WATCHLIST_TS_PATH.exists():
        content = WATCHLIST_TS_PATH.read_text(encoding="utf-8")
        entries = [
            {
                "code": match.group("code"),
                "name": match.group("name").strip() or match.group("code"),
            }
            for match in WATCHLIST_ENTRY_PATTERN.finditer(content)
        ]
        if entries:
            return entries

    if WATCHLIST_PATH.exists():
        content = WATCHLIST_PATH.read_text(encoding="utf-8")
        return [
            {
                "code": line.strip().lstrip("\ufeff"),
                "name": line.strip().lstrip("\ufeff"),
            }
            for line in content.splitlines()
            if line.strip()
        ]

    raise FileNotFoundError("未找到自选池文件：src/data/watchlist.ts 或 watchlist_codes.txt")


def read_codes() -> list[str]:
    return [item["code"] for item in read_watchlist_entries()]


def read_watchlist_name_map() -> dict[str, str]:
    return {item["code"]: item["name"] for item in read_watchlist_entries()}


def normalize_label(value: object) -> str:
    text = str(value).strip()
    try:
        repaired = text.encode("gbk").decode("utf-8")
        return repaired.strip() or text
    except UnicodeError:
        return text


def normalize_website_url(value: object) -> str:
    text = normalize_label(value).strip().rstrip("/")
    if text.lower() in {"", "none", "nan", "null"}:
        return ""
    if not text.startswith(("http://", "https://")):
        text = f"https://{text}"
    return text


def default_technicals() -> TechnicalIndicators:
    return TechnicalIndicators(
        macd=MacdIndicator(
            dif=0.0,
            dea=0.0,
            histogram=0.0,
            signalLabel="无数据",
            biasLabel="等待样本",
            tone="neutral",
        ),
        rsi14=RsiIndicator(
            period=9,
            value=50.0,
            signalLabel="无数据",
            biasLabel="等待样本",
            tone="neutral",
        ),
    )


def default_bollinger() -> BollingerProfile:
    return BollingerProfile(period=30, stdMultiplier=2.0, points=[])


def default_limit_up_signal() -> LimitUpSignalProfile:
    return LimitUpSignalProfile(
        recentLimitUpCount10=0,
        isHoldingAboveOpen=False,
        anchorDate="",
        anchorOpen=0.0,
        anchorClose=0.0,
        holdDays=0,
        currentBiasPct=0.0,
        tone="neutral",
        summary="暂无涨停守开信号",
    )


def default_chip_distribution(current_price: float = 0.0) -> ChipDistributionProfile:
    base_price = round(current_price, 2) if current_price > 0 else 0.0
    return ChipDistributionProfile(
        algorithm="turnover_decay_v1",
        bucketSize=0.1,
        sampleSize=0,
        tradeDate="",
        mainCost=base_price,
        mainCostZoneLow=base_price,
        mainCostZoneHigh=base_price,
        mainCostZoneWidthPct=0.0,
        averageCost=base_price,
        winnerRatio=0.0,
        dominantRatio=0.0,
        concentration70Low=base_price,
        concentration70High=base_price,
        concentration90Low=base_price,
        concentration90High=base_price,
        currentPriceBiasPct=0.0,
        shapeLabel="筹码待观察",
        stageLabel="等待样本",
        riskLabel="暂无主力成本区样本",
        tone="neutral",
        summary="暂无筹码分布样本",
        controlEvidence=[],
        bands=[],
    )


def default_selection_score() -> SelectionScore:
    return SelectionScore(
        total=0,
        maxScore=100,
        grade="D",
        summary="等待更多信号",
        factors=[],
    )


def default_stock_theme_linkage() -> StockThemeLinkage:
    return StockThemeLinkage(
        updatedAt="",
        industry="",
        concepts=[],
        matchedKeywords=[],
        hotBoards=[],
        relatedEtfs=[],
        summary="暂无板块联动结果",
    )


def default_company_insight() -> CompanyInsight:
    return CompanyInsight(
        updatedAt="",
        accountingBusiness=AccountingBusinessInsight(
            reportDate="",
            classification="",
            summary="暂无会计主营拆分数据",
            segments=[],
        ),
        officialBusiness=OfficialBusinessInsight(
            companyName="",
            industry="",
            mainBusiness="",
            businessScope="",
            companyIntro="",
        ),
        newsSensitivity=NewsSensitivityInsight(
            score=0,
            level="低",
            summary="暂无新闻与政策敏感度样本",
            matchedKeywords=[],
            items=[],
        ),
        researchFocus=ResearchFocusInsight(
            monthlyReportCount=0,
            summary="暂无券商研报样本",
            focusKeywords=[],
            items=[],
        ),
    )


def default_us_market_pulse() -> UsMarketPulse:
    return UsMarketPulse(
        updatedAt="",
        tradeDate="",
        summary="暂无隔夜美股晨报",
        items=[],
    )


def default_market_breadth() -> MarketBreadthProfile:
    return MarketBreadthProfile(
        updatedAt="",
        tradeDate="",
        activityPct=0.0,
        upCount=0,
        downCount=0,
        flatCount=0,
        limitUpCount=0,
        limitDownCount=0,
        netAdvance=0,
        advanceDeclineRatio=0.0,
        breadthLow=0,
        breadthHigh=0,
        tone="neutral",
        signalLabel="鏆傛棤甯傚満瀹藉害鏍锋湰",
        summary="鏆傛棤涓婃定/涓嬭穼瀹舵暟鏇茬嚎",
        trendPoints=[],
    )


def default_market_radar() -> MarketRadar:
    return MarketRadar(
        updatedAt="",
        hottestBoards=[],
        hottestEtfs=[],
        usMarketPulse=default_us_market_pulse(),
        marketBreadth=default_market_breadth(),
    )


def normalize_text_block(value: object) -> str:
    text = normalize_label(value)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def to_float(value: object, default: float = 0.0) -> float:
    try:
        result = float(value)
        if math.isnan(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def is_shanghai_symbol(symbol: str) -> bool:
    return symbol.startswith(("600", "601", "603", "605", "688", "900"))


def baostock_symbol(symbol: str) -> str | None:
    if is_shanghai_symbol(symbol):
        return f"sh.{symbol}"
    if symbol.startswith(("000", "001", "002", "003", "200", "300", "301")):
        return f"sz.{symbol}"
    return None


def ensure_baostock_login() -> None:
    global _BAOSTOCK_LOGGED_IN
    if _BAOSTOCK_LOGGED_IN:
        return

    result = bs.login()
    if result.error_code != "0":
        raise RuntimeError(f"baostock login failed: {result.error_code} {result.error_msg}")
    _BAOSTOCK_LOGGED_IN = True


def logout_baostock() -> None:
    global _BAOSTOCK_LOGGED_IN
    if not _BAOSTOCK_LOGGED_IN:
        return

    try:
        bs.logout()
    finally:
        _BAOSTOCK_LOGGED_IN = False


def truncate_text(value: object, limit: int) -> str:
    text = normalize_text_block(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


def format_date_value(value: object) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        try:
            return str(value.isoformat())
        except TypeError:
            pass
    return normalize_text_block(value)


def unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in values:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def normalize_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)

    text = normalize_text_block(value)
    if not text:
        return default
    text = text.replace("%", "").replace(",", "")
    try:
        return float(text)
    except ValueError:
        return default


def normalize_int(value: object, default: int = 0) -> int:
    return int(round(normalize_float(value, float(default))))


def tone_from_change(change_pct: float) -> str:
    if change_pct >= 1.5:
        return "positive"
    if change_pct <= -1.5:
        return "negative"
    return "neutral"


def symbol_for_zygc(symbol: str) -> str:
    prefix = "SH" if symbol.startswith(("600", "601", "603", "605", "688")) else "SZ"
    return f"{prefix}{symbol}"


def extract_theme_keywords(*texts: object) -> list[str]:
    haystack = " ".join(normalize_text_block(item) for item in texts if item is not None)
    matched = [keyword for keyword in THEME_KEYWORDS + POLICY_KEYWORDS if keyword and keyword in haystack]
    return unique_in_order(matched)


def extract_actionable_theme_keywords(*texts: object) -> list[str]:
    return [keyword for keyword in extract_theme_keywords(*texts) if keyword not in BOARD_NOISE_KEYWORDS]


def score_news_level(score: int) -> str:
    if score >= 65:
        return "高"
    if score >= 35:
        return "中"
    return "低"


def has_meaningful_company_insight(company_insight: CompanyInsight | None) -> bool:
    if not company_insight:
        return False

    return any(
        [
            bool(company_insight.accountingBusiness.segments),
            bool(company_insight.officialBusiness.mainBusiness),
            bool(company_insight.newsSensitivity.items),
            bool(company_insight.researchFocus.items),
        ]
    )


def calc_signal_level(value: float, strong_threshold: float, watch_threshold: float) -> str:
    if value >= strong_threshold:
        return "strong"
    if value >= watch_threshold:
        return "watch"
    return "calm"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_json_cache(path: Path) -> dict | None:
    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_snapshot_stock_map() -> dict[str, WatchStock]:
    if not OUTPUT_PATH.exists():
        return {}

    try:
        payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    raw_stocks = payload.get("stocks", []) if isinstance(payload, dict) else []
    stock_map: dict[str, WatchStock] = {}
    for item in raw_stocks:
        if not isinstance(item, dict):
            continue
        try:
            stock = stock_from_dict(item)
        except (TypeError, ValueError):
            continue
        if stock.symbol:
            stock_map[stock.symbol] = stock

    return stock_map


def load_snapshot_payload() -> dict:
    if not OUTPUT_PATH.exists():
        return {}

    try:
        payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    return payload if isinstance(payload, dict) else {}


def sanitize_json_value(value):
    if isinstance(value, float):
        return value if math.isfinite(value) else 0.0
    if isinstance(value, dict):
        return {key: sanitize_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_json_value(item) for item in value]
    return value


def write_json_cache(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_payload = sanitize_json_value(payload)
    path.write_text(json.dumps(safe_payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def get_cache_time(payload: dict | None) -> datetime | None:
    if not payload:
        return None

    raw_value = payload.get("fetchedAt")
    if not isinstance(raw_value, str):
        return None

    try:
        return datetime.fromisoformat(raw_value)
    except ValueError:
        return None


def is_cache_fresh(payload: dict | None, ttl_seconds: int) -> bool:
    cached_at = get_cache_time(payload)
    if not cached_at:
        return False
    return (datetime.now() - cached_at).total_seconds() <= ttl_seconds


def append_name_rows(name_map: dict[str, str], frame: pd.DataFrame, code_col: str, name_col: str) -> None:
    normalized = frame.copy()
    normalized[code_col] = normalized[code_col].astype(str).str.zfill(6)
    for _, row in normalized.iterrows():
        code = str(row[code_col]).zfill(6)
        name_map[code] = normalize_label(row[name_col])


def load_name_cache() -> tuple[dict[str, str], dict | None]:
    payload = load_json_cache(NAME_CACHE_PATH)
    raw_map = payload.get("data", {}) if payload else {}
    if not isinstance(raw_map, dict):
        return {}, payload

    return ({str(code): normalize_label(name) for code, name in raw_map.items()}, payload)


def fetch_name_map(codes: list[str]) -> dict[str, str]:
    cached_map, cached_payload = load_name_cache()
    cached_subset = {code: cached_map[code] for code in codes if code in cached_map}

    if len(cached_subset) == len(codes) and is_cache_fresh(cached_payload, NAME_CACHE_TTL_SECONDS):
        return cached_subset

    name_map: dict[str, str] = {}

    try:
        sh_df = ak.stock_info_sh_name_code(symbol=SH_MAIN)
        append_name_rows(name_map, sh_df, SH_CODE_COL, SH_NAME_COL)
    except Exception as exc:
        print(f"Warning: failed to fetch SH name map: {exc}")

    try:
        kc_df = ak.stock_info_sh_name_code(symbol=STAR_BOARD)
        append_name_rows(name_map, kc_df, SH_CODE_COL, SH_NAME_COL)
    except Exception as exc:
        print(f"Warning: failed to fetch STAR name map: {exc}")

    try:
        sz_df = ak.stock_info_sz_name_code(symbol=SZ_A_LIST)
        append_name_rows(name_map, sz_df, SZ_CODE_COL, SZ_NAME_COL)
    except Exception as exc:
        print(f"Warning: failed to fetch SZ name map: {exc}")

    try:
        bj_df = ak.stock_info_bj_name_code()
        append_name_rows(name_map, bj_df, BJ_CODE_COL, BJ_NAME_COL)
    except Exception as exc:
        print(f"Warning: failed to fetch BJ name map: {exc}")

    if name_map:
        merged_map = {**cached_map, **name_map}
        write_json_cache(
            NAME_CACHE_PATH,
            {
                "fetchedAt": now_iso(),
                "data": merged_map,
            },
        )
        return {code: merged_map[code] for code in codes if code in merged_map}

    return cached_subset


def load_spot_cache() -> tuple[dict[str, dict], dict | None]:
    payload = load_json_cache(SPOT_CACHE_PATH)
    raw_map = payload.get("data", {}) if payload else {}
    if not isinstance(raw_map, dict):
        return {}, payload

    normalized_map: dict[str, dict] = {}
    for code, row in raw_map.items():
        if isinstance(row, dict):
            normalized_map[str(code)] = row
    return normalized_map, payload


def fetch_spot_map(codes: list[str]) -> dict[str, dict]:
    cached_map, cached_payload = load_spot_cache()
    cached_subset = {code: cached_map[code] for code in codes if code in cached_map}

    if len(cached_subset) == len(codes) and is_cache_fresh(cached_payload, SPOT_CACHE_TTL_SECONDS):
        return cached_subset

    try:
        spot_df = ak.stock_zh_a_spot_em()
        spot_df[C_CODE] = spot_df[C_CODE].astype(str).str.zfill(6)
        filtered = spot_df[spot_df[C_CODE].isin(codes)].copy()
        fresh_map = filtered.set_index(C_CODE).to_dict(orient="index")

        if fresh_map:
          merged_map = {**cached_map, **fresh_map}
          write_json_cache(
              SPOT_CACHE_PATH,
              {
                  "fetchedAt": now_iso(),
                  "data": merged_map,
              },
          )
          return {code: merged_map[code] for code in codes if code in merged_map}
    except Exception as exc:
        print(f"Warning: failed to fetch spot snapshot: {exc}")

    return cached_subset


def hist_cache_path(symbol: str) -> Path:
    return HIST_CACHE_DIR / f"{symbol}.json"


def stock_cache_path(symbol: str) -> Path:
    return STOCK_CACHE_DIR / f"{symbol}.json"


def cap_cache_path(symbol: str) -> Path:
    return CAP_CACHE_DIR / f"{symbol}.json"


def meta_cache_path(symbol: str) -> Path:
    return META_CACHE_DIR / f"{symbol}.json"


def board_list_cache_path(board_type: str) -> Path:
    return BOARD_LIST_CACHE_DIR / f"{board_type}.json"


def board_member_cache_path(board_type: str, board_code: str) -> Path:
    return BOARD_MEMBER_CACHE_DIR / f"{board_type}-{board_code}.json"


def us_daily_cache_path(symbol: str) -> Path:
    return US_CACHE_DIR / f"{symbol.lower()}-daily.json"


def us_news_cache_path(symbol: str) -> Path:
    safe_symbol = re.sub(r"[^A-Za-z0-9_-]+", "-", symbol)
    return US_CACHE_DIR / f"{safe_symbol.lower()}-news.json"


def load_frame_cache(path: Path) -> tuple[pd.DataFrame, dict | None]:
    payload = load_json_cache(path)
    rows = payload.get("rows", []) if payload else []
    if not isinstance(rows, list):
        return pd.DataFrame(), payload
    return pd.DataFrame(rows), payload


def write_frame_cache(path: Path, frame: pd.DataFrame, extra: dict | None = None) -> None:
    payload = {
        "fetchedAt": now_iso(),
        "rows": frame.to_dict(orient="records"),
    }
    if extra:
        payload.update(extra)
    write_json_cache(path, payload)


def load_hist_cache(symbol: str) -> tuple[pd.DataFrame, dict | None]:
    payload = load_json_cache(hist_cache_path(symbol))
    rows = payload.get("rows", []) if payload else []
    if not isinstance(rows, list) or not rows:
        return pd.DataFrame(), payload

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame, payload

    normalized = frame.copy()
    column_map = {}
    if "close" in normalized.columns and C_CLOSE not in normalized.columns:
        column_map["close"] = C_CLOSE
    if "high" in normalized.columns and C_HIGH not in normalized.columns:
        column_map["high"] = C_HIGH
    if "low" in normalized.columns and C_LOW not in normalized.columns:
        column_map["low"] = C_LOW
    if "amount" in normalized.columns and "volume" not in normalized.columns and C_VOLUME not in normalized.columns:
        column_map["amount"] = C_VOLUME
    if column_map:
        normalized = normalized.rename(columns=column_map)

    if "date" not in normalized.columns and "日期" in normalized.columns:
        normalized["date"] = normalized["日期"].astype(str)
    elif "日期" not in normalized.columns and "date" in normalized.columns:
        normalized["日期"] = normalized["date"].astype(str)

    if C_CLOSE not in normalized.columns:
        return pd.DataFrame(), payload

    normalized[C_CLOSE] = pd.to_numeric(normalized[C_CLOSE], errors="coerce")
    if C_HIGH in normalized.columns:
        normalized[C_HIGH] = pd.to_numeric(normalized[C_HIGH], errors="coerce")
    if C_LOW in normalized.columns:
        normalized[C_LOW] = pd.to_numeric(normalized[C_LOW], errors="coerce")
    if C_VOLUME in normalized.columns:
        normalized[C_VOLUME] = pd.to_numeric(normalized[C_VOLUME], errors="coerce")
    if C_CHANGE in normalized.columns:
        normalized[C_CHANGE] = pd.to_numeric(normalized[C_CHANGE], errors="coerce")

    return normalized.dropna(subset=[C_CLOSE]), payload


def write_hist_cache(symbol: str, start_date: str, end_date: str, hist_df: pd.DataFrame) -> None:
    write_json_cache(
        hist_cache_path(symbol),
        {
            "fetchedAt": now_iso(),
            "startDate": start_date,
            "endDate": end_date,
            "rows": hist_df.to_dict(orient="records"),
        },
    )


def is_hist_cache_fresh(payload: dict | None, start_date: str, end_date: str) -> bool:
    if not payload:
        return False
    if payload.get("startDate") != start_date or payload.get("endDate") != end_date:
        return False
    return is_cache_fresh(payload, HIST_CACHE_TTL_SECONDS)


def load_stock_cache(symbol: str) -> tuple[WatchStock | None, dict | None]:
    payload = load_json_cache(stock_cache_path(symbol))
    raw_stock = payload.get("data") if payload else None
    if not isinstance(raw_stock, dict):
        return None, payload

    try:
        return stock_from_dict(raw_stock), payload
    except (TypeError, ValueError):
        return None, payload


def write_stock_cache(symbol: str, start_date: str, end_date: str, stock: WatchStock) -> None:
    write_json_cache(
        stock_cache_path(symbol),
        {
            "version": STOCK_CACHE_VERSION,
            "fetchedAt": now_iso(),
            "startDate": start_date,
            "endDate": end_date,
            "data": asdict(stock),
        },
    )


def is_stock_cache_fresh(payload: dict | None, start_date: str, end_date: str) -> bool:
    if not payload:
        return False
    if payload.get("version") != STOCK_CACHE_VERSION:
        return False
    if payload.get("startDate") != start_date or payload.get("endDate") != end_date:
        return False
    return is_cache_fresh(payload, HIST_CACHE_TTL_SECONDS)


def load_cap_cache(symbol: str) -> tuple[float | None, dict | None]:
    payload = load_json_cache(cap_cache_path(symbol))
    if not payload:
        return None, payload

    raw_value = payload.get("marketCapYi")
    try:
        return float(raw_value), payload
    except (TypeError, ValueError):
        return None, payload


def write_cap_cache(symbol: str, market_cap_yi: float) -> None:
    write_json_cache(
        cap_cache_path(symbol),
        {
            "fetchedAt": now_iso(),
            "marketCapYi": round(market_cap_yi, 2),
        },
    )


def load_meta_cache(symbol: str) -> tuple[StockMetadata | None, dict | None]:
    payload = load_json_cache(meta_cache_path(symbol))
    raw_value = payload.get("data") if payload else None
    if not isinstance(raw_value, dict):
        return None, payload

    return metadata_from_dict(raw_value), payload


def write_meta_cache(symbol: str, metadata: StockMetadata) -> None:
    write_json_cache(
        meta_cache_path(symbol),
        {
            "fetchedAt": now_iso(),
            "data": asdict(metadata),
        },
    )


def fetch_stock_metadata(symbol: str, fallback_metadata: StockMetadata | None = None) -> StockMetadata:
    cached_metadata, cached_payload = load_meta_cache(symbol)
    if cached_metadata and cached_metadata.officialWebsite and is_cache_fresh(cached_payload, META_CACHE_TTL_SECONDS):
        return cached_metadata

    try:
        profile_df = ak.stock_profile_cninfo(symbol=symbol)
        if not profile_df.empty and C_WEBSITE in profile_df.columns:
            official_website = normalize_website_url(profile_df.iloc[0].get(C_WEBSITE, ""))
            if official_website:
                metadata = StockMetadata(
                    officialWebsite=official_website,
                    websiteSource="cninfo",
                )
                write_meta_cache(symbol, metadata)
                return metadata
    except Exception as exc:
        print(f"Warning: failed to fetch profile metadata for {symbol}: {exc}")

    if cached_metadata and cached_metadata.officialWebsite:
        return cached_metadata
    if fallback_metadata and fallback_metadata.officialWebsite:
        return fallback_metadata
    return StockMetadata(officialWebsite="", websiteSource="")


def build_accounting_business_insight(
    symbol: str,
    fallback_insight: AccountingBusinessInsight | None = None,
) -> AccountingBusinessInsight:
    try:
        accounting_df = ak.stock_zygc_em(symbol=symbol_for_zygc(symbol))
        if accounting_df.empty:
            raise ValueError("empty accounting business frame")

        frame = accounting_df.copy()
        for column in ["主营收入", "收入比例", "主营利润", "利润比例", "毛利率"]:
            if column in frame.columns:
                frame[column] = pd.to_numeric(frame[column], errors="coerce")

        latest_report = frame["报告日期"].dropna().max() if "报告日期" in frame.columns else None
        if latest_report is not None:
            frame = frame[frame["报告日期"] == latest_report].copy()

        preferred_types = ["按产品分类", "按行业分类", "按业务分类"]
        selected_type = ""
        for preferred in preferred_types:
            candidate = frame[frame["分类类型"] == preferred].copy() if "分类类型" in frame.columns else pd.DataFrame()
            if not candidate.empty:
                frame = candidate
                selected_type = preferred
                break

        if not selected_type and "分类类型" in frame.columns and not frame.empty:
            selected_type = normalize_text_block(frame.iloc[0].get("分类类型", ""))

        frame = frame.sort_values(by="收入比例", ascending=False, na_position="last").head(5)
        segments: list[AccountingBusinessSegment] = []
        for _, row in frame.iterrows():
            name = normalize_text_block(row.get("主营构成", ""))
            if not name:
                continue
            segments.append(
                AccountingBusinessSegment(
                    name=name,
                    revenueYi=round(float(row.get("主营收入", 0.0) or 0.0) / 100000000, 2),
                    revenueRatio=round(float(row.get("收入比例", 0.0) or 0.0), 4),
                    profitYi=round(float(row.get("主营利润", 0.0) or 0.0) / 100000000, 2),
                    profitRatio=round(float(row.get("利润比例", 0.0) or 0.0), 4),
                    grossMargin=round(float(row.get("毛利率", 0.0) or 0.0), 4),
                )
            )

        if segments:
            head_labels = [f"{segment.name}{segment.revenueRatio * 100:.1f}%" for segment in segments[:2] if segment.revenueRatio > 0]
            concentration = sum(segment.revenueRatio for segment in segments[:2])
            concentration_label = "主营集中度较高" if concentration >= 0.6 else "主营分布相对均衡"
            summary = "；".join(part for part in [
                f"{format_date_value(latest_report)} {selected_type}口径",
                "、".join(head_labels) if head_labels else "",
                concentration_label,
            ] if part)
            return AccountingBusinessInsight(
                reportDate=format_date_value(latest_report),
                classification=selected_type,
                summary=summary or "已抓取最近一期会计主营结构",
                segments=segments,
            )
    except Exception as exc:
        print(f"Warning: failed to fetch accounting business for {symbol}: {exc}")

    if fallback_insight and fallback_insight.segments:
        return fallback_insight
    return default_company_insight().accountingBusiness


def build_official_business_insight(
    symbol: str,
    fallback_insight: OfficialBusinessInsight | None = None,
) -> OfficialBusinessInsight:
    try:
        profile_df = ak.stock_profile_cninfo(symbol=symbol)
        if not profile_df.empty:
            row = profile_df.iloc[0]
            official_business = OfficialBusinessInsight(
                companyName=normalize_text_block(row.get("公司名称", "")),
                industry=normalize_text_block(row.get("所属行业", "")),
                mainBusiness=truncate_text(row.get("主营业务", ""), 160),
                businessScope=truncate_text(row.get("经营范围", ""), 220),
                companyIntro=truncate_text(row.get("机构简介", ""), 260),
            )
            if any(
                [
                    official_business.companyName,
                    official_business.mainBusiness,
                    official_business.businessScope,
                    official_business.companyIntro,
                ]
            ):
                return official_business
    except Exception as exc:
        print(f"Warning: failed to fetch official business for {symbol}: {exc}")

    if fallback_insight and any([fallback_insight.companyName, fallback_insight.mainBusiness, fallback_insight.businessScope]):
        return fallback_insight
    return default_company_insight().officialBusiness


def build_news_sensitivity_insight(
    symbol: str,
    fallback_insight: NewsSensitivityInsight | None = None,
) -> NewsSensitivityInsight:
    try:
        news_df = ak.stock_news_em(symbol=symbol)
        if news_df.empty:
            raise ValueError("empty news frame")

        frame = news_df.copy()
        if "发布时间" in frame.columns:
            frame["sort_time"] = pd.to_datetime(frame["发布时间"], errors="coerce")
            frame = frame.sort_values(by="sort_time", ascending=False, na_position="last")

        collected_items: list[tuple[int, float, NewsInsightItem]] = []
        collected_keywords: list[str] = []
        total_score = 0
        for _, row in frame.head(20).iterrows():
            title = normalize_text_block(row.get("新闻标题", ""))
            content = normalize_text_block(row.get("新闻内容", ""))
            source = normalize_text_block(row.get("文章来源", ""))
            url = normalize_text_block(row.get("新闻链接", ""))
            publish_time = format_date_value(row.get("发布时间", ""))
            matched_keywords = extract_theme_keywords(title, content)
            policy_hit = any(keyword in f"{title} {content}" for keyword in POLICY_KEYWORDS)

            sort_time = row.get("sort_time")
            recency_score = 0
            sort_timestamp = 0.0
            if pd.notna(sort_time):
                delta_days = max(0, (datetime.now() - sort_time.to_pydatetime()).days)
                sort_timestamp = sort_time.timestamp()
                if delta_days <= 7:
                    recency_score = 4
                elif delta_days <= 30:
                    recency_score = 2

            row_score = 0
            if matched_keywords:
                row_score += 14 + min(len(matched_keywords) * 4, 16)
            if policy_hit:
                row_score += 8
            row_score += recency_score
            total_score += row_score
            collected_keywords.extend(matched_keywords)

            if row_score > 0 or len(collected_items) < 3:
                collected_items.append(
                    (
                        row_score,
                        sort_timestamp,
                        NewsInsightItem(
                            title=title,
                            publishTime=publish_time,
                            source=source,
                            url=url,
                            excerpt=truncate_text(content, 120),
                            matchedKeywords=matched_keywords,
                        ),
                    )
                )

        matched_keywords = unique_in_order(collected_keywords)[:8]
        items = [
            item
            for _, _, item in sorted(
                collected_items,
                key=lambda entry: (entry[0], entry[1]),
                reverse=True,
            )[:5]
        ]
        score = min(100, total_score)
        level = score_news_level(score)

        if matched_keywords:
            summary = f"近端新闻/政策敏感度{level}，焦点集中在{'、'.join(matched_keywords[:4])}"
        else:
            summary = "近端相关新闻以行情异动和榜单信息为主，暂未提炼出明确政策或主题催化"

        if items:
            return NewsSensitivityInsight(
                score=score,
                level=level,
                summary=summary,
                matchedKeywords=matched_keywords,
                items=items,
            )
    except Exception as exc:
        print(f"Warning: failed to fetch news sensitivity for {symbol}: {exc}")

    if fallback_insight and fallback_insight.items:
        return fallback_insight
    return default_company_insight().newsSensitivity


def build_research_focus_insight(
    symbol: str,
    fallback_insight: ResearchFocusInsight | None = None,
) -> ResearchFocusInsight:
    try:
        report_df = ak.stock_research_report_em(symbol=symbol)
        if report_df.empty:
            raise ValueError("empty research report frame")

        frame = report_df.copy()
        if "日期" in frame.columns:
            frame["sort_date"] = pd.to_datetime(frame["日期"], errors="coerce")
            frame = frame.sort_values(by="sort_date", ascending=False, na_position="last")

        monthly_report_count = 0
        if "近一月个股研报数" in frame.columns:
            monthly_counts = pd.to_numeric(frame["近一月个股研报数"], errors="coerce").dropna()
            if not monthly_counts.empty:
                monthly_report_count = int(monthly_counts.max())

        items: list[ResearchInsightItem] = []
        focus_keywords: list[str] = []
        institutions: list[str] = []
        rating_labels: list[str] = []
        for _, row in frame.head(6).iterrows():
            title = normalize_text_block(row.get("报告名称", ""))
            industry = normalize_text_block(row.get("行业", ""))
            institution = normalize_text_block(row.get("机构", ""))
            rating = normalize_text_block(row.get("东财评级", "")) or "未披露评级"
            report_url = normalize_text_block(row.get("报告PDF链接", ""))
            report_date = format_date_value(row.get("日期", ""))

            items.append(
                ResearchInsightItem(
                    date=report_date,
                    institution=institution,
                    rating=rating,
                    title=title,
                    industry=industry,
                    reportUrl=report_url,
                )
            )
            focus_keywords.extend(extract_theme_keywords(title, industry))
            if industry and not focus_keywords:
                focus_keywords.append(industry)
            institutions.append(institution)
            if rating != "未披露评级":
                rating_labels.append(rating)

        focus_keywords = unique_in_order(focus_keywords)[:8]
        institutions = unique_in_order(institutions)[:3]
        rating_labels = unique_in_order(rating_labels)[:3]
        rating_text = f"评级标签：{'、'.join(rating_labels)}" if rating_labels else "评级标签披露较少"
        theme_text = f"关注主题：{'、'.join(focus_keywords[:4])}" if focus_keywords else "主题标签暂不集中"
        institution_text = f"覆盖机构：{'、'.join(institutions)}" if institutions else ""
        summary = "；".join(
            part
            for part in [
                f"近一月研报数 {monthly_report_count or len(items)}",
                theme_text,
                rating_text,
                institution_text,
            ]
            if part
        )
        if items:
            return ResearchFocusInsight(
                monthlyReportCount=monthly_report_count or len(items),
                summary=summary or "已抓取券商研报样本",
                focusKeywords=focus_keywords,
                items=items,
            )
    except Exception as exc:
        print(f"Warning: failed to fetch research focus for {symbol}: {exc}")

    if fallback_insight and fallback_insight.items:
        return fallback_insight
    return default_company_insight().researchFocus


def build_company_insight(symbol: str, fallback_insight: CompanyInsight | None = None) -> CompanyInsight:
    fallback = fallback_insight or default_company_insight()
    company_insight = CompanyInsight(
        updatedAt=datetime.now().strftime("%Y-%m-%d %H:%M"),
        accountingBusiness=build_accounting_business_insight(symbol, fallback.accountingBusiness),
        officialBusiness=build_official_business_insight(symbol, fallback.officialBusiness),
        newsSensitivity=build_news_sensitivity_insight(symbol, fallback.newsSensitivity),
        researchFocus=build_research_focus_insight(symbol, fallback.researchFocus),
    )
    if has_meaningful_company_insight(company_insight):
        return company_insight
    return fallback


def fetch_with_retries(fetcher, attempts: int = 3, sleep_seconds: float = 0.8):
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fetcher()
        except Exception as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(sleep_seconds * attempt)
    if last_error:
        raise last_error
    raise RuntimeError("fetch failed without an explicit error")


def build_theme_hotspot(row: dict | pd.Series, board_type: str, match_reason: str = "") -> ThemeHotspot:
    source = row.to_dict() if isinstance(row, pd.Series) else row
    return ThemeHotspot(
        boardType=board_type,
        name=normalize_label(source.get("板块名称") or source.get("基金简称") or source.get("名称") or ""),
        code=str(source.get("板块代码") or source.get("基金代码") or source.get("代码") or ""),
        rank=normalize_int(source.get("排名"), 0),
        changePct=round(normalize_float(source.get("涨跌幅") or source.get("增长率数值") or source.get("增长率")), 2),
        riseCount=normalize_int(source.get("上涨家数"), 0),
        fallCount=normalize_int(source.get("下跌家数"), 0),
        leaderName=normalize_label(source.get("领涨股票") or ""),
        leaderCode=str(source.get("领涨股票代码") or ""),
        leaderChangePct=round(normalize_float(source.get("领涨股票-涨跌幅")), 2),
        matchReason=match_reason,
    )


def fetch_hot_board_frame(board_type: str) -> pd.DataFrame:
    cache_path = board_list_cache_path(board_type)
    cached_df, cached_payload = load_frame_cache(cache_path)
    if not cached_df.empty and is_cache_fresh(cached_payload, BOARD_LIST_CACHE_TTL_SECONDS):
        return cached_df

    fetcher = ak.stock_board_concept_name_em if board_type == "concept" else ak.stock_board_industry_name_em
    try:
        frame = fetch_with_retries(fetcher)
        if isinstance(frame, pd.DataFrame) and not frame.empty:
            write_frame_cache(cache_path, frame)
            return frame
    except Exception as exc:
        print(f"Warning: failed to fetch {board_type} board list: {exc}")

    return cached_df


def fetch_board_member_frame(board: ThemeHotspot) -> pd.DataFrame:
    board_code = board.code or board.name
    cache_path = board_member_cache_path(board.boardType, board_code or board.name)
    cached_df, cached_payload = load_frame_cache(cache_path)
    if not cached_df.empty and is_cache_fresh(cached_payload, BOARD_MEMBER_CACHE_TTL_SECONDS):
        return cached_df

    fetcher = ak.stock_board_concept_cons_em if board.boardType == "concept" else ak.stock_board_industry_cons_em
    board_symbol = board.code or board.name
    try:
        frame = fetch_with_retries(lambda: fetcher(symbol=board_symbol), attempts=2, sleep_seconds=1.0)
        if isinstance(frame, pd.DataFrame) and not frame.empty:
            normalized = frame.copy()
            if "代码" in normalized.columns:
                normalized["代码"] = normalized["代码"].astype(str).str.zfill(6)
            write_frame_cache(cache_path, normalized, {"boardName": board.name, "boardCode": board.code})
            return normalized
    except Exception as exc:
        print(f"Warning: failed to fetch {board.boardType} members for {board.name}: {exc}")

    return cached_df


def fetch_etf_daily_frame() -> pd.DataFrame:
    cached_df, cached_payload = load_frame_cache(ETF_DAILY_CACHE_PATH)
    if not cached_df.empty and is_cache_fresh(cached_payload, ETF_DAILY_CACHE_TTL_SECONDS):
        return cached_df

    try:
        frame = fetch_with_retries(ak.fund_etf_fund_daily_em, attempts=2, sleep_seconds=1.0)
        if isinstance(frame, pd.DataFrame) and not frame.empty:
            normalized = frame.copy()
            normalized["基金代码"] = normalized["基金代码"].astype(str).str.zfill(6)
            normalized["基金简称"] = normalized["基金简称"].astype(str)
            normalized["类型"] = normalized["类型"].astype(str)
            normalized["增长率数值"] = normalized["增长率"].apply(normalize_float)
            normalized["市价数值"] = normalized["市价"].apply(normalize_float)
            write_frame_cache(ETF_DAILY_CACHE_PATH, normalized)
            return normalized
    except Exception as exc:
        print(f"Warning: failed to fetch ETF daily data: {exc}")

    return cached_df


def fetch_us_daily_frame(symbol: str) -> pd.DataFrame:
    cache_path = us_daily_cache_path(symbol)
    cached_df, cached_payload = load_frame_cache(cache_path)
    if not cached_df.empty and is_cache_fresh(cached_payload, US_DAILY_CACHE_TTL_SECONDS):
        return cached_df

    try:
        frame = fetch_with_retries(lambda: ak.stock_us_daily(symbol=symbol, adjust=""), attempts=2, sleep_seconds=1.0)
        if isinstance(frame, pd.DataFrame) and not frame.empty:
            normalized = frame.copy()
            normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce").dt.strftime("%Y-%m-%d")
            for column in ["open", "high", "low", "close", "volume"]:
                if column in normalized.columns:
                    normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
            write_frame_cache(cache_path, normalized.tail(40), {"symbol": symbol})
            return normalized
    except Exception as exc:
        print(f"Warning: failed to fetch US daily data for {symbol}: {exc}")

    return cached_df


def normalize_news_rows(frame: pd.DataFrame, limit: int = 3) -> list[NewsInsightItem]:
    if frame.empty:
        return []

    items: list[NewsInsightItem] = []
    for _, row in frame.head(limit).iterrows():
        keyword = normalize_label(row.get("关键词", ""))
        items.append(
            NewsInsightItem(
                title=normalize_text_block(row.get("新闻标题", "")),
                publishTime=format_date_value(row.get("发布时间", "")),
                source=normalize_text_block(row.get("文章来源", "")),
                url=normalize_website_url(row.get("新闻链接", "")),
                excerpt=truncate_text(row.get("新闻内容", ""), 120),
                matchedKeywords=[keyword] if keyword else [],
            )
        )
    return items


def fetch_us_news_items(symbol: str, limit: int = 3) -> list[NewsInsightItem]:
    cache_path = us_news_cache_path(symbol)
    cached_df, cached_payload = load_frame_cache(cache_path)
    if not cached_df.empty and is_cache_fresh(cached_payload, US_DAILY_CACHE_TTL_SECONDS):
        return normalize_news_rows(cached_df, limit)

    try:
        frame = fetch_with_retries(lambda: ak.stock_news_em(symbol=symbol), attempts=2, sleep_seconds=1.0)
        if isinstance(frame, pd.DataFrame) and not frame.empty:
            write_frame_cache(cache_path, frame.head(20), {"symbol": symbol})
            return normalize_news_rows(frame, limit)
    except Exception as exc:
        print(f"Warning: failed to fetch US/news items for {symbol}: {exc}")

    return normalize_news_rows(cached_df, limit)


def build_us_focus_item(definition: dict[str, str]) -> UsFocusItem:
    symbol = definition.get("symbol", "")
    news_symbol = definition.get("newsSymbol", "") or symbol
    news_items = fetch_us_news_items(news_symbol, limit=3)

    if symbol:
        daily_frame = fetch_us_daily_frame(symbol)
        if len(daily_frame.index) >= 2:
            latest = daily_frame.iloc[-1]
            previous = daily_frame.iloc[-2]
            close = normalize_float(latest.get("close"))
            prev_close = normalize_float(previous.get("close"))
            change_pct = round(((close - prev_close) / prev_close * 100), 2) if prev_close else 0.0
            summary_parts = [
                f"上一交易日收于 {close:.2f}",
                f"涨跌幅 {change_pct:+.2f}%",
            ]
            if news_items:
                summary_parts.append(news_items[0].title)
            return UsFocusItem(
                key=definition.get("key", symbol),
                name=definition.get("name", symbol),
                symbol=symbol,
                category=definition.get("category", ""),
                lastTradeDate=str(latest.get("date", "")),
                close=close,
                prevClose=prev_close,
                changePct=change_pct,
                high=normalize_float(latest.get("high")),
                low=normalize_float(latest.get("low")),
                volume=normalize_float(latest.get("volume")),
                tone=tone_from_change(change_pct),
                summary="；".join(part for part in summary_parts if part),
                news=news_items,
            )

    summary = news_items[0].title if news_items else "暂无最新新闻"
    return UsFocusItem(
        key=definition.get("key", news_symbol or "news"),
        name=definition.get("name", news_symbol or "新闻"),
        symbol=symbol,
        category=definition.get("category", ""),
        lastTradeDate=news_items[0].publishTime[:10] if news_items and news_items[0].publishTime else "",
        close=0.0,
        prevClose=0.0,
        changePct=0.0,
        high=0.0,
        low=0.0,
        volume=0.0,
        tone="neutral",
        summary=summary,
        news=news_items,
    )


def build_us_market_pulse() -> UsMarketPulse:
    items = [build_us_focus_item(definition) for definition in US_FOCUS_DEFINITIONS]
    priced_items = [item for item in items if item.symbol and item.lastTradeDate]
    if not priced_items:
        return default_us_market_pulse()

    up_count = sum(1 for item in priced_items if item.changePct >= 0)
    down_count = len(priced_items) - up_count
    leader = max(priced_items, key=lambda item: item.changePct)
    laggard = min(priced_items, key=lambda item: item.changePct)
    trade_date = max((item.lastTradeDate for item in priced_items if item.lastTradeDate), default="")
    summary_parts = [
        f"隔夜七姐妹 {up_count} 涨 {down_count} 跌",
        f"领涨 {leader.name} {leader.changePct:+.2f}%",
        f"领跌 {laggard.name} {laggard.changePct:+.2f}%",
    ]
    openai_item = next((item for item in items if item.key == "OPENAI"), None)
    if openai_item and openai_item.summary:
        summary_parts.append(f"OpenAI：{openai_item.summary}")

    return UsMarketPulse(
        updatedAt=datetime.now().strftime("%Y-%m-%d %H:%M"),
        tradeDate=trade_date,
        summary="；".join(summary_parts),
        items=items,
    )


def build_stock_theme_summary(hot_boards: list[ThemeHotspot], related_etfs: list[ThemeHotspot]) -> str:
    if hot_boards:
        board_names = "、".join(item.name for item in hot_boards[:2])
        leader_parts = [
            f"{item.name} 龙头 {item.leaderName}{item.leaderChangePct:+.2f}%"
            for item in hot_boards[:2]
            if item.leaderName
        ]
        etf_part = ""
        if related_etfs:
            etf_part = f"相关 ETF {related_etfs[0].name}{related_etfs[0].changePct:+.2f}%"
        return "；".join(part for part in [f"热点重合：{board_names}", *leader_parts, etf_part] if part)

    if related_etfs:
        return f"未命中直接热点板块，相关 ETF 关注 {related_etfs[0].name}{related_etfs[0].changePct:+.2f}%"

    return "当前未捕捉到与该股直接重合的热点板块"


def build_cluster_hotspot(name: str, board_type: str, stocks: list[WatchStock], match_reason: str) -> ThemeHotspot:
    leader = max(
        stocks,
        key=lambda item: (
            item.changePct,
            item.selectionScore.total,
            item.volumeRatio,
        ),
    )
    rise_count = sum(1 for item in stocks if item.changePct >= 0)
    fall_count = len(stocks) - rise_count
    avg_change = round(sum(item.changePct for item in stocks) / len(stocks), 2) if stocks else 0.0
    return ThemeHotspot(
        boardType=board_type,
        name=name,
        code="",
        rank=0,
        changePct=avg_change,
        riseCount=rise_count,
        fallCount=fall_count,
        leaderName=leader.name,
        leaderCode=leader.symbol,
        leaderChangePct=round(leader.changePct, 2),
        matchReason=match_reason,
    )


def build_watchlist_cluster_hotspots(stocks: list[WatchStock]) -> tuple[list[ThemeHotspot], list[ThemeHotspot], dict[str, list[str]]]:
    industry_groups: dict[str, list[WatchStock]] = {}
    concept_groups: dict[str, list[WatchStock]] = {}
    stock_concepts: dict[str, list[str]] = {}

    for stock in stocks:
        industry_name = normalize_text_block(stock.companyInsight.officialBusiness.industry or stock.sector or "自选池")
        industry_groups.setdefault(industry_name, []).append(stock)

        concepts = unique_in_order(
            extract_actionable_theme_keywords(
                stock.name,
                stock.sector,
                stock.companyInsight.officialBusiness.industry,
                stock.companyInsight.officialBusiness.mainBusiness,
                stock.companyInsight.accountingBusiness.summary,
                stock.companyInsight.newsSensitivity.summary,
            )
        )[:8]
        stock_concepts[stock.symbol] = concepts
        for concept in concepts:
            concept_groups.setdefault(concept, []).append(stock)

    industry_hotspots = [
        build_cluster_hotspot(name, "industry", members, "自选池行业联动")
        for name, members in industry_groups.items()
        if len(members) >= 1
    ]
    concept_hotspots = [
        build_cluster_hotspot(name, "concept", members, "自选池概念联动")
        for name, members in concept_groups.items()
        if len(members) >= 2
    ]

    industry_hotspots.sort(key=lambda item: (item.changePct, item.riseCount, item.leaderChangePct), reverse=True)
    concept_hotspots.sort(key=lambda item: (item.changePct, item.riseCount, item.leaderChangePct), reverse=True)

    for index, item in enumerate(industry_hotspots, start=1):
        item.rank = index
    for index, item in enumerate(concept_hotspots, start=1):
        item.rank = index

    return industry_hotspots, concept_hotspots, stock_concepts


def build_global_etf_hotspots(etf_frame: pd.DataFrame) -> list[ThemeHotspot]:
    if etf_frame.empty:
        return []

    pool = etf_frame.copy()
    if "类型" in pool.columns:
        pool = pool[~pool["类型"].astype(str).str.contains("固收|债|货币", na=False)]
    if pool.empty:
        return []

    ranked = pool.sort_values(by="增长率数值", ascending=False).head(MAX_GLOBAL_ETFS)
    hotspots = []
    for rank, (_, row) in enumerate(ranked.iterrows(), start=1):
        hotspots.append(
            ThemeHotspot(
                boardType="etf",
                name=normalize_label(row.get("基金简称", "")),
                code=str(row.get("基金代码", "")),
                rank=rank,
                changePct=round(normalize_float(row.get("增长率数值")), 2),
                riseCount=0,
                fallCount=0,
                leaderName="",
                leaderCode="",
                leaderChangePct=0.0,
                matchReason="ETF 日涨幅",
            )
        )
    return hotspots


def build_related_etf_hotspots(stock: WatchStock, hot_boards: list[ThemeHotspot], etf_frame: pd.DataFrame) -> list[ThemeHotspot]:
    if etf_frame.empty:
        return []

    eligible_etfs = etf_frame.copy()
    if "类型" in eligible_etfs.columns:
        eligible_etfs = eligible_etfs[~eligible_etfs["类型"].astype(str).str.contains("固收|债|货币|国债|地债", na=False)]
    if eligible_etfs.empty:
        return []

    search_terms = unique_in_order(
        [
            *[board.name for board in hot_boards],
            stock.companyInsight.officialBusiness.industry,
            *extract_actionable_theme_keywords(
                stock.name,
                stock.sector,
                stock.companyInsight.officialBusiness.industry,
                stock.companyInsight.officialBusiness.mainBusiness,
                stock.companyInsight.accountingBusiness.summary,
                stock.companyInsight.newsSensitivity.summary,
            ),
        ]
    )
    search_terms = [term for term in search_terms if len(term) >= 2]
    if not search_terms:
        return []

    matches: list[ThemeHotspot] = []
    for _, row in eligible_etfs.iterrows():
        etf_name = normalize_label(row.get("基金简称", ""))
        matched_term = next((term for term in search_terms if term in etf_name), "")
        if not matched_term:
            continue
        matches.append(
            ThemeHotspot(
                boardType="etf",
                name=etf_name,
                code=str(row.get("基金代码", "")),
                rank=0,
                changePct=round(normalize_float(row.get("增长率数值")), 2),
                riseCount=0,
                fallCount=0,
                leaderName="",
                leaderCode="",
                leaderChangePct=0.0,
                matchReason=f"ETF 主题匹配：{matched_term}",
            )
        )

    matches.sort(key=lambda item: item.changePct, reverse=True)
    deduped: list[ThemeHotspot] = []
    seen: set[tuple[str, str]] = set()
    for item in matches:
        key = (item.name, item.code)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:MAX_STOCK_ETFS]


def parse_legu_activity_snapshot() -> dict[str, object]:
    try:
        frame = ak.stock_market_activity_legu()
    except Exception as exc:
        raise RuntimeError(f"legu activity fetch failed: {exc}") from exc

    result: dict[str, object] = {}
    for _, row in frame.iterrows():
        item = normalize_label(row.get("item"))
        if not item:
            continue
        result[item] = row.get("value")
    return result


def build_market_breadth_summary(
    points: list[MarketBreadthPoint],
    latest: MarketBreadthPoint,
) -> tuple[str, str, str, int, int]:
    if not points:
        return "neutral", "鏆傛棤甯傚満瀹藉害鏍锋湰", "鏆傛棤涓婃定/涓嬭穼瀹舵暟鏇茬嚎", 0, 0

    net_values = [point.netAdvance for point in points]
    breadth_low = min(net_values)
    breadth_high = max(net_values)
    latest_net = latest.netAdvance
    first_net = points[0].netAdvance
    low_index = min(range(len(points)), key=lambda index: points[index].netAdvance)
    recovery = latest_net - breadth_low

    if latest_net <= -1800 and low_index == len(points) - 1:
        return (
            "negative",
            "鍐扮偣鎵╂暎",
            f"褰撳墠鍑€瀹舵暟 {latest_net:+d}锛屼笅璺屽鏁颁粛鍦ㄧ户缁墿澶э紝鍏堢瓑鍐扮偣绋冲畾銆?",
            breadth_low,
            breadth_high,
        )

    if recovery >= 900 and latest_net - first_net >= 600 and low_index <= max(len(points) - 4, 0):
        return (
            "positive",
            "鍐扮偣淇",
            f"鏃ュ唴浠庢渶浣庡噣瀹舵暟 {breadth_low:+d} 淇鑷? {latest_net:+d}锛屼笂娑ㄥ鏁板洖鍗囷紝鍙暀鎰忓啺鐐瑰弽杞満浼氥€?",
            breadth_low,
            breadth_high,
        )

    if latest_net >= 500 and latest_net - first_net >= 300:
        return (
            "positive",
            "鏅定鎵╂暎",
            f"鍑€瀹舵暟鍥炲崌鑷? {latest_net:+d}锛屼笂娑ㄥ鏁版鍦ㄦ墿鏁ｏ紝鐜鍋忓洖鏆栥€?",
            breadth_low,
            breadth_high,
        )

    if latest_net <= -800:
        return (
            "alert",
            "鍐扮偣鍖洪棿",
            f"鍑€瀹舵暟浠嶅湪 {latest_net:+d} 浣庝綅闄勮繎锛屽彲浠ュ叧娉ㄦ槸鍚﹀嚭鐜扮涓€娆℃湁鏁堝洖鍗囥€?",
            breadth_low,
            breadth_high,
        )

    return (
        "neutral",
        "鍒嗗寲闇囪崱",
        f"褰撳墠鍑€瀹舵暟 {latest_net:+d}锛屼笂涓嬪鏁扮粨鏋勪粛鍦ㄦ媺鎵紝鍏堢户缁瀵熻浆寮哄埡婵€銆?",
        breadth_low,
        breadth_high,
    )


def fetch_market_breadth_profile() -> MarketBreadthProfile:
    cached_payload = load_json_cache(MARKET_BREADTH_CACHE_PATH)
    cached_profile = market_breadth_from_dict(cached_payload.get("data", {})) if cached_payload else default_market_breadth()
    if cached_payload and is_cache_fresh(cached_payload, MARKET_BREADTH_CACHE_TTL_SECONDS) and cached_profile.trendPoints:
        return cached_profile

    snapshot_payload = load_snapshot_payload()
    snapshot_breadth = market_breadth_from_dict(
        (snapshot_payload.get("marketRadar", {}) or {}).get("marketBreadth", {})
    )

    try:
        response = requests.get(
            "https://legulegu.com/stockdata/market-activity-trend-data",
            headers=LEGU_HEADERS,
            timeout=20,
        )
        response.raise_for_status()
        raw_points = response.json()
        if not isinstance(raw_points, list) or not raw_points:
            raise RuntimeError("market breadth trend payload is empty")

        points: list[MarketBreadthPoint] = []
        for item in raw_points:
            if not isinstance(item, dict):
                continue
            trade_time = datetime.fromtimestamp(normalize_float(item.get("date")) / 1000)
            total_up = normalize_int(item.get("totalUp"), 0)
            total_down = normalize_int(item.get("totalDown"), 0)
            flat_count = normalize_int(item.get("priceStop"), 0)
            points.append(
                MarketBreadthPoint(
                    timestamp=trade_time.strftime("%H:%M"),
                    totalUp=total_up,
                    totalDown=total_down,
                    limitUp=normalize_int(item.get("limitUp"), 0),
                    limitDown=normalize_int(item.get("limitDown"), 0),
                    flatCount=flat_count,
                    netAdvance=total_up - total_down,
                )
            )

        if not points:
            raise RuntimeError("market breadth points are empty")

        points.sort(key=lambda item: item.timestamp)
        latest = points[-1]
        activity_map = parse_legu_activity_snapshot()
        activity_pct = round(normalize_float(activity_map.get("娲昏穬搴?"), 0.0), 2)
        trade_date = datetime.fromtimestamp(normalize_float(raw_points[-1].get("date")) / 1000).strftime("%Y-%m-%d")
        tone, signal_label, summary, breadth_low, breadth_high = build_market_breadth_summary(points, latest)
        advance_decline_ratio = round(latest.totalUp / max(latest.totalDown, 1), 2)

        profile = MarketBreadthProfile(
            updatedAt=datetime.now().strftime("%Y-%m-%d %H:%M"),
            tradeDate=trade_date,
            activityPct=activity_pct,
            upCount=normalize_int(activity_map.get("涓婃定"), latest.totalUp),
            downCount=normalize_int(activity_map.get("涓嬭穼"), latest.totalDown),
            flatCount=normalize_int(activity_map.get("骞崇洏"), latest.flatCount),
            limitUpCount=normalize_int(activity_map.get("娑ㄥ仠"), latest.limitUp),
            limitDownCount=normalize_int(activity_map.get("璺屽仠"), latest.limitDown),
            netAdvance=latest.netAdvance,
            advanceDeclineRatio=advance_decline_ratio,
            breadthLow=breadth_low,
            breadthHigh=breadth_high,
            tone=tone,
            signalLabel=signal_label,
            summary=summary,
            trendPoints=points,
        )
        write_json_cache(MARKET_BREADTH_CACHE_PATH, {"fetchedAt": now_iso(), "data": asdict(profile)})
        return profile
    except Exception as exc:
        print(f"Warning: failed to fetch market breadth profile: {exc}")

    if cached_profile.trendPoints:
        return cached_profile
    if snapshot_breadth.trendPoints:
        return snapshot_breadth
    return default_market_breadth()


def enrich_market_radar(stocks: list[WatchStock]) -> MarketRadar:
    industry_hotspots, concept_hotspots, stock_concepts = build_watchlist_cluster_hotspots(stocks)

    etf_frame = fetch_etf_daily_frame()
    global_etfs = build_global_etf_hotspots(etf_frame)
    hottest_boards = sorted(
        (industry_hotspots[:4] + concept_hotspots[:4]),
        key=lambda item: (item.changePct, -item.rank),
        reverse=True,
    )[:MAX_GLOBAL_BOARDS]

    for stock in stocks:
        stock_industry = normalize_text_block(stock.companyInsight.officialBusiness.industry or stock.sector)
        matched_hot_boards = [
            item for item in industry_hotspots
            if item.name == stock_industry
        ]
        matched_hot_boards.extend(
            item for item in concept_hotspots
            if item.name in stock_concepts.get(stock.symbol, [])
        )
        matched_hot_boards = sorted(matched_hot_boards, key=lambda item: (item.changePct, item.riseCount, item.leaderChangePct), reverse=True)[:MAX_STOCK_HOT_BOARDS]
        industry_name = next((item.name for item in matched_hot_boards if item.boardType == "industry"), "")
        if not industry_name:
            industry_name = normalize_text_block(stock.companyInsight.officialBusiness.industry or stock.sector)
        concepts = unique_in_order([item.name for item in matched_hot_boards if item.boardType == "concept"]) or stock_concepts.get(stock.symbol, [])
        matched_keywords = unique_in_order(
            extract_actionable_theme_keywords(
                stock.name,
                stock.sector,
                industry_name,
                stock.companyInsight.officialBusiness.mainBusiness,
                stock.companyInsight.accountingBusiness.summary,
                " ".join(concepts),
            )
        )[:8]
        related_etfs = build_related_etf_hotspots(stock, matched_hot_boards, etf_frame)
        stock.themeLinkage = StockThemeLinkage(
            updatedAt=datetime.now().strftime("%Y-%m-%d %H:%M"),
            industry=industry_name,
            concepts=concepts[:6],
            matchedKeywords=matched_keywords,
            hotBoards=matched_hot_boards,
            relatedEtfs=related_etfs,
            summary=build_stock_theme_summary(matched_hot_boards, related_etfs),
        )

    return MarketRadar(
        updatedAt=datetime.now().strftime("%Y-%m-%d %H:%M"),
        hottestBoards=hottest_boards,
        hottestEtfs=global_etfs,
        usMarketPulse=build_us_market_pulse(),
        marketBreadth=fetch_market_breadth_profile(),
    )


def fetch_market_cap_yi(symbol: str, current_price: float, fallback_market_cap_yi: float) -> float:
    cached_cap, cached_payload = load_cap_cache(symbol)
    if cached_cap is not None and is_cache_fresh(cached_payload, CAP_CACHE_TTL_SECONDS):
        return cached_cap

    market_prefix = "sh" if symbol.startswith(("600", "601", "603", "605", "688")) else "sz"
    alt_symbol = f"{market_prefix}{symbol}"

    try:
        daily_df = ak.stock_zh_a_daily(symbol=alt_symbol, adjust="qfq")
        if not daily_df.empty and "outstanding_share" in daily_df.columns:
            latest = daily_df.dropna(subset=["outstanding_share"]).tail(1)
            if not latest.empty:
                outstanding_share = float(latest.iloc[-1]["outstanding_share"])
                market_cap_yi = (current_price * outstanding_share) / 100000000
                write_cap_cache(symbol, market_cap_yi)
                return round(market_cap_yi, 2)
    except Exception:
        pass

    if cached_cap is not None:
        return cached_cap
    return fallback_market_cap_yi


def fetch_hist_with_baostock(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    bs_symbol = baostock_symbol(symbol)
    if not bs_symbol:
        return pd.DataFrame()

    start_label = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
    end_label = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"
    last_error: Exception | None = None

    for attempt in range(1, 4):
        try:
            ensure_baostock_login()
            result = bs.query_history_k_data_plus(
                bs_symbol,
                BAOSTOCK_DAILY_FIELDS,
                start_date=start_label,
                end_date=end_label,
                frequency="d",
                adjustflag="2",
            )
            if result.error_code != "0":
                raise RuntimeError(f"baostock history query failed: {result.error_code} {result.error_msg}")

            rows: list[list[str]] = []
            while result.error_code == "0" and result.next():
                rows.append(result.get_row_data())

            if not rows:
                return pd.DataFrame()

            return pd.DataFrame(rows, columns=result.fields)
        except Exception as exc:
            last_error = exc
            logout_baostock()
            if attempt < 3:
                time.sleep(0.5 * attempt)

    raise last_error or RuntimeError("baostock history query failed")


def fetch_chip_hist_with_baostock(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    bs_symbol = baostock_symbol(symbol)
    if not bs_symbol:
        return pd.DataFrame()

    start_label = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
    end_label = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"
    last_error: Exception | None = None

    for attempt in range(1, 4):
        try:
            ensure_baostock_login()
            result = bs.query_history_k_data_plus(
                bs_symbol,
                BAOSTOCK_CHIP_FIELDS,
                start_date=start_label,
                end_date=end_label,
                frequency="d",
                adjustflag="3",
            )
            if result.error_code != "0":
                raise RuntimeError(f"baostock chip query failed: {result.error_code} {result.error_msg}")

            rows: list[list[str]] = []
            while result.error_code == "0" and result.next():
                rows.append(result.get_row_data())

            if not rows:
                return pd.DataFrame()

            frame = pd.DataFrame(rows, columns=result.fields)
            numeric_columns = ["close", "preclose", "volume", "amount", "turn"]
            for column in numeric_columns:
                if column in frame.columns:
                    frame[column] = pd.to_numeric(frame[column], errors="coerce")
            return frame
        except Exception as exc:
            last_error = exc
            logout_baostock()
            if attempt < 3:
                time.sleep(0.5 * attempt)

    raise last_error or RuntimeError("baostock chip query failed")


def fetch_hist(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    cached_df, cached_payload = load_hist_cache(symbol)
    if not cached_df.empty and is_hist_cache_fresh(cached_payload, start_date, end_date):
        return cached_df

    hist_df = pd.DataFrame()
    market_prefix = "sh" if symbol.startswith(("600", "601", "603", "605", "688")) else "sz"
    alt_symbol = f"{market_prefix}{symbol}"

    fetchers = [
        ("baostock", lambda: fetch_hist_with_baostock(symbol, start_date, end_date)),
        ("stock_zh_a_daily", lambda: ak.stock_zh_a_daily(
            symbol=alt_symbol,
            adjust="qfq",
        )),
        ("stock_zh_a_hist_tx", lambda: ak.stock_zh_a_hist_tx(
            symbol=alt_symbol,
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
        )),
        ("stock_zh_a_hist", lambda: ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
        )),
    ]

    last_error: Exception | None = None
    used_source = ""

    for source_name, fetcher in fetchers:
        for attempt in range(1, 3):
            try:
                candidate = fetcher()
                if not candidate.empty:
                    hist_df = candidate.copy()
                    used_source = source_name
                    break
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(0.6 * attempt)
        if not hist_df.empty:
            break

    if hist_df.empty:
        if last_error is not None:
            print(f"Warning: failed to fetch history for {symbol}: {last_error}")
        return cached_df

    normalized = hist_df.copy()
    column_map = {}
    if "date" in normalized.columns and "日期" not in normalized.columns:
        column_map["date"] = "日期"
    if "open" in normalized.columns and "开盘" not in normalized.columns:
        column_map["open"] = "开盘"
    if "close" in normalized.columns and C_CLOSE not in normalized.columns:
        column_map["close"] = C_CLOSE
    if "high" in normalized.columns and C_HIGH not in normalized.columns:
        column_map["high"] = C_HIGH
    if "low" in normalized.columns and C_LOW not in normalized.columns:
        column_map["low"] = C_LOW
    if "volume" in normalized.columns and C_VOLUME not in normalized.columns:
        column_map["volume"] = C_VOLUME
    if "amount" in normalized.columns and "volume" not in normalized.columns and C_VOLUME not in normalized.columns:
        column_map["amount"] = C_VOLUME
    if "pctChg" in normalized.columns and C_CHANGE not in normalized.columns:
        column_map["pctChg"] = C_CHANGE
    if column_map:
        normalized = normalized.rename(columns=column_map)

    if "date" not in normalized.columns and "日期" in normalized.columns:
        normalized["date"] = normalized["日期"].astype(str)
    elif "日期" not in normalized.columns and "date" in normalized.columns:
        normalized["日期"] = normalized["date"].astype(str)

    normalized[C_CLOSE] = pd.to_numeric(normalized.get(C_CLOSE), errors="coerce")
    if "开盘" in normalized.columns:
        normalized["开盘"] = pd.to_numeric(normalized["开盘"], errors="coerce")
    if C_HIGH in normalized.columns:
        normalized[C_HIGH] = pd.to_numeric(normalized[C_HIGH], errors="coerce")
    if C_LOW in normalized.columns:
        normalized[C_LOW] = pd.to_numeric(normalized[C_LOW], errors="coerce")
    if C_VOLUME in normalized.columns:
        normalized[C_VOLUME] = pd.to_numeric(normalized[C_VOLUME], errors="coerce")
    else:
        normalized[C_VOLUME] = 0

    if C_CHANGE in normalized.columns:
        normalized[C_CHANGE] = pd.to_numeric(normalized[C_CHANGE], errors="coerce")
    else:
        normalized[C_CHANGE] = normalized[C_CLOSE].pct_change() * 100

    if used_source == "stock_zh_a_daily" and "date" in normalized.columns:
        normalized["date"] = normalized["date"].astype(str)
        normalized = normalized[
            (normalized["date"] >= f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}") &
            (normalized["date"] <= f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}")
        ]

    normalized = normalized.dropna(subset=[C_CLOSE])

    if normalized.empty:
        return cached_df

    write_hist_cache(symbol, start_date, end_date, normalized)
    return normalized


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def is_growth_board(symbol: str) -> bool:
    return symbol.startswith(("300", "301", "688"))


def price_limit_ratio(symbol: str) -> float:
    if symbol.startswith(("300", "301", "688")):
        return 0.20
    if symbol.startswith(("430", "830", "831", "832", "833", "835", "836", "837", "838", "839", "870", "871", "872", "873", "874", "875", "876", "877", "878", "879")):
        return 0.30
    return 0.10


def is_limit_up_close(symbol: str, row: pd.Series, close_value: float, high_value: float) -> bool:
    limit_ratio = price_limit_ratio(symbol)
    pct_value = to_float(row.get(C_CHANGE, row.get("pctChg", 0.0)), 0.0)
    if pct_value < limit_ratio * 100 - 0.35:
        return False
    return abs(close_value - high_value) <= max(0.01, close_value * 0.0012)


def resolve_amplitude_template(symbol: str, market_cap_yi: float) -> tuple[str, str, float, list[float]]:
    board_type = "创业成长板" if is_growth_board(symbol) else "沪深主板"

    if board_type == "创业成长板":
        if market_cap_yi >= 1000:
            return board_type, "千亿以上", 40.0, [0.0, 0.8, 1.5, 3.0, 5.0, 8.0, 40.0]
        if market_cap_yi >= 500:
            return board_type, "500-1000亿", 40.0, [0.0, 1.0, 2.0, 4.0, 6.0, 10.0, 40.0]
        if market_cap_yi >= 100:
            return board_type, "100-500亿", 40.0, [0.0, 1.0, 5.0, 10.0, 15.0, 25.0, 40.0]
        return board_type, "100亿以下", 40.0, [0.0, 2.0, 5.0, 10.0, 18.0, 28.0, 40.0]

    if market_cap_yi >= 1000:
        return board_type, "千亿以上", 20.0, [0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 20.0]
    if market_cap_yi >= 500:
        return board_type, "500-1000亿", 20.0, [0.0, 0.8, 1.5, 3.0, 5.0, 8.0, 20.0]
    if market_cap_yi >= 100:
        return board_type, "100-500亿", 20.0, [0.0, 1.0, 3.0, 5.0, 10.0, 15.0, 20.0]
    return board_type, "100亿以下", 20.0, [0.0, 1.5, 3.0, 5.0, 8.0, 12.0, 20.0]


def build_price_distribution(close_series: list[float], current_price: float) -> PriceDistributionProfile:
    if not close_series:
        close_series = [current_price] if current_price else [0.0]

    year_low = round(min(close_series), 2)
    year_high = round(max(close_series), 2)
    sample_size = len(close_series)

    if year_high <= year_low:
        stable_band = 2
        bands = []
        for index in range(6):
            close_count = sample_size if index == stable_band else 0
            bands.append(
                PriceDistributionBand(
                    index=index,
                    lower=year_low,
                    upper=year_high,
                    closeCount=close_count,
                    ratio=round(close_count / sample_size if sample_size else 0.0, 4),
                    rangeLabel=f"{year_low:.2f}-{year_high:.2f}",
                )
            )

        return PriceDistributionProfile(
            yearHigh=year_high,
            yearLow=year_low,
            sampleSize=sample_size,
            currentBand=stable_band,
            dominantBand=stable_band,
            currentPositionPct=0.5,
            bands=bands,
        )

    band_width = (year_high - year_low) / 6
    counts = [0] * 6

    def resolve_band(price: float) -> int:
        if band_width <= 0:
            return 2
        raw_index = int((price - year_low) / band_width)
        return max(0, min(5, raw_index))

    for close_price in close_series:
        counts[resolve_band(close_price)] += 1

    bounded_price = clamp(current_price, year_low, year_high)
    current_band = resolve_band(bounded_price)
    dominant_band = max(range(6), key=lambda index: counts[index])
    current_position_pct = round((bounded_price - year_low) / (year_high - year_low), 4)

    bands: list[PriceDistributionBand] = []
    for index in range(6):
        lower = year_low + index * band_width
        upper = year_high if index == 5 else year_low + (index + 1) * band_width
        close_count = counts[index]
        bands.append(
            PriceDistributionBand(
                index=index,
                lower=round(lower, 2),
                upper=round(upper, 2),
                closeCount=close_count,
                ratio=round(close_count / sample_size if sample_size else 0.0, 4),
                rangeLabel=f"{lower:.2f}-{upper:.2f}",
            )
        )

    return PriceDistributionProfile(
        yearHigh=year_high,
        yearLow=year_low,
        sampleSize=sample_size,
        currentBand=current_band,
        dominantBand=dominant_band,
        currentPositionPct=current_position_pct,
        bands=bands,
    )


def build_macd_indicator(close_series: list[float]) -> MacdIndicator:
    if len(close_series) < 2:
        return default_technicals().macd

    close_frame = pd.Series(close_series, dtype="float64")
    ema10 = close_frame.ewm(span=10, adjust=False).mean()
    ema200 = close_frame.ewm(span=200, adjust=False).mean()
    dif_series = ema10 - ema200
    dea_series = dif_series.ewm(span=7, adjust=False).mean()
    histogram_series = (dif_series - dea_series) * 2

    latest_dif = float(dif_series.iloc[-1])
    latest_dea = float(dea_series.iloc[-1])
    latest_histogram = float(histogram_series.iloc[-1])
    prev_dif = float(dif_series.iloc[-2])
    prev_dea = float(dea_series.iloc[-2])

    if prev_dif < prev_dea and latest_dif >= latest_dea:
        signal_label = "MACD 金叉"
        bias_label = "短中期转强，关注跟随"
        tone = "positive"
    elif prev_dif > prev_dea and latest_dif <= latest_dea:
        signal_label = "MACD 死叉"
        bias_label = "趋势转弱，谨慎追高"
        tone = "negative"
    elif latest_dif >= latest_dea and latest_dif >= 0:
        signal_label = "长周期多头"
        bias_label = "站上长周期均线"
        tone = "positive"
    elif latest_dif >= latest_dea:
        signal_label = "长周期修复"
        bias_label = "空头背景下修复观察"
        tone = "neutral"
    elif latest_dif < latest_dea and latest_dif <= 0:
        signal_label = "长周期空头"
        bias_label = "远离 200 日均线"
        tone = "negative"
    else:
        signal_label = "长周期回落"
        bias_label = "多头回踩，防止走弱"
        tone = "alert"

    return MacdIndicator(
        dif=round(latest_dif, 3),
        dea=round(latest_dea, 3),
        histogram=round(latest_histogram, 3),
        signalLabel=signal_label,
        biasLabel=bias_label,
        tone=tone,
    )


def build_rsi_indicator(close_series: list[float], period: int = 9) -> RsiIndicator:
    if len(close_series) <= period:
        return default_technicals().rsi14

    close_frame = pd.Series(close_series, dtype="float64")
    delta = close_frame.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    average_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    average_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = average_gain / average_loss.replace(0, 1e-9)
    rsi_series = 100 - (100 / (1 + rs))
    normalized_rsi = rsi_series.fillna(50)
    latest_rsi = float(normalized_rsi.iloc[-1])
    prev_rsi = float(normalized_rsi.iloc[-2]) if len(normalized_rsi) > 1 else latest_rsi

    if latest_rsi >= 80:
        signal_label = "RSI 高风险"
        bias_label = "建议卖出或减仓"
        tone = "alert"
    elif prev_rsi < 50 <= latest_rsi:
        signal_label = "RSI 上穿50"
        bias_label = "重点关注买入"
        tone = "positive"
    elif latest_rsi >= 50:
        signal_label = "RSI 强势区"
        bias_label = "多头主导，持有观察"
        tone = "positive"
    elif prev_rsi >= 50 > latest_rsi:
        signal_label = "RSI 跌破50"
        bias_label = "强势失守，转弱观察"
        tone = "negative"
    elif latest_rsi >= 30:
        signal_label = "RSI 观察区"
        bias_label = "等待重新站上50"
        tone = "neutral"
    else:
        signal_label = "RSI 弱势区"
        bias_label = "低于30，先等修复"
        tone = "negative"

    return RsiIndicator(
        period=period,
        value=round(latest_rsi, 2),
        signalLabel=signal_label,
        biasLabel=bias_label,
        tone=tone,
    )


def build_technical_indicators(close_series: list[float]) -> TechnicalIndicators:
    if not close_series:
        return default_technicals()

    return TechnicalIndicators(
        macd=build_macd_indicator(close_series),
        rsi14=build_rsi_indicator(close_series),
    )


def build_bollinger_profile(hist_df: pd.DataFrame, period: int = 30, std_multiplier: float = 2.0) -> BollingerProfile:
    if hist_df.empty or C_CLOSE not in hist_df.columns:
        return default_bollinger()

    close_series = pd.to_numeric(hist_df[C_CLOSE], errors="coerce")
    rolling_mean = close_series.rolling(window=period).mean()
    rolling_std = close_series.rolling(window=period).std(ddof=0)
    frame = pd.DataFrame({
        "date": hist_df.get("日期", hist_df.index),
        "middle": rolling_mean,
        "upper": rolling_mean + rolling_std * std_multiplier,
        "lower": rolling_mean - rolling_std * std_multiplier,
    }).dropna().tail(12)

    points = [
        BollingerPoint(
            date=str(row["date"])[:10],
            middle=round(float(row["middle"]), 2),
            upper=round(float(row["upper"]), 2),
            lower=round(float(row["lower"]), 2),
        )
        for _, row in frame.iterrows()
    ]
    return BollingerProfile(period=period, stdMultiplier=std_multiplier, points=points)


def build_recent_candles(symbol: str, hist_df: pd.DataFrame) -> list[CandlePoint]:
    candles: list[CandlePoint] = []
    if hist_df.empty:
        return candles

    for _, row in hist_df.iterrows():
        close_value = round(to_float(row.get(C_CLOSE, row.get("close", 0.0)), 0.0), 2)
        open_value = round(to_float(row.get("开盘", row.get("open", close_value)), close_value), 2)
        high_value = round(to_float(row.get(C_HIGH, row.get("high", close_value)), close_value), 2)
        low_value = round(to_float(row.get(C_LOW, row.get("low", close_value)), close_value), 2)
        normalized_high = max(high_value, open_value, close_value)
        normalized_low = min(low_value, open_value, close_value)
        candles.append(
            CandlePoint(
                date=normalize_text_block(row.get("日期", row.get("date", "")))[:10],
                open=open_value,
                high=normalized_high,
                low=normalized_low,
                close=close_value,
                isLimitUpClose=is_limit_up_close(symbol, row, close_value, normalized_high),
            )
        )

    return candles


def build_limit_up_signal_profile(symbol: str, hist_df: pd.DataFrame, current_price: float) -> LimitUpSignalProfile:
    if hist_df.empty:
        return default_limit_up_signal()

    recent_frame = hist_df.tail(10).copy()
    recent_count_10 = 0
    candidates: list[LimitUpSignalProfile] = []

    for position, (_, row) in enumerate(recent_frame.iterrows()):
        close_value = round(to_float(row.get(C_CLOSE, row.get("close", 0.0)), 0.0), 2)
        open_value = round(to_float(row.get("开盘", row.get("open", close_value)), close_value), 2)
        high_value = round(to_float(row.get(C_HIGH, row.get("high", close_value)), close_value), 2)
        normalized_high = max(high_value, open_value, close_value)
        is_limit_up = is_limit_up_close(symbol, row, close_value, normalized_high)
        if not is_limit_up:
            continue

        if position >= len(recent_frame) - 10:
            recent_count_10 += 1

        future = recent_frame.iloc[position + 1 :]
        if future.empty:
            continue
        future_closes = pd.to_numeric(future[C_CLOSE], errors="coerce").dropna()
        if future_closes.empty or float(future_closes.min()) < open_value:
            continue

        anchor_date = normalize_text_block(row.get("日期", row.get("date", "")))[:10]
        hold_days = len(future)
        current_bias_pct = ((current_price / open_value) - 1) * 100 if open_value else 0.0
        candidates.append(
            LimitUpSignalProfile(
                recentLimitUpCount10=recent_count_10,
                isHoldingAboveOpen=True,
                anchorDate=anchor_date,
                anchorOpen=open_value,
                anchorClose=close_value,
                holdDays=hold_days,
                currentBiasPct=round(current_bias_pct, 2),
                tone="alert" if hold_days >= 3 else "positive",
                summary=(
                    f"自 {anchor_date} 涨停以来，后续收盘始终未跌破当日开盘价 {open_value:.2f}。"
                    f"已保持 {hold_days} 个交易日，当前仍高于该位置 {current_bias_pct:+.1f}%。"
                ),
            )
        )

    if candidates:
        strongest = max(candidates, key=lambda item: (item.holdDays, item.currentBiasPct, item.anchorDate))
        strongest.recentLimitUpCount10 = recent_count_10
        return strongest

    signal = default_limit_up_signal()
    signal.recentLimitUpCount10 = recent_count_10
    if recent_count_10 > 0:
        signal.summary = f"近 10 日出现 {recent_count_10} 次涨停，但守开条件未成立。"
    return signal


def bucket_price(value: float, bucket_size: float) -> float:
    if bucket_size <= 0:
        return round(value, 2)
    return round(round(value / bucket_size) * bucket_size, 2)


def weighted_price_quantile(bands: list[tuple[float, float]], quantile: float) -> float:
    if not bands:
        return 0.0

    target = max(0.0, min(1.0, quantile))
    cumulative = 0.0
    for price, ratio in bands:
        cumulative += ratio
        if cumulative >= target:
            return round(price, 2)
    return round(bands[-1][0], 2)


def turnover_weighted_cost_line(frame: pd.DataFrame, window: int | None = None) -> float:
    scoped = frame.tail(window) if window else frame
    scoped = scoped.dropna(subset=["adj_avg_price", "turnover"])
    if scoped.empty:
        return 0.0

    weights = scoped["turnover"].clip(lower=0.0001)
    total_weight = float(weights.sum())
    if total_weight <= 0:
        return round(float(scoped["adj_avg_price"].mean()), 2)

    return round(float((scoped["adj_avg_price"] * weights).sum() / total_weight), 2)


def find_significant_chip_peaks(
    bands: list[tuple[float, float]],
    dominant_ratio: float,
) -> list[tuple[int, float, float]]:
    if not bands:
        return []

    threshold = max(0.02, dominant_ratio * 0.45)
    peaks: list[tuple[int, float, float]] = []
    for index, (price, ratio) in enumerate(bands):
        left_ratio = bands[index - 1][1] if index > 0 else -1.0
        right_ratio = bands[index + 1][1] if index + 1 < len(bands) else -1.0
        if ratio >= left_ratio and ratio >= right_ratio and ratio >= threshold:
            peaks.append((index, price, ratio))

    if peaks:
        return peaks

    dominant_index = max(range(len(bands)), key=lambda item: bands[item][1])
    dominant_price, dominant_peak_ratio = bands[dominant_index]
    return [(dominant_index, dominant_price, dominant_peak_ratio)]


def resolve_main_cost_zone(
    bands: list[tuple[float, float]],
    dominant_index: int,
    dominant_ratio: float,
    dominant_price: float,
) -> tuple[float, float, float]:
    if not bands:
        return 0.0, 0.0, 0.0

    threshold = max(0.015, dominant_ratio * 0.35)
    start = dominant_index
    end = dominant_index

    while start > 0 and bands[start - 1][1] >= threshold:
        start -= 1
    while end + 1 < len(bands) and bands[end + 1][1] >= threshold:
        end += 1

    zone_low = round(bands[start][0], 2)
    zone_high = round(bands[end][0], 2)
    zone_width_pct = round((((zone_high - zone_low) / dominant_price) * 100) if dominant_price else 0.0, 2)
    return zone_low, zone_high, zone_width_pct


def resolve_chip_shape(
    peaks: list[tuple[int, float, float]],
    low_90: float,
    high_90: float,
    zone_low: float,
    zone_high: float,
    zone_width_pct: float,
    current_price: float,
    dominant_price: float,
    winner_ratio: float,
    bucket_size: float,
) -> tuple[str, str, str, str]:
    span = max(high_90 - low_90, bucket_size)
    zone_mid = (zone_low + zone_high) / 2 if zone_high or zone_low else dominant_price
    zone_position = ((zone_mid - low_90) / span) if span else 0.5
    peak_span = abs(peaks[-1][1] - peaks[0][1]) if len(peaks) >= 2 else 0.0

    if len(peaks) >= 2 and peak_span >= max(bucket_size * 6, dominant_price * 0.08):
        return "双峰结构", "双峰博弈", "上下成本峰同时存在，先等方向选择", "neutral"
    if current_price >= zone_high * 1.08 and winner_ratio >= 0.68:
        return "向上发散", "拉升展开", "已经脱离主力成本区，趋势在走，但不宜追高", "positive"
    if current_price <= zone_low * 0.92 and winner_ratio <= 0.35:
        return "向下发散", "下行出清", "价格落在主力成本区下方，筹码承压明显", "negative"
    if zone_width_pct <= 12 and zone_position <= 0.35:
        return "低位密集", "吸筹蓄势", "低位换手较充分，等待放量确认", "positive"
    if zone_width_pct <= 12 and zone_position >= 0.65:
        return "高位密集", "高位博弈", "高位筹码堆积，优先防派发风险", "alert"
    if zone_width_pct <= 18:
        return "筹码密集", "震荡换手", "筹码集中但方向未完全展开，继续观察", "neutral"
    return "宽幅发散", "筹码分散", "持仓成本差异较大，控盘轮廓不够清晰", "neutral"


def build_chip_control_evidence(
    normalized: pd.DataFrame,
    current_price: float,
    winner_ratio: float,
    zone_low: float,
    zone_high: float,
    zone_width_pct: float,
    zone_position: float,
) -> list[ChipControlEvidence]:
    if normalized.empty:
        return []

    latest_turnover = float(normalized["turnover"].iloc[-1])
    recent_turnover = float(normalized["turnover"].tail(3).mean())
    recent_min_close = float(normalized["close"].tail(6).min())
    cyc5 = turnover_weighted_cost_line(normalized, 5)
    cyc13 = turnover_weighted_cost_line(normalized, 13)
    cyc34 = turnover_weighted_cost_line(normalized, 34)

    if zone_low <= current_price <= zone_high:
        zone_tone = "positive"
        zone_value = "处于成本区内"
        zone_summary = "当前价格仍在主力成本区内部，博弈重心没有明显失控。"
    elif current_price > zone_high:
        premium_pct = ((current_price / zone_high) - 1) * 100 if zone_high else 0.0
        zone_tone = "alert" if premium_pct >= 12 else "neutral"
        zone_value = f"高于成本区 {premium_pct:.1f}%"
        zone_summary = "价格已运行到主力成本区上方，越远越要防追高。"
    else:
        discount_pct = (1 - (current_price / zone_low)) * 100 if zone_low else 0.0
        zone_tone = "negative" if discount_pct >= 5 else "neutral"
        zone_value = f"低于成本区 {discount_pct:.1f}%"
        zone_summary = "价格回到主力成本区下方，说明上方筹码存在明显压力。"

    if winner_ratio >= 0.9 and latest_turnover <= 0.03:
        winner_tone = "positive"
        winner_summary = "满足 90 比 3，获利盘高而换手低，筹码锁定较好。"
    elif winner_ratio >= 0.75 and latest_turnover <= 0.05:
        winner_tone = "neutral"
        winner_summary = "接近 90 比 3，说明持股者总体占优，但锁定程度还不够强。"
    else:
        winner_tone = "negative"
        winner_summary = "未达到 90 比 3，当前筹码锁定性一般。"

    breakout_ready = current_price > zone_high * 1.01 and recent_min_close <= zone_high * 1.01
    if breakout_ready and recent_turnover <= 0.03:
        breakout_tone = "positive"
        breakout_value = f"近 3 日换手 {recent_turnover * 100:.2f}%"
        breakout_summary = "股价刚脱离密集区且换手偏低，接近无量上穿密集区。"
    elif breakout_ready and recent_turnover >= 0.06:
        breakout_tone = "alert"
        breakout_value = f"近 3 日换手 {recent_turnover * 100:.2f}%"
        breakout_summary = "虽然价格站上密集区，但换手偏大，更像放量冲关，追高要谨慎。"
    else:
        breakout_tone = "neutral"
        breakout_value = f"近 3 日换手 {recent_turnover * 100:.2f}%"
        breakout_summary = "暂未出现典型的无量上穿密集区结构。"

    low_lock_ready = zone_position <= 0.35 and zone_width_pct <= 12 and current_price <= zone_high * 1.05 and winner_ratio >= 0.75
    if low_lock_ready:
        lock_tone = "positive"
        lock_value = f"区宽 {zone_width_pct:.1f}%"
        lock_summary = "主力成本区位于低位且分布较窄，接近低位锁定。"
    elif zone_position >= 0.65 and zone_width_pct <= 12:
        lock_tone = "alert"
        lock_value = f"区宽 {zone_width_pct:.1f}%"
        lock_summary = "筹码虽然集中，但位置偏高，更像高位锁定博弈。"
    else:
        lock_tone = "neutral"
        lock_value = f"区宽 {zone_width_pct:.1f}%"
        lock_summary = "锁定结构不典型，继续观察筹码是否进一步收敛。"

    if cyc5 > cyc13 > cyc34 and cyc34 > 0 and ((cyc5 / cyc34) - 1) >= 0.05:
        cost_tone = "positive"
        cost_value = "成本均线发散"
        cost_summary = f"CYC5/13/34 约为 {cyc5:.2f}/{cyc13:.2f}/{cyc34:.2f}，短中期成本抬升明显。"
    elif cyc5 < cyc13 < cyc34 and cyc5 > 0:
        cost_tone = "negative"
        cost_value = "成本均线走弱"
        cost_summary = f"CYC5/13/34 约为 {cyc5:.2f}/{cyc13:.2f}/{cyc34:.2f}，成本结构偏空。"
    else:
        cost_tone = "neutral"
        cost_value = "成本均线缠绕"
        cost_summary = f"CYC5/13/34 约为 {cyc5:.2f}/{cyc13:.2f}/{cyc34:.2f}，主力方向仍需确认。"

    return [
        ChipControlEvidence("cost_zone", "成本区位置", zone_value, zone_tone, zone_summary),
        ChipControlEvidence("winner_lock", "90比3", f"获利 {winner_ratio * 100:.1f}% / 换手 {latest_turnover * 100:.2f}%", winner_tone, winner_summary),
        ChipControlEvidence("low_lock", "低位锁定", lock_value, lock_tone, lock_summary),
        ChipControlEvidence("breakout", "无量上穿密集区", breakout_value, breakout_tone, breakout_summary),
        ChipControlEvidence("cost_lines", "成本均线", cost_value, cost_tone, cost_summary),
    ]


def build_chip_distribution_profile(
    symbol: str,
    start_date: str,
    end_date: str,
    current_price: float,
    fallback_profile: ChipDistributionProfile | None = None,
) -> ChipDistributionProfile:
    try:
        frame = fetch_chip_hist_with_baostock(symbol, start_date, end_date)
    except Exception as exc:
        print(f"Warning: failed to fetch chip history for {symbol}: {exc}")
        return fallback_profile or default_chip_distribution(current_price)

    required_columns = {"date", "close", "preclose", "volume", "amount", "turn"}
    if frame.empty or not required_columns.issubset(frame.columns):
        return fallback_profile or default_chip_distribution(current_price)

    normalized = frame.copy()
    normalized["date"] = normalized["date"].astype(str)
    normalized = normalized.replace([np.inf, -np.inf], np.nan)
    normalized = normalized.dropna(subset=["date", "close", "preclose", "volume", "amount", "turn"])
    normalized = normalized[
        (normalized["close"] > 0) &
        (normalized["preclose"] > 0) &
        (normalized["volume"] > 0) &
        (normalized["amount"] > 0)
    ].copy()
    if normalized.empty:
        return fallback_profile or default_chip_distribution(current_price)

    normalized["pct_change"] = normalized["close"] / normalized["preclose"] - 1
    normalized["adj_factor"] = (1 + normalized["pct_change"]).cumprod()
    first_close = to_float(normalized.iloc[0]["close"], 0.0)
    first_factor = to_float(normalized.iloc[0]["adj_factor"], 1.0) or 1.0
    normalized["adj_close"] = normalized["adj_factor"] * (first_close / first_factor)
    normalized["avg_price"] = normalized["amount"] / normalized["volume"]
    normalized["adj_avg_price"] = normalized["adj_close"] * normalized["avg_price"] / normalized["close"]
    normalized["turnover"] = (normalized["turn"] / 100).clip(lower=0.0, upper=1.0)

    bucket_size = 0.2 if current_price >= 100 else 0.1
    chips: dict[float, float] = {}
    initial_price = bucket_price(to_float(normalized.iloc[0]["preclose"], current_price), bucket_size)
    chips[initial_price] = 1.0

    for row in normalized.itertuples(index=False):
        target_price = bucket_price(to_float(getattr(row, "adj_avg_price", 0.0), current_price), bucket_size)
        turnover = max(0.0, min(1.0, to_float(getattr(row, "turnover", 0.0), 0.0)))
        decay = 1.0 - turnover
        next_chips = {
            price: ratio * decay
            for price, ratio in chips.items()
            if ratio * decay >= 1e-6
        }
        next_chips[target_price] = next_chips.get(target_price, 0.0) + turnover
        chips = next_chips

    if not chips:
        return fallback_profile or default_chip_distribution(current_price)

    total_ratio = sum(chips.values())
    if total_ratio <= 0:
        return fallback_profile or default_chip_distribution(current_price)

    normalized_bands = sorted(
        ((price, ratio / total_ratio) for price, ratio in chips.items()),
        key=lambda item: item[0],
    )
    bands = [
        ChipDistributionBand(price=round(price, 2), ratio=round(ratio, 6))
        for price, ratio in normalized_bands
    ]
    dominant_price, dominant_ratio = max(normalized_bands, key=lambda item: item[1])
    average_cost = sum(price * ratio for price, ratio in normalized_bands)
    winner_ratio = sum(ratio for price, ratio in normalized_bands if price <= current_price)
    low_70 = weighted_price_quantile(normalized_bands, 0.15)
    high_70 = weighted_price_quantile(normalized_bands, 0.85)
    low_90 = weighted_price_quantile(normalized_bands, 0.05)
    high_90 = weighted_price_quantile(normalized_bands, 0.95)
    bias_pct = ((current_price / dominant_price) - 1) * 100 if dominant_price else 0.0
    zone_low, zone_high, zone_width_pct = resolve_main_cost_zone(
        normalized_bands,
        max(range(len(normalized_bands)), key=lambda index: normalized_bands[index][1]),
        dominant_ratio,
        dominant_price,
    )
    zone_span = max(high_90 - low_90, bucket_size)
    zone_position = (((zone_low + zone_high) / 2) - low_90) / zone_span if zone_span else 0.5
    peaks = find_significant_chip_peaks(normalized_bands, dominant_ratio)
    shape_label, stage_label, risk_label, shape_tone = resolve_chip_shape(
        peaks,
        low_90,
        high_90,
        zone_low,
        zone_high,
        zone_width_pct,
        current_price,
        dominant_price,
        winner_ratio,
        bucket_size,
    )
    control_evidence = build_chip_control_evidence(
        normalized,
        current_price,
        winner_ratio,
        zone_low,
        zone_high,
        zone_width_pct,
        zone_position,
    )

    zone_state = "位于主力成本区内"
    if current_price > zone_high:
        zone_state = f"高于主力成本区 {((current_price / zone_high) - 1) * 100:.1f}%"
    elif current_price < zone_low:
        zone_state = f"低于主力成本区 {(1 - (current_price / zone_low)) * 100:.1f}%"

    summary = (
        f"{shape_label}，主力成本区 {zone_low:.2f}-{zone_high:.2f}，"
        f"获利盘 {winner_ratio * 100:.1f}%，{zone_state}。{risk_label}"
    )

    return ChipDistributionProfile(
        algorithm="turnover_decay_v1",
        bucketSize=bucket_size,
        sampleSize=int(len(normalized)),
        tradeDate=str(normalized.iloc[-1]["date"])[:10],
        mainCost=round(dominant_price, 2),
        mainCostZoneLow=zone_low,
        mainCostZoneHigh=zone_high,
        mainCostZoneWidthPct=zone_width_pct,
        averageCost=round(average_cost, 2),
        winnerRatio=round(winner_ratio, 6),
        dominantRatio=round(dominant_ratio, 6),
        concentration70Low=low_70,
        concentration70High=high_70,
        concentration90Low=low_90,
        concentration90High=high_90,
        currentPriceBiasPct=round(bias_pct, 2),
        shapeLabel=shape_label,
        stageLabel=stage_label,
        riskLabel=risk_label,
        tone=shape_tone,
        summary=summary,
        controlEvidence=control_evidence,
        bands=bands,
    )


def grade_from_total_score(total_score: int) -> str:
    if total_score >= 85:
        return "A"
    if total_score >= 75:
        return "B+"
    if total_score >= 65:
        return "B"
    if total_score >= 55:
        return "C"
    return "D"


def build_selection_score(
    price_distribution: PriceDistributionProfile,
    amplitude_distribution: AmplitudeDistributionProfile,
    volume_ratio: float,
    technicals: TechnicalIndicators,
) -> SelectionScore:
    factors: list[ScoreFactor] = []

    position_pct = price_distribution.currentPositionPct
    position_score = 2
    position_summary = "年内高位，价格优势有限"
    position_tone = "negative"
    if position_pct <= 0.2:
        position_score = 20
        position_summary = "年内低位，价格周期占优"
        position_tone = "positive"
    elif position_pct <= 0.4:
        position_score = 17
        position_summary = "年内中低位，具备位置优势"
        position_tone = "positive"
    elif position_pct <= 0.6:
        position_score = 12
        position_summary = "年内中位，性价比中性"
        position_tone = "neutral"
    elif position_pct <= 0.8:
        position_score = 7
        position_summary = "年内偏高位，注意追涨风险"
        position_tone = "alert"

    factors.append(
        ScoreFactor(
            key="price_cycle",
            label="价格周期",
            score=position_score,
            maxScore=20,
            tone=position_tone,
            summary=position_summary,
        )
    )

    band_gap = amplitude_distribution.currentBand - amplitude_distribution.dominantBand
    amplitude_score = 6
    amplitude_summary = "振幅过热，警惕波动放大"
    amplitude_tone = "alert"
    if band_gap == 1:
        amplitude_score = 18
        amplitude_summary = "振幅略强于常态，活跃度理想"
        amplitude_tone = "positive"
    elif band_gap == 0:
        amplitude_score = 16
        amplitude_summary = "振幅处于常态活跃区"
        amplitude_tone = "positive"
    elif band_gap < 0:
        amplitude_score = 10
        amplitude_summary = "振幅偏弱，等待波动放大"
        amplitude_tone = "neutral"
    elif band_gap >= 2:
        amplitude_score = 4
        amplitude_summary = "振幅明显过热，先控风险"
        amplitude_tone = "negative"

    factors.append(
        ScoreFactor(
            key="amplitude_strength",
            label="振幅强度",
            score=amplitude_score,
            maxScore=20,
            tone=amplitude_tone,
            summary=amplitude_summary,
        )
    )

    volume_score = 2
    volume_summary = "量能不足，资金关注度弱"
    volume_tone = "negative"
    if volume_ratio >= 2.0:
        volume_score = 20
        volume_summary = "量能显著放大，资金参与强"
        volume_tone = "positive"
    elif volume_ratio >= 1.5:
        volume_score = 17
        volume_summary = "量能活跃，具备跟随价值"
        volume_tone = "positive"
    elif volume_ratio >= 1.2:
        volume_score = 14
        volume_summary = "量能温和放大，关注延续"
        volume_tone = "positive"
    elif volume_ratio >= 1.0:
        volume_score = 10
        volume_summary = "量能中性，等待放量确认"
        volume_tone = "neutral"
    elif volume_ratio >= 0.8:
        volume_score = 6
        volume_summary = "量能偏淡，尚未形成共振"
        volume_tone = "neutral"

    factors.append(
        ScoreFactor(
            key="volume_strength",
            label="量能",
            score=volume_score,
            maxScore=20,
            tone=volume_tone,
            summary=volume_summary,
        )
    )

    rsi = technicals.rsi14
    rsi_score = 3
    rsi_summary = "RSI 弱势区，先等修复"
    rsi_tone = "negative"
    if rsi.signalLabel == "RSI 上穿50":
        rsi_score = 20
        rsi_summary = "RSI 从30-50上穿50，重点关注买入"
        rsi_tone = "positive"
    elif rsi.signalLabel == "RSI 强势区":
        rsi_score = 17
        rsi_summary = "RSI 位于50-80强势区"
        rsi_tone = "positive"
    elif rsi.signalLabel == "RSI 观察区":
        rsi_score = 10
        rsi_summary = "RSI 位于30-50观察区"
        rsi_tone = "neutral"
    elif rsi.signalLabel == "RSI 跌破50":
        rsi_score = 5
        rsi_summary = "RSI 跌破50，强势失守"
        rsi_tone = "negative"
    elif rsi.signalLabel == "RSI 高风险":
        rsi_score = 1
        rsi_summary = "RSI 超过80，高风险区"
        rsi_tone = "alert"

    factors.append(
        ScoreFactor(
            key="rsi_signal",
            label="RSI",
            score=rsi_score,
            maxScore=20,
            tone=rsi_tone,
            summary=rsi_summary,
        )
    )

    macd = technicals.macd
    macd_score = 4
    macd_summary = "长周期空头，趋势拖累"
    macd_tone = "negative"
    if macd.signalLabel == "MACD 金叉":
        macd_score = 20
        macd_summary = "MACD 金叉，趋势扭转信号强"
        macd_tone = "positive"
    elif macd.signalLabel == "长周期多头":
        macd_score = 17
        macd_summary = "长周期多头，趋势保持完整"
        macd_tone = "positive"
    elif macd.signalLabel == "长周期修复":
        macd_score = 12
        macd_summary = "长周期修复，等待进一步确认"
        macd_tone = "neutral"
    elif macd.signalLabel == "长周期回落":
        macd_score = 8
        macd_summary = "长周期回落，关注是否再度走弱"
        macd_tone = "alert"
    elif macd.signalLabel == "MACD 死叉":
        macd_score = 3
        macd_summary = "MACD 死叉，短中期偏弱"
        macd_tone = "negative"

    factors.append(
        ScoreFactor(
            key="macd_trend",
            label="MACD趋势",
            score=macd_score,
            maxScore=20,
            tone=macd_tone,
            summary=macd_summary,
        )
    )

    total_score = sum(factor.score for factor in factors)
    sorted_factors = sorted(factors, key=lambda item: item.score, reverse=True)
    leading_summaries = [factor.summary for factor in sorted_factors[:2] if factor.score >= 14]
    if leading_summaries:
        summary = "；".join(leading_summaries)
    else:
        summary = "；".join(factor.summary for factor in sorted_factors[:2])

    return SelectionScore(
        total=total_score,
        maxScore=100,
        grade=grade_from_total_score(total_score),
        summary=summary,
        factors=factors,
    )


def build_amplitude_distribution(
    symbol: str,
    amplitude_series: list[float],
    current_amplitude: float,
    market_cap_yi: float,
) -> AmplitudeDistributionProfile:
    board_type, market_cap_bucket, amplitude_cap, edges = resolve_amplitude_template(symbol, market_cap_yi)
    source = amplitude_series if amplitude_series else [current_amplitude or 0.0]
    counts = [0] * (len(edges) - 1)
    sample_size = len(source)

    def resolve_band(value: float) -> int:
        bounded = clamp(value, 0.0, amplitude_cap)
        for index in range(len(edges) - 1):
            lower = edges[index]
            upper = edges[index + 1]
            if index == len(edges) - 2:
                if lower <= bounded <= upper:
                    return index
            elif lower <= bounded < upper:
                return index
        return len(edges) - 2

    for value in source:
        counts[resolve_band(value)] += 1

    current_band = resolve_band(current_amplitude)
    dominant_band = max(range(len(counts)), key=lambda index: counts[index])
    bands: list[PriceDistributionBand] = []
    for index, count in enumerate(counts):
        lower = edges[index]
        upper = edges[index + 1]
        bands.append(
            PriceDistributionBand(
                index=index,
                lower=round(lower, 2),
                upper=round(upper, 2),
                closeCount=count,
                ratio=round(count / sample_size if sample_size else 0.0, 4),
                rangeLabel=f"{lower:.1f}%-{upper:.1f}%",
            )
        )

    return AmplitudeDistributionProfile(
        boardType=board_type,
        marketCapYi=round(market_cap_yi, 2),
        marketCapBucket=market_cap_bucket,
        amplitudeCap=amplitude_cap,
        currentAmplitude=round(current_amplitude, 2),
        sampleSize=sample_size,
        currentBand=current_band,
        dominantBand=dominant_band,
        bands=bands,
    )


def build_stock(
    code: str,
    index: int,
    manual_name_map: dict[str, str],
    name_map: dict[str, str],
    start_date: str,
    end_date: str,
    fallback_stock: WatchStock | None = None,
) -> WatchStock:
    hist_df = fetch_hist(code, start_date, end_date)
    fallback_metadata = fallback_stock.metadata if fallback_stock else None
    fallback_company_insight = fallback_stock.companyInsight if fallback_stock else None
    fallback_chip_distribution = fallback_stock.chipDistribution if fallback_stock else None
    fallback_market_cap_yi = (
        fallback_stock.amplitudeDistribution.marketCapYi
        if fallback_stock and getattr(fallback_stock, "amplitudeDistribution", None)
        else 0.0
    )

    if hist_df.empty:
        fallback_price = fallback_stock.price if fallback_stock else 0.0
        fallback_change_pct = fallback_stock.changePct if fallback_stock else 0.0
        price = round(fallback_price, 2)
        change_pct = round(fallback_change_pct, 2)
        sparkline = (
            fallback_stock.sparkline[-8:]
            if fallback_stock and fallback_stock.sparkline
            else ([price] * 8 if price else [0.0] * 8)
        )
        candles = (
            fallback_stock.candles
            if fallback_stock and fallback_stock.candles
            else [
                CandlePoint(
                    date="",
                    open=round(price, 2),
                    high=round(price, 2),
                    low=round(price, 2),
                    close=round(price, 2),
                    isLimitUpClose=False,
                )
                for _ in range(12)
            ] if price else []
        )
        bollinger = (
            fallback_stock.bollinger
            if fallback_stock and fallback_stock.bollinger and fallback_stock.bollinger.points
            else BollingerProfile(
                period=30,
                stdMultiplier=2.0,
                points=[
                    BollingerPoint(date="", middle=round(price, 2), upper=round(price, 2), lower=round(price, 2))
                    for _ in range(len(candles))
                ],
            )
        ) if price else default_bollinger()
        momentum = 0
        volume_ratio = 0.0
        technicals = default_technicals()
        distribution = build_price_distribution([], price)
        chip_distribution = fallback_chip_distribution or default_chip_distribution(price)
        amplitude_distribution = build_amplitude_distribution(code, [], 0.0, fallback_market_cap_yi)
        limit_up_signal = fallback_stock.limitUpSignal if fallback_stock else default_limit_up_signal()
    else:
        recent = hist_df.tail(8)
        recent_candles = hist_df.tail(12).copy()
        close_series = [float(value) for value in hist_df[C_CLOSE].tolist()]
        last_close = float(recent.iloc[-1][C_CLOSE])
        prev_close = float(recent.iloc[-2][C_CLOSE]) if len(recent) > 1 else last_close
        hist_change = ((last_close - prev_close) / prev_close * 100) if prev_close else 0.0
        price = round(last_close, 2)
        change_pct = round(hist_change, 2)
        sparkline = [round(float(value), 2) for value in recent[C_CLOSE].tolist()]
        candles = build_recent_candles(code, recent_candles)
        bollinger = build_bollinger_profile(hist_df)
        ma5 = recent[C_CLOSE].tail(5).mean()
        momentum = int(max(0, min(99, 50 + ((last_close - ma5) / ma5 * 400 if ma5 else 0))))
        recent_volume = recent[C_VOLUME].tail(5).mean()
        base_volume = hist_df[C_VOLUME].tail(20).mean()
        volume_ratio = round(float(recent_volume / base_volume), 2) if base_volume else 0.0
        technicals = build_technical_indicators(close_series)
        distribution = build_price_distribution(close_series, price or last_close)
        chip_distribution = build_chip_distribution_profile(
            code,
            start_date,
            end_date,
            price or last_close,
            fallback_chip_distribution,
        )
        limit_up_signal = build_limit_up_signal_profile(code, hist_df, price or last_close)

        amplitude_series: list[float] = []
        if C_HIGH in hist_df.columns and C_LOW in hist_df.columns:
            prev_close_series = hist_df[C_CLOSE].shift(1)
            amplitude_frame = pd.DataFrame({
                C_HIGH: hist_df[C_HIGH],
                C_LOW: hist_df[C_LOW],
                "prev_close": prev_close_series,
            }).dropna()
            if not amplitude_frame.empty:
                amplitude_series = [
                    float(value)
                    for value in (((amplitude_frame[C_HIGH] - amplitude_frame[C_LOW]) / amplitude_frame["prev_close"]) * 100).tolist()
                ]

        current_amplitude = round(amplitude_series[-1], 2) if amplitude_series else 0.0
        market_cap_yi = fallback_market_cap_yi
        if "outstanding_share" in hist_df.columns and not hist_df["outstanding_share"].dropna().empty:
            latest_outstanding = float(hist_df["outstanding_share"].dropna().iloc[-1])
            market_cap_yi = round((price or last_close) * latest_outstanding / 100000000, 2)
        else:
            market_cap_yi = fetch_market_cap_yi(code, price or last_close, fallback_market_cap_yi)

        amplitude_distribution = build_amplitude_distribution(
            code,
            amplitude_series,
            current_amplitude,
            market_cap_yi,
        )

    selection_score = build_selection_score(
        distribution,
        amplitude_distribution,
        volume_ratio,
        technicals,
    )

    name = normalize_label(name_map.get(code) or manual_name_map.get(code) or (fallback_stock.name if fallback_stock else "") or code)
    sector = normalize_label((fallback_stock.sector if fallback_stock and fallback_stock.sector else "") or "自选池")
    change_label = f"{change_pct:+.2f}%"

    signals = [
        Signal("涨跌", change_label, calc_signal_level(change_pct, 2.0, 0.0)),
        Signal("动能", str(momentum), calc_signal_level(momentum, 75, 55)),
        Signal("量比", f"{volume_ratio:.2f}倍", calc_signal_level(volume_ratio, 1.2, 1.0)),
    ]
    metadata = fetch_stock_metadata(code, fallback_metadata)
    company_insight = build_company_insight(code, fallback_company_insight)

    built_stock = WatchStock(
        symbol=code,
        name=name,
        market="A股",
        sector=sector,
        price=price,
        changePct=change_pct,
        momentum=momentum,
        volumeRatio=volume_ratio,
        note=NOTE_POOL[index % len(NOTE_POOL)],
        thesis=THESIS_POOL[index % len(THESIS_POOL)],
        sparkline=sparkline,
        candles=candles,
        limitUpSignal=limit_up_signal,
        bollinger=bollinger,
        chipDistribution=chip_distribution,
        signals=signals,
        metadata=metadata,
        companyInsight=company_insight,
        technicals=technicals,
        selectionScore=selection_score,
        priceDistribution=distribution,
        amplitudeDistribution=amplitude_distribution,
        themeLinkage=(fallback_stock.themeLinkage if fallback_stock else default_stock_theme_linkage()),
    )

    has_meaningful_data = built_stock.price > 0 or built_stock.priceDistribution.sampleSize > 1
    if has_meaningful_data:
        write_stock_cache(code, start_date, end_date, built_stock)
        return built_stock

    return fallback_stock or built_stock


def main() -> None:
    ensure_cache_dirs()
    codes = read_codes()
    manual_name_map = read_watchlist_name_map()
    end = datetime.now()
    start = end - timedelta(days=365)
    start_date = start.strftime("%Y%m%d")
    end_date = end.strftime("%Y%m%d")

    name_map = fetch_name_map(codes)
    snapshot_stock_map = load_snapshot_stock_map()
    stocks = []
    try:
        for index, code in enumerate(codes):
            cached_stock, cached_payload = load_stock_cache(code)
            if cached_stock and is_stock_cache_fresh(cached_payload, start_date, end_date):
                needs_cache_rewrite = False
                if not cached_stock.metadata.officialWebsite:
                    fallback_stock = snapshot_stock_map.get(code)
                    fallback_metadata = fallback_stock.metadata if fallback_stock else None
                    refreshed_metadata = fetch_stock_metadata(code, fallback_metadata)
                    if refreshed_metadata.officialWebsite:
                        cached_stock.metadata = refreshed_metadata
                        needs_cache_rewrite = True
                if not has_meaningful_company_insight(cached_stock.companyInsight):
                    fallback_stock = snapshot_stock_map.get(code)
                    fallback_company_insight = fallback_stock.companyInsight if fallback_stock else None
                    refreshed_company_insight = build_company_insight(code, fallback_company_insight)
                    if has_meaningful_company_insight(refreshed_company_insight):
                        cached_stock.companyInsight = refreshed_company_insight
                        needs_cache_rewrite = True
                if needs_cache_rewrite:
                    write_stock_cache(code, start_date, end_date, cached_stock)
                stocks.append(cached_stock)
                continue

            fallback_stock = cached_stock or snapshot_stock_map.get(code)
            stocks.append(build_stock(code, index, manual_name_map, name_map, start_date, end_date, fallback_stock))
            time.sleep(0.15)
    finally:
        logout_baostock()

    market_radar = enrich_market_radar(stocks)

    avg_change = round(sum(stock.changePct for stock in stocks) / len(stocks), 2) if stocks else 0.0
    strong_signals = sum(1 for stock in stocks if any(signal.level == "strong" for signal in stock.signals))

    payload = {
        "syncTime": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "watchlistCount": len(stocks),
        "strongSignals": strong_signals,
        "avgChange": avg_change,
        "mood": "偏强" if avg_change >= 0 else "分化",
        "marketRadar": asdict(market_radar),
        "stocks": [
            {
                **{key: value for key, value in asdict(stock).items() if key != "signals"},
                "signals": [asdict(signal) for signal in stock.signals],
            }
            for stock in stocks
        ],
    }

    safe_payload = sanitize_json_value(payload)
    OUTPUT_PATH.write_text(json.dumps(safe_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写入 {len(stocks)} 只股票的 AkShare 快照到 {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
