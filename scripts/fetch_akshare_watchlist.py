import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import math
from pathlib import Path
import re
import time

import akshare as ak
import pandas as pd

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
STOCK_CACHE_VERSION = 8
WATCHLIST_ENTRY_PATTERN = re.compile(
    r'\{\s*code:\s*["\'](?P<code>\d{6})["\']\s*,\s*name:\s*["\'](?P<name>[^"\']*)["\']\s*\}'
)

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
    signals: list[Signal]
    metadata: StockMetadata
    companyInsight: CompanyInsight
    technicals: TechnicalIndicators
    selectionScore: SelectionScore
    priceDistribution: PriceDistributionProfile
    amplitudeDistribution: AmplitudeDistributionProfile


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
        signals=signals,
        metadata=metadata_from_dict(data.get("metadata", {})),
        companyInsight=company_insight_from_dict(data.get("companyInsight", {})),
        technicals=technicals_from_dict(data.get("technicals", {})),
        selectionScore=selection_score_from_dict(data.get("selectionScore", {})),
        priceDistribution=distribution_from_dict(data.get("priceDistribution", {})),
        amplitudeDistribution=amplitude_distribution_from_dict(data.get("amplitudeDistribution", {})),
    )


def ensure_cache_dirs() -> None:
    HIST_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    STOCK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CAP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    META_CACHE_DIR.mkdir(parents=True, exist_ok=True)


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


def default_selection_score() -> SelectionScore:
    return SelectionScore(
        total=0,
        maxScore=100,
        grade="D",
        summary="等待更多信号",
        factors=[],
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


def normalize_text_block(value: object) -> str:
    text = normalize_label(value)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


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


def symbol_for_zygc(symbol: str) -> str:
    prefix = "SH" if symbol.startswith(("600", "601", "603", "605", "688")) else "SZ"
    return f"{prefix}{symbol}"


def extract_theme_keywords(*texts: object) -> list[str]:
    haystack = " ".join(normalize_text_block(item) for item in texts if item is not None)
    matched = [keyword for keyword in THEME_KEYWORDS + POLICY_KEYWORDS if keyword and keyword in haystack]
    return unique_in_order(matched)


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
    if "amount" in normalized.columns and C_VOLUME not in normalized.columns:
        column_map["amount"] = C_VOLUME
    if column_map:
        normalized = normalized.rename(columns=column_map)

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


def fetch_hist(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    cached_df, cached_payload = load_hist_cache(symbol)
    if not cached_df.empty and is_hist_cache_fresh(cached_payload, start_date, end_date):
        return cached_df

    hist_df = pd.DataFrame()
    market_prefix = "sh" if symbol.startswith(("600", "601", "603", "605", "688")) else "sz"
    alt_symbol = f"{market_prefix}{symbol}"

    fetchers = [
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
    if "close" in normalized.columns and C_CLOSE not in normalized.columns:
        column_map["close"] = C_CLOSE
    if "high" in normalized.columns and C_HIGH not in normalized.columns:
        column_map["high"] = C_HIGH
    if "low" in normalized.columns and C_LOW not in normalized.columns:
        column_map["low"] = C_LOW
    if "amount" in normalized.columns and C_VOLUME not in normalized.columns:
        column_map["amount"] = C_VOLUME
    if column_map:
        normalized = normalized.rename(columns=column_map)

    normalized[C_CLOSE] = pd.to_numeric(normalized.get(C_CLOSE), errors="coerce")
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
    spot_map: dict[str, dict],
    start_date: str,
    end_date: str,
    fallback_stock: WatchStock | None = None,
) -> WatchStock:
    hist_df = fetch_hist(code, start_date, end_date)
    spot = spot_map.get(code, {})
    fallback_metadata = fallback_stock.metadata if fallback_stock else None
    fallback_company_insight = fallback_stock.companyInsight if fallback_stock else None
    fallback_market_cap_yi = (
        fallback_stock.amplitudeDistribution.marketCapYi
        if fallback_stock and getattr(fallback_stock, "amplitudeDistribution", None)
        else 0.0
    )

    if hist_df.empty:
        price = round(float(spot.get(C_LATEST, 0) or 0), 2)
        change_pct = round(float(spot.get(C_CHANGE, 0) or 0), 2)
        sparkline = [price] * 8 if price else [0.0] * 8
        momentum = 0
        volume_ratio = 0.0
        technicals = default_technicals()
        distribution = build_price_distribution([], price)
        amplitude_distribution = build_amplitude_distribution(code, [], 0.0, fallback_market_cap_yi)
    else:
        recent = hist_df.tail(8)
        close_series = [float(value) for value in hist_df[C_CLOSE].tolist()]
        last_close = float(recent.iloc[-1][C_CLOSE])
        prev_close = float(recent.iloc[-2][C_CLOSE]) if len(recent) > 1 else last_close
        hist_change = ((last_close - prev_close) / prev_close * 100) if prev_close else 0.0
        price = round(float(spot.get(C_LATEST, last_close) or last_close), 2)
        change_pct = round(float(spot.get(C_CHANGE, hist_change) or hist_change), 2)
        sparkline = [round(float(value), 2) for value in recent[C_CLOSE].tolist()]
        ma5 = recent[C_CLOSE].tail(5).mean()
        momentum = int(max(0, min(99, 50 + ((last_close - ma5) / ma5 * 400 if ma5 else 0))))
        recent_volume = recent[C_VOLUME].tail(5).mean()
        base_volume = hist_df[C_VOLUME].tail(20).mean()
        volume_ratio = round(float(recent_volume / base_volume), 2) if base_volume else 0.0
        technicals = build_technical_indicators(close_series)
        distribution = build_price_distribution(close_series, price or last_close)

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

    name = normalize_label(spot.get(C_NAME) or name_map.get(code) or manual_name_map.get(code) or code)
    sector = normalize_label(spot.get(C_INDUSTRY) or "自选池")
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
        signals=signals,
        metadata=metadata,
        companyInsight=company_insight,
        technicals=technicals,
        selectionScore=selection_score,
        priceDistribution=distribution,
        amplitudeDistribution=amplitude_distribution,
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
    spot_map = fetch_spot_map(codes)
    snapshot_stock_map = load_snapshot_stock_map()
    stocks = []
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
        stocks.append(build_stock(code, index, manual_name_map, name_map, spot_map, start_date, end_date, fallback_stock))
        time.sleep(0.15)

    avg_change = round(sum(stock.changePct for stock in stocks) / len(stocks), 2) if stocks else 0.0
    strong_signals = sum(1 for stock in stocks if any(signal.level == "strong" for signal in stock.signals))

    payload = {
        "syncTime": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "watchlistCount": len(stocks),
        "strongSignals": strong_signals,
        "avgChange": avg_change,
        "mood": "偏强" if avg_change >= 0 else "分化",
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
