import { useEffect, useRef, useState, type CSSProperties } from "react";
import { getInitialSnapshot } from "./data/mock";
import {
  isTauriRuntime,
  listenDashboardRefresh,
  loadDashboardSnapshot,
  openExternalLink,
  startDashboardRefresh,
} from "./tauriBridge";
import type {
  AmplitudeDistributionProfile,
  BollingerProfile,
  CandlePoint,
  ChipControlEvidence,
  ChipDistributionProfile,
  CycleAnalysis,
  CycleWindow,
  CompanyInsight,
  DashboardSnapshot,
  MarketRadar,
  PriceDistributionProfile,
  SelectionScore,
  SignalLevel,
  TechnicalIndicators,
  ThemeHotspot,
  UsFocusItem,
  WatchStock
} from "./types";

const moodLabelMap: Record<string, string> = {
  "risk-on": "偏强",
  mixed: "分化",
  偏强: "偏强",
  分化: "分化"
};

const marketLabelMap: Record<string, string> = {
  CN: "A股",
  A股: "A股"
};

const sectorLabelMap: Record<string, string> = {
  Watchlist: "自选池",
  自选池: "自选池"
};

const signalLabelMap: Record<string, string> = {
  Change: "涨跌",
  Momentum: "动能",
  Volume: "量比",
  涨跌: "涨跌",
  动能: "动能",
  量比: "量比"
};

const noteTextMap: Record<string, string> = {
  "Watch whether the tape confirms the setup into the close.": "收盘前观察盘口是否确认当前形态。",
  "Keep this on radar for a stronger volume expansion day.": "继续跟踪，等待更强的放量日。",
  "Trend structure is constructive, but confirmation still matters.": "趋势结构尚可，但仍需进一步确认。",
  "A clean follow-through day would improve confidence.": "若出现干净的延续日，信号可信度会更高。",
  "Treat this as a tracking name until price and volume align.": "在价量重新共振前，先作为跟踪标的。"
};

const thesisTextMap: Record<string, string> = {
  "Track whether sector strength is broadening around this name.": "观察该股周边板块强度是否继续扩散。",
  "Use daily structure and turnover to judge conviction.": "结合日线结构与换手强度判断资金共识。",
  "Focus on whether the current swing can hold above recent support.": "重点看当前波段能否站稳近期支撑。",
  "Keep this in the pool for momentum confirmation rather than prediction.": "保留在自选池中，等待动能确认，而不是提前预判。",
  "A stronger close and cleaner breadth would upgrade the setup.": "若收盘更强、板块扩散更清晰，可上调关注级别。"
};

function createDefaultCompanyInsight(): CompanyInsight {
  return {
    updatedAt: "",
    accountingBusiness: {
      reportDate: "",
      classification: "",
      summary: "暂无会计主营拆分数据",
      segments: []
    },
    officialBusiness: {
      companyName: "",
      industry: "",
      mainBusiness: "",
      businessScope: "",
      companyIntro: ""
    },
    newsSensitivity: {
      score: 0,
      level: "低",
      summary: "暂无新闻与政策敏感度样本",
      matchedKeywords: [],
      items: []
    },
    researchFocus: {
      monthlyReportCount: 0,
      summary: "暂无券商研报样本",
      focusKeywords: [],
      items: []
    }
  };
}

function App() {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot>(getInitialSnapshot());
  const [syncStatus, setSyncStatus] = useState("默认不自动刷新。需要时手动触发，后台异步更新。");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [activeStock, setActiveStock] = useState<WatchStock | null>(null);
  const [isRadarOpen, setIsRadarOpen] = useState(false);
  const stockCardRefs = useRef<Record<string, HTMLElement | null>>({});
  const stockHighlightTimers = useRef<Record<string, number>>({});

  useEffect(() => {
    let cancelled = false;

    loadDashboardSnapshot()
      .then((nextSnapshot) => {
        if (!cancelled) {
          setSnapshot(nextSnapshot);
          setSyncStatus(`当前快照：${nextSnapshot.syncTime}。默认不自动刷新。`);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSyncStatus("当前使用本地快照，浏览器模式下无法执行桌面刷新。");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!activeStock && !isRadarOpen) {
      return undefined;
    }

    const originalOverflow = document.body.style.overflow;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setActiveStock(null);
        setIsRadarOpen(false);
      }
    };

    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [activeStock, isRadarOpen]);
  useEffect(() => {
    if (!isTauriRuntime()) {
      return undefined;
    }

    let cancelled = false;
    let unlisten: (() => void) | undefined;

    void listenDashboardRefresh(async (event) => {
      if (cancelled) {
        return;
      }

      if (event.status === "error") {
        setIsRefreshing(false);
        setSyncStatus(event.message || "后台刷新失败。");
        return;
      }

      try {
        const nextSnapshot = await loadDashboardSnapshot();
        if (cancelled) {
          return;
        }
        setSnapshot(nextSnapshot);
        setSyncStatus(event.message || `行情快照已刷新：${nextSnapshot.syncTime}`);
      } catch {
        if (!cancelled) {
          setSyncStatus(event.message || "行情快照已刷新。");
        }
      } finally {
        if (!cancelled) {
          setIsRefreshing(false);
        }
      }
    }).then((dispose) => {
      unlisten = dispose;
    });

    return () => {
      cancelled = true;
      unlisten?.();
    };
  }, []);

  const leaders = [...snapshot.stocks]
    .sort((left, right) => right.changePct - left.changePct)
    .slice(0, 3);
  const featuredStocks = [...snapshot.stocks]
    .sort((left, right) => right.selectionScore.total - left.selectionScore.total)
    .slice(0, 5);
  const sortedStocks = sortStocksByRecentLimitUp(snapshot.stocks);
  const marketRadar = resolveMarketRadar(snapshot.marketRadar);

  async function handleRefresh() {
    if (isRefreshing) {
      return;
    }

    setIsRefreshing(true);
    setSyncStatus("已发起后台刷新。你可以继续浏览当前页面。");

    try {
      const started = await startDashboardRefresh();
      if (!started) {
        setSyncStatus("后台已有刷新任务在执行。你可以继续浏览当前页面。");
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "刷新失败。";
      setSyncStatus(message);
      setIsRefreshing(false);
    }
  }
  async function handleOpenLink(url: string) {
    if (!url) {
      return;
    }

    try {
      await openExternalLink(url);
    } catch (error) {
      console.error("打开外部链接失败", error);
    }
  }


  useEffect(() => {
    return () => {
      Object.values(stockHighlightTimers.current).forEach((timerId) => {
        window.clearTimeout(timerId);
      });
    };
  }, []);

  function handleLocateStock(symbol: string) {
    const target = stockCardRefs.current[symbol];
    if (!target) {
      return;
    }

    target.scrollIntoView({ behavior: "smooth", block: "center" });
    target.classList.remove("stock-card-highlight");
    void target.offsetWidth;
    target.classList.add("stock-card-highlight");

    const existingTimer = stockHighlightTimers.current[symbol];
    if (existingTimer) {
      window.clearTimeout(existingTimer);
    }

    stockHighlightTimers.current[symbol] = window.setTimeout(() => {
      target.classList.remove("stock-card-highlight");
      delete stockHighlightTimers.current[symbol];
    }, 1600);
  }

  return (
    <>
      <main className="app-shell">
        <section className="hero-panel">
          <div className="hero-copy">
            <p className="eyebrow">Tauri 2 自选跟踪台</p>
            <h1>美股映射 + 全球大宗期货跟踪。</h1>
            <p className="hero-text">
              当前已经接入 A 股板块联动、热ETF 映射和隔夜美股晨报；全球大宗期货跟踪还没有接入真实数据，这一块我会放到下一步            </p>
            <p className="sync-status">{syncStatus}</p>
          </div>

          <div className="hero-stats">
            <StatCard label="自选池" value={String(snapshot.watchlistCount)} />
            <StatCard label="强信号" value={String(snapshot.strongSignals)} />
            <StatCard label="平均涨跌" value={`${snapshot.avgChange.toFixed(2)}%`} />
            <StatCard label="最近同步" value={snapshot.syncTime} />
          </div>
        </section>

        <FeaturedSelectionBoard stocks={featuredStocks} onLocateStock={handleLocateStock} />
        <CycleOverviewBoard stocks={snapshot.stocks} />
        <MarketRadarBoard
          radar={marketRadar}
          onOpen={() => {
            setIsRadarOpen(true);
          }}
        />

        <section className="market-strip">
          <div>
            <p className="section-label">市场温度</p>
            <strong>{formatMoodLabel(snapshot.mood)}</strong>
          </div>
          <div>
            <p className="section-label">领涨观察</p>
            <div className="leader-list">
              {leaders.map((stock) => (
                <span key={stock.symbol}>
                  {stock.name} {formatSigned(stock.changePct)}%
                </span>
              ))}
            </div>
          </div>
        </section>

        <section className="board-header">
          <div>
            <p className="section-label">自选看板</p>
            <h2>每只股票都带有价格位置、振幅、技术指标和弹窗详情</h2>
          </div>
          <div className="board-header-actions">
            <button className="ghost-button" type="button" onClick={handleRefresh} disabled={isRefreshing}>
              {isRefreshing ? "后台刷新中..." : "手动刷新行情快照"}
            </button>
          </div>
        </section>

        <section className="card-grid">
          {sortedStocks.map((stock) => (
            <StockCard
              key={stock.symbol}
              stock={stock}
              cardRef={(node) => {
                stockCardRefs.current[stock.symbol] = node;
              }}
              onOpenInsight={() => {
                setActiveStock(stock);
              }}
              onOpenLink={handleOpenLink}
            />
          ))}
        </section>
      </main>

      {activeStock ? (
        <InsightModal
          stock={activeStock}
          onClose={() => {
            setActiveStock(null);
          }}
          onOpenLink={handleOpenLink}
        />
      ) : null}

      {isRadarOpen ? (
        <MarketRadarModal
          radar={marketRadar}
          onClose={() => {
            setIsRadarOpen(false);
          }}
          onOpenLink={handleOpenLink}
        />
      ) : null}

    </>
  );
}

function StatCard(props: { label: string; value: string }) {
  return (
    <article className="stat-card">
      <p>{props.label}</p>
      <strong>{props.value}</strong>
    </article>
  );
}

function FeaturedSelectionBoard(props: { stocks: WatchStock[]; onLocateStock: (symbol: string) => void }) {
  return (
    <section className="featured-board">
      <div className="featured-header">
        <div>
          <p className="section-label">精选15股</p>
          <h2>按综合评分优先观察的高分股票</h2>
        </div>
        <p className="featured-caption">当前基于价格周期、振幅、量能、RSI 和 MACD 趋势评分。</p>
      </div>

      <div className="featured-grid">
        {props.stocks.map((stock, index) => (
          <button
            className="featured-card featured-card-button"
            key={`featured-${stock.symbol}`}
            type="button"
            onClick={() => {
              props.onLocateStock(stock.symbol);
            }}
            title={`定位到 ${stock.name} 卡片`}
          >
            <div className="featured-rank">#{index + 1}</div>
            <div className="featured-main">
              <p className="section-label">{stock.symbol}</p>
              <h3>{stock.name}</h3>
              <p className="featured-summary">{stock.selectionScore.summary}</p>
            </div>
            <div className="featured-score">
              <strong>{stock.selectionScore.total}</strong>
              <span>/ {stock.selectionScore.maxScore}</span>
              <em>{stock.selectionScore.grade}</em>
            </div>
            <div className="featured-factors">
              {topScoreFactors(stock.selectionScore).map((factor) => (
                <span className={`featured-factor ${factor.tone}`} key={`${stock.symbol}-${factor.key}`}>
                  {factor.label} {factor.score}
                </span>
              ))}
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}

function CycleOverviewBoard(props: { stocks: WatchStock[] }) {
  const clearStocks = props.stocks
    .filter((stock) => stock.cycleAnalysis?.level === "明显规律")
    .sort((left, right) => (right.cycleAnalysis?.score ?? 0) - (left.cycleAnalysis?.score ?? 0));
  const weakStocks = props.stocks
    .filter((stock) => stock.cycleAnalysis?.level === "弱规律" || stock.cycleAnalysis?.level === "规律不明显")
    .sort((left, right) => (left.cycleAnalysis?.score ?? 0) - (right.cycleAnalysis?.score ?? 0));
  const usableCount = props.stocks.filter((stock) => stock.cycleAnalysis?.level === "可跟踪规律").length;
  const activeRangeStocks = props.stocks
    .filter((stock) => stock.cycleAnalysis?.regime.label === "活跃波段")
    .sort((left, right) => (right.cycleAnalysis?.regime.amplitudeRatio ?? 0) - (left.cycleAnalysis?.regime.amplitudeRatio ?? 0));
  const trendStocks = props.stocks
    .filter((stock) => stock.cycleAnalysis?.regime.label === "活跃波段")
    .sort((left, right) => (right.cycleAnalysis?.regime.currentPositionPct ?? 0) - (left.cycleAnalysis?.regime.currentPositionPct ?? 0));

  return (
    <section className="cycle-board">
      <div className="featured-header">
        <div>
          <p className="section-label">周期总览</p>
          <h2>把波峰波谷节奏直接标到自选池里</h2>
        </div>
        <p className="featured-caption">明显规律优先保留，弱规律优先复核。每次桌面端刷新时会同步重算周期报告。</p>
      </div>

      <div className="cycle-summary-grid">
        <article className="cycle-summary-card clear">
          <p className="section-label">明显规律</p>
          <strong>{clearStocks.length}</strong>
          <span>适合长期跟踪</span>
        </article>
        <article className="cycle-summary-card usable">
          <p className="section-label">可跟踪规律</p>
          <strong>{usableCount}</strong>
          <span>继续观察</span>
        </article>
        <article className="cycle-summary-card weak">
          <p className="section-label">弱规律</p>
          <strong>{weakStocks.length}</strong>
          <span>优先复核</span>
        </article>
      </div>

      <div className="cycle-list-grid">
        <article className="cycle-list-card">
          <p className="section-label">优先保留</p>
          <div className="cycle-chip-row">
            {clearStocks.slice(0, 6).map((stock) => (
              <span className="cycle-chip clear" key={`clear-${stock.symbol}`}>
                {stock.name} {stock.cycleAnalysis?.score}
              </span>
            ))}
          </div>
        </article>

        <article className="cycle-list-card">
          <p className="section-label">优先复核</p>
          {weakStocks.length > 0 ? (
            <div className="cycle-chip-row">
              {weakStocks.slice(0, 6).map((stock) => (
                <span className="cycle-chip weak" key={`weak-${stock.symbol}`}>
                  {stock.name} {stock.cycleAnalysis?.score}
                </span>
              ))}
            </div>
          ) : (
            <p className="cycle-empty">当前没有落入弱规律区的股票。</p>
          )}
        </article>
      </div>

      <div className="cycle-list-grid">
        <article className="cycle-list-card">
          <p className="section-label">活跃波段{activeRangeStocks.length}</p>
          {activeRangeStocks.length > 0 ? (
            <div className="cycle-chip-row">
              {activeRangeStocks.slice(0, 8).map((stock) => (
                <span className={`cycle-chip ${regimeChipTone(stock.cycleAnalysis?.regime.tone)}`} key={`range-${stock.symbol}`}>
                  {stock.name} · {stock.cycleAnalysis?.regime.actionLabel}
                </span>
              ))}
            </div>
          ) : (
            <p className="cycle-empty">当前没有落入弱规律区的股票。</p>
          )}
        </article>

        <article className="cycle-list-card">
          <p className="section-label">趋势推进{trendStocks.length}</p>
          {trendStocks.length > 0 ? (
            <div className="cycle-chip-row">
              {trendStocks.slice(0, 8).map((stock) => (
                <span className={`cycle-chip ${regimeChipTone(stock.cycleAnalysis?.regime.tone)}`} key={`trend-${stock.symbol}`}>
                  {stock.name} · {stock.cycleAnalysis?.regime.actionLabel}
                </span>
              ))}
            </div>
          ) : (
            <p className="cycle-empty">当前没有趋势推进股票。</p>
          )}
        </article>
      </div>
    </section>
  );
}

function MarketRadarBoard(props: {
  radar: MarketRadar;
  onOpen: () => void;
}) {
  const hottestBoards = props.radar.hottestBoards.slice(0, 4);
  const usLeaders = props.radar.usMarketPulse.items
    .filter((item) => item.symbol)
    .sort((left, right) => right.changePct - left.changePct)
    .slice(0, 3);

  return (
    <section className="market-radar-board">
      <div className="featured-header">
        <div>
          <p className="section-label">板块联动 / 美股晨报</p>
          <h2>把热点板块、ETF 和隔夜美股映射压到一个入口里。</h2>
        </div>
        <button className="ghost-button" type="button" onClick={props.onOpen}>
          查看联动详情
        </button>
      </div>

      <div className="market-radar-grid">
        <article className="market-radar-card">
          <p className="section-label">热点板块</p>
          <div className="cycle-chip-row">
            {hottestBoards.length > 0 ? (
              hottestBoards.map((item) => (
                <span className={`cycle-chip ${hotspotTone(item.changePct)}`} key={`${item.boardType}-${item.code || item.name}`}>
                  {item.name} {formatSigned(item.changePct)}%
                </span>
              ))
            ) : (
              <p className="cycle-empty">暂无热点板块快照。</p>
            )}
          </div>
        </article>

        <article className="market-radar-card">
          <p className="section-label">美股热点</p>
          <div className="cycle-chip-row">
            {usLeaders.length > 0 ? (
              usLeaders.map((item) => (
                <span className={`cycle-chip ${hotspotTone(item.changePct)}`} key={item.key}>
                  {item.name} {formatSigned(item.changePct)}%
                </span>
              ))
            ) : (
              <p className="cycle-empty">暂无热点板块快照。</p>
            )}
          </div>
          <p className="distribution-caption">{props.radar.usMarketPulse.summary}</p>
        </article>
      </div>
    </section>
  );
}

function StockCard(props: {
  stock: WatchStock;
  cardRef?: (node: HTMLElement | null) => void;
  onOpenInsight: () => void;
  onOpenLink: (url: string) => Promise<void>;
}) {
  const { stock, cardRef, onOpenInsight, onOpenLink } = props;
  const officialWebsite = stock.metadata.officialWebsite;
  const insight = resolveCompanyInsight(stock.companyInsight);
  const cycle = stock.cycleAnalysis;
  const themeLinkage = resolveThemeLinkage(stock.themeLinkage);
  const displayThemes = buildDisplayThemes(themeLinkage);
  const limitUpStats = getRecentLimitUpStats(stock);

  return (
    <article className="stock-card" ref={cardRef}>
      <header className="stock-card-header">
        <div>
          <p className="section-label">
            {formatMarketLabel(stock.market)} / {formatSectorLabel(stock.sector)}
          </p>
          <h3>{stock.name}</h3>
          <span className="ticker">{stock.symbol}</span>
          {displayThemes.length > 0 ? (
            <div className="theme-style-row">
              {displayThemes.map((item) => (
                <span className={`theme-style-pill ${item.tone}`} key={`${stock.symbol}-${item.label}-${item.value}`}>
                  {item.label} {item.value}
                </span>
              ))}
            </div>
          ) : null}
          <div className="score-pill-row">
            <span className={`score-pill ${scoreTone(stock.selectionScore)}`}>
              精选评分 {stock.selectionScore.total} / {stock.selectionScore.maxScore}
            </span>
            <span className="score-grade">{stock.selectionScore.grade}</span>
            <span className={`score-pill ${stock.chipDistribution.tone}`}>
              筹码 {stock.chipDistribution.shapeLabel}
            </span>
            {cycle ? (
              <span className={`score-pill ${cycle.regime.tone}`}>
                状态 {cycle.regime.label}
              </span>
            ) : null}
            {cycle ? (
              <span className={`score-pill ${cycleTone(cycle.level)}`}>
                周期 {cycle.level} · {cycle.score}
              </span>
            ) : null}
            <span className={`score-pill ${insightLevelTone(insight.newsSensitivity.level)}`}>
              新闻敏感度 {insight.newsSensitivity.level}
            </span>
            {stock.limitUpSignal.isHoldingAboveOpen ? (
              <span className={`score-pill ${stock.limitUpSignal.tone}`}>
                重点 守开 {stock.limitUpSignal.holdDays} 天
              </span>
            ) : null}
            {limitUpStats.count > 0 ? (
              <span className="score-pill alert">
                近 10 日涨停 {limitUpStats.count}
              </span>
            ) : null}
          </div>
          {stock.limitUpSignal.isHoldingAboveOpen ? (
            <p className="limit-up-summary">{stock.limitUpSignal.summary}</p>
          ) : null}
          <div className="stock-link-row">
            {officialWebsite ? (
              <>
                <button
                  className="meta-link-button"
                  type="button"
                  onClick={() => {
                    void onOpenLink(officialWebsite);
                  }}
                  title={`打开官网：${officialWebsite}`}
                >
                  官网
                </button>
                <span className="meta-link-text">{formatWebsiteLabel(officialWebsite)}</span>
              </>
            ) : null}
            <button className="meta-link-button secondary" type="button" onClick={onOpenInsight}>
              信息采集
            </button>
          </div>
        </div>
        <div className={stock.changePct >= 0 ? "pill up" : "pill down"}>{formatSigned(stock.changePct)}%</div>
      </header>

      <div className="price-row">
        <strong>{stock.price.toFixed(2)}</strong>
        <span>动能 {stock.momentum}</span>
        <span>量比 {stock.volumeRatio.toFixed(2)} 倍</span>
      </div>

      <CandlestickChart
        candles={stock.candles}
        bollinger={stock.bollinger}
        limitUpSignal={stock.limitUpSignal}
        cycle={cycle}
      />
      <PriceBattery profile={stock.priceDistribution} currentPrice={stock.price} />
      <AmplitudeDistributionPanel profile={stock.amplitudeDistribution} />
      <TechnicalsPanel profile={stock.technicals} />
      {cycle ? <CyclePanel analysis={cycle} compact /> : null}

      <div className="signal-row">
        {stock.signals.map((signal) => (
          <SignalTag
            key={`${stock.symbol}-${signal.label}`}
            label={`${formatSignalLabel(signal.label)}锛?{formatSignalValue(signal.label, signal.value)}`}
            level={signal.level}
          />
        ))}
      </div>

      <p className="note">{formatNoteText(stock.note)}</p>
      <p className="thesis">{formatThesisText(stock.thesis)}</p>
    </article>
  );
}

function InsightModal(props: {
  stock: WatchStock;
  onClose: () => void;
  onOpenLink: (url: string) => Promise<void>;
}) {
  const { stock, onClose, onOpenLink } = props;
  const insight = resolveCompanyInsight(stock.companyInsight);
  const officialWebsite = stock.metadata.officialWebsite;
  const themeLinkage = resolveThemeLinkage(stock.themeLinkage);
  const chipDistribution = stock.chipDistribution;

  return (
    <section
      className="detail-modal-backdrop"
      onClick={onClose}
      aria-label={`个股信息弹窗{stock.name}`}
      role="dialog"
      aria-modal="true"
    >
      <article
        className="detail-modal"
        onClick={(event) => {
          event.stopPropagation();
        }}
      >
        <header className="detail-modal-header">
          <div>
            <p className="section-label">{stock.symbol}</p>
            <h2>
              {stock.name}
              <span>{formatMarketLabel(stock.market)}</span>
            </h2>
            <div className="detail-badges">
              <span className={`detail-badge ${insightLevelTone(insight.newsSensitivity.level)}`}>
                新闻敏感度 {insight.newsSensitivity.level}
              </span>
              <span className="detail-badge neutral">近一月研报 {insight.researchFocus.monthlyReportCount}</span>
              <span className="detail-badge neutral">更新时间 {insight.updatedAt || "未记录"}</span>
            </div>
          </div>
          <div className="detail-header-actions">
            {officialWebsite ? (
              <button
                className="meta-link-button"
                type="button"
                onClick={() => {
                  void onOpenLink(officialWebsite);
                }}
              >
                打开官网
              </button>
            ) : null}
            <button className="modal-close-button" type="button" onClick={onClose}>
              关闭
            </button>
          </div>
        </header>

        <div className="detail-modal-body">
          {stock.cycleAnalysis ? (
            <section className="detail-section">
              <CyclePanel analysis={stock.cycleAnalysis} />
            </section>
          ) : null}

          <ChipDistributionDetail profile={chipDistribution} currentPrice={stock.price} />

          <section className="detail-section">
            <div className="distribution-header">
              <div>
                <p className="section-label">板块联动</p>
                <strong>{themeLinkage.summary}</strong>
              </div>
              <span className="distribution-pill balanced">
                {themeLinkage.updatedAt || "等待刷新"}
              </span>
            </div>

            <div className="detail-text-grid">
              <article className="detail-text-card">
                <p className="section-label">关联行业</p>
                <p>{themeLinkage.industry || "暂无热点行业重合"}</p>
              </article>
              <article className="detail-text-card">
                <p className="section-label">关联概念</p>
                <p>{themeLinkage.concepts.length > 0 ? themeLinkage.concepts.join("、") : "暂无热点概念重合"}</p>
              </article>
            </div>

            {themeLinkage.matchedKeywords.length > 0 ? (
              <div className="detail-chip-row">
                {themeLinkage.matchedKeywords.map((keyword) => (
                  <span className="detail-chip" key={`${stock.symbol}-theme-${keyword}`}>
                    {keyword}
                  </span>
                ))}
              </div>
            ) : null}

            <ThemeHotspotList title="热点板块" items={themeLinkage.hotBoards} />
            <ThemeHotspotList title="相关 ETF" items={themeLinkage.relatedEtfs} />
          </section>

          <section className="detail-section">
            <div className="distribution-header">
              <div>
                <p className="section-label">会计主营</p>
                <strong>{insight.accountingBusiness.summary}</strong>
              </div>
              <span className="distribution-pill balanced">
                {insight.accountingBusiness.reportDate || "暂无报告期"}
              </span>
            </div>

            {insight.accountingBusiness.segments.length > 0 ? (
              <div className="segment-grid">
                {insight.accountingBusiness.segments.map((segment) => (
                  <article className="segment-card" key={`${stock.symbol}-${segment.name}`}>
                    <h3>{segment.name}</h3>
                    <div className="segment-meta">
                      <span>收入 {formatYi(segment.revenueYi)}</span>
                      <span>收入占比 {formatPercent(segment.revenueRatio)}</span>
                    </div>
                    <div className="segment-meta">
                      <span>利润 {formatYi(segment.profitYi)}</span>
                      <span>利润占比 {formatPercent(segment.profitRatio)}</span>
                    </div>
                    <p className="distribution-caption">毛利率 {formatPercent(segment.grossMargin)}</p>
                  </article>
                ))}
              </div>
            ) : (
              <p className="detail-empty">暂无会计主营拆分数据。</p>
            )}
          </section>

          <section className="detail-section">
            <div className="distribution-header">
              <div>
                <p className="section-label">业务主营</p>
                <strong>{insight.officialBusiness.companyName || `${stock.name} 公司资料`}</strong>
              </div>
              <span className="distribution-pill balanced">
                {insight.officialBusiness.industry || "行业未识别"}
              </span>
            </div>

            <div className="detail-text-grid">
              <article className="detail-text-card">
                <p className="section-label">主营业务</p>
                <p>{insight.officialBusiness.mainBusiness || "暂无主营业务摘要"}</p>
              </article>
              <article className="detail-text-card">
                <p className="section-label">经营范围</p>
                <p>{insight.officialBusiness.businessScope || "暂无经营范围摘要"}</p>
              </article>
              <article className="detail-text-card wide">
                <p className="section-label">机构简介</p>
                <p>{insight.officialBusiness.companyIntro || "暂无机构简介"}</p>
              </article>
            </div>
          </section>

          <section className="detail-section">
            <div className="distribution-header">
              <div>
                <p className="section-label">新闻与政策敏感度</p>
                <strong>{insight.newsSensitivity.summary}</strong>
              </div>
              <span className={`distribution-pill ${insightLevelTone(insight.newsSensitivity.level)}`}>
              得分 {insight.newsSensitivity.score}
              </span>
            </div>

            {insight.newsSensitivity.matchedKeywords.length > 0 ? (
              <div className="detail-chip-row">
                {insight.newsSensitivity.matchedKeywords.map((keyword) => (
                  <span className="detail-chip" key={`${stock.symbol}-news-${keyword}`}>
                    {keyword}
                  </span>
                ))}
              </div>
            ) : null}

            {insight.newsSensitivity.items.length > 0 ? (
              <div className="detail-list">
                {insight.newsSensitivity.items.map((item, index) => (
                  <article className="detail-list-card" key={`${stock.symbol}-news-item-${index}`}>
                    <div className="detail-list-header">
                      <div>
                        <h3>{item.title}</h3>
                        <p className="detail-list-meta">
                          {item.source || "未知来源"} · {item.publishTime || "时间未披露"}
                        </p>
                      </div>
                      {item.url ? (
                        <button
                          className="meta-link-button secondary"
                          type="button"
                          onClick={() => {
                            void onOpenLink(item.url);
                          }}
                        >
                          查看原文
                        </button>
                      ) : null}
                    </div>
                    <p className="distribution-caption">{item.excerpt || "暂无正文摘要"}</p>
                    {item.matchedKeywords.length > 0 ? (
                      <div className="detail-chip-row">
                        {item.matchedKeywords.map((keyword) => (
                          <span className="detail-chip subtle" key={`${stock.symbol}-news-hit-${index}-${keyword}`}>
                            {keyword}
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </article>
                ))}
              </div>
            ) : (
              <p className="detail-empty">暂无新闻样本。</p>
            )}
          </section>

          <section className="detail-section">
            <div className="distribution-header">
              <div>
                <p className="section-label">投资方主营</p>
                <strong>{insight.researchFocus.summary}</strong>
              </div>
              <span className="distribution-pill balanced">
                研报 {insight.researchFocus.monthlyReportCount}
              </span>
            </div>

            {insight.researchFocus.focusKeywords.length > 0 ? (
              <div className="detail-chip-row">
                {insight.researchFocus.focusKeywords.map((keyword) => (
                  <span className="detail-chip" key={`${stock.symbol}-research-${keyword}`}>
                    {keyword}
                  </span>
                ))}
              </div>
            ) : null}

            {insight.researchFocus.items.length > 0 ? (
              <div className="detail-list">
                {insight.researchFocus.items.map((item, index) => (
                  <article className="detail-list-card" key={`${stock.symbol}-report-item-${index}`}>
                    <div className="detail-list-header">
                      <div>
                        <h3>{item.title || "未命名研报"}</h3>
                        <p className="detail-list-meta">
                          {item.institution || "机构未披露"} · {item.date || "日期未披露"} · {item.rating || "未披露评级"}
                        </p>
                      </div>
                      {item.reportUrl ? (
                        <button
                          className="meta-link-button secondary"
                          type="button"
                          onClick={() => {
                            void onOpenLink(item.reportUrl);
                          }}
                        >
                          打开 PDF
                        </button>
                      ) : null}
                    </div>
                    <p className="distribution-caption">{item.industry || "行业未披露"}</p>
                  </article>
                ))}
              </div>
            ) : (
              <p className="detail-empty">暂无券商研报样本。</p>
            )}
          </section>
        </div>
      </article>
    </section>
  );
}

function MarketRadarModal(props: {
  radar: MarketRadar;
  onClose: () => void;
  onOpenLink: (url: string) => Promise<void>;
}) {
  const { radar, onClose, onOpenLink } = props;

  return (
    <section className="detail-modal-backdrop" onClick={onClose} aria-label="市场联动弹窗" role="dialog" aria-modal="true">
      <article
        className="detail-modal"
        onClick={(event) => {
          event.stopPropagation();
        }}
      >
        <header className="detail-modal-header">
          <div>
            <p className="section-label">板块联动 / 美股晨报</p>
            <h2>
              市场联动观察
              <span>{radar.updatedAt || "等待刷新"}</span>
            </h2>
            <div className="detail-badges">
              <span className="detail-badge neutral">热点板块 {radar.hottestBoards.length}</span>
              <span className="detail-badge neutral">热点 ETF {radar.hottestEtfs.length}</span>
              <span className="detail-badge neutral">美股日期 {radar.usMarketPulse.tradeDate || "未刷新"}</span>
            </div>
          </div>
          <div className="detail-header-actions">
            <button className="modal-close-button" type="button" onClick={onClose}>
              关闭
            </button>
          </div>
        </header>

        <div className="detail-modal-body">
          <section className="detail-section">
            <div className="distribution-header">
              <div>
                <p className="section-label">美股晨报</p>
                <strong>{radar.usMarketPulse.summary}</strong>
              </div>
              <span className="distribution-pill balanced">{radar.usMarketPulse.tradeDate || "未刷新"}</span>
            </div>

            <div className="us-focus-grid">
              {radar.usMarketPulse.items.length > 0 ? (
                radar.usMarketPulse.items.map((item) => <UsFocusCard item={item} key={item.key} onOpenLink={onOpenLink} />)
              ) : (
                <p className="detail-empty">暂无隔夜美股晨报。</p>
              )}
            </div>
          </section>

          <section className="detail-section">
            <ThemeHotspotList title="最热板块" items={radar.hottestBoards} />
            <ThemeHotspotList title="最热 ETF" items={radar.hottestEtfs} />
          </section>
        </div>
      </article>
    </section>
  );
}

function ThemeHotspotList(props: {
  title: string;
  items: ThemeHotspot[];
}) {
  return (
    <div className="theme-hotspot-section">
      <div className="distribution-header">
        <div>
          <p className="section-label">{props.title}</p>
          <strong>{props.items.length > 0 ? "优先关注最强映射" : "暂无样本"}</strong>
        </div>
      </div>

      {props.items.length > 0 ? (
        <div className="detail-list">
          {props.items.map((item) => (
            <article className="detail-list-card" key={`${item.boardType}-${item.code || item.name}`}>
              <div className="detail-list-header">
                <div>
                  <h3>{item.name}</h3>
                  <p className="detail-list-meta">
                    {item.boardType === "industry" ? "行业" : item.boardType === "concept" ? "概念" : "ETF"} · {item.matchReason || "热度匹配"}
                  </p>
                </div>
                <span className={`distribution-pill ${hotspotTone(item.changePct)}`}>{formatSigned(item.changePct)}%</span>
              </div>
              <p className="distribution-caption">
                {item.leaderName
                  ? `龙头 ${item.leaderName} ${formatSigned(item.leaderChangePct)}% · 上涨家数 ${item.riseCount} / 下跌家数 ${item.fallCount}`
                  : item.code
                    ? `代码 ${item.code}`
                    : "暂无龙头信息"}
              </p>
            </article>
          ))}
        </div>
      ) : (
        <p className="detail-empty">暂无相关热点。</p>
      )}
    </div>
  );
}

function UsFocusCard(props: {
  item: UsFocusItem;
  onOpenLink: (url: string) => Promise<void>;
}) {
  const topNews = props.item.news.slice(0, 2);

  return (
    <article className={`us-focus-card ${props.item.tone}`}>
      <div className="detail-list-header">
        <div>
          <p className="section-label">{props.item.category}</p>
          <h3>{props.item.name}</h3>
          <p className="detail-list-meta">
            {props.item.symbol || "新闻跟踪"} · {props.item.lastTradeDate || "未刷新"}
          </p>
        </div>
        <span className={`distribution-pill ${hotspotTone(props.item.changePct)}`}>
          {props.item.symbol ? `${formatSigned(props.item.changePct)}%` : "新闻"}
        </span>
      </div>

      {props.item.symbol ? (
        <div className="distribution-meta">
          <span>收盘 {props.item.close.toFixed(2)}</span>
          <span>前收 {props.item.prevClose.toFixed(2)}</span>
          <span>高低 {props.item.high.toFixed(2)} / {props.item.low.toFixed(2)}</span>
        </div>
      ) : null}

      <p className="distribution-caption">{props.item.summary}</p>

      {topNews.length > 0 ? (
        <div className="detail-list">
          {topNews.map((news, index) => (
            <article className="detail-list-card compact" key={`${props.item.key}-news-${index}`}>
              <div className="detail-list-header">
                <div>
                  <h3>{news.title}</h3>
                  <p className="detail-list-meta">
                    {news.source || "未知来源"} · {news.publishTime || "时间未披露"}
                  </p>
                </div>
                {news.url ? (
                  <button
                    className="meta-link-button secondary"
                    type="button"
                    onClick={() => {
                      void props.onOpenLink(news.url);
                    }}
                  >
                    打开
                  </button>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </article>
  );
}

function CyclePanel(props: { analysis: CycleAnalysis; compact?: boolean }) {
  const { analysis, compact = false } = props;
  const pivotRows = buildPivotRows(analysis);
  const cycleWindows = buildRecentCycleWindows(analysis);
  return (
    <section className={`cycle-panel${compact ? " compact" : ""}`}>
      <div className="distribution-header">
        <div>
          <p className="section-label">波峰波谷周期</p>
          <strong>{analysis.recommendation}</strong>
        </div>
        <span className={`distribution-pill ${cycleTone(analysis.level)}`}>
          {analysis.level} · {analysis.score}
        </span>
      </div>

      <div className={`cycle-opportunity-card regime-card ${analysis.regime.tone}`}>
        <div className="cycle-opportunity-header">
          <div>
            <p className="section-label">当前状态区</p>
            <strong>{analysis.regime.label}</strong>
          </div>
          <span className={`distribution-pill ${analysis.regime.tone}`}>{analysis.regime.actionLabel}</span>
        </div>
        <div className="cycle-meta-row">
          <span>起点 {analysis.regime.sinceDate || "未识别"}</span>
          <span>
            区间 {analysis.regime.rangeLow.toFixed(2)} - {analysis.regime.rangeHigh.toFixed(2)}
          </span>
          <span>当前位置 {analysis.regime.currentPositionPct.toFixed(1)}%</span>
        </div>
        <div className="cycle-meta-row">
          <span>振幅倍率 {analysis.regime.amplitudeRatio.toFixed(2)}x</span>
          <span>流动性倍率 {analysis.regime.liquidityRatio.toFixed(2)}x</span>
          <span>近期波段 {analysis.regime.recentSwingCount}</span>
        </div>
        <p className="distribution-caption">{analysis.regime.summary}</p>
      </div>

      <div className={`cycle-opportunity-card ${analysis.opportunity.tone}`}>
        <div className="cycle-opportunity-header">
          <div>
            <p className="section-label">市场温度</p>
            <strong>{analysis.opportunity.phaseLabel}</strong>
          </div>
          <span className={`distribution-pill ${analysis.opportunity.tone}`}>{analysis.opportunity.actionLabel}</span>
        </div>
        <div className="cycle-meta-row">
          <span>支撑 {analysis.opportunity.supportPrice.toFixed(2)} · {analysis.opportunity.supportDate || "未识别"}</span>
          <span>压力 {analysis.opportunity.resistancePrice.toFixed(2)} · {analysis.opportunity.resistanceDate || "未识别"}</span>
        </div>
        <div className="cycle-meta-row">
          <span>距支撑 {formatSigned(analysis.opportunity.distanceToSupportPct)}%</span>
          <span>距压力 {formatSigned(analysis.opportunity.distanceToResistancePct)}%</span>
          <span>当前价 {analysis.opportunity.currentPrice.toFixed(2)}</span>
        </div>
        <p className="distribution-caption">{analysis.opportunity.summary}</p>
      </div>

      <div className="cycle-metric-grid">
        <span>拐点 {analysis.pivotCount}</span>
        <span>波段 {analysis.swingCount}</span>
        <span>平均上涨 {analysis.avgUpDays.toFixed(1)} 天</span>
        <span>平均下跌 {analysis.avgDownDays.toFixed(1)} 天</span>
        <span>平均上涨幅度 {formatSigned(analysis.avgUpReturnPct)}%</span>
        <span>平均下跌幅度 {formatSigned(analysis.avgDownReturnPct)}%</span>
      </div>

      <div className="cycle-meta-row">
        <span>节奏离散 {analysis.durationCv.toFixed(2)}</span>
        <span>幅度离散 {analysis.amplitudeCv.toFixed(2)}</span>
        {analysis.startDate && analysis.endDate ? (
          <span>
            区间 {analysis.startDate} 至 {analysis.endDate}
          </span>
        ) : null}
      </div>

      <p className="distribution-caption">{analysis.latestState}</p>

      {cycleWindows.length > 0 ? (
        <div className={`cycle-window-grid${compact ? " compact" : ""}`}>
          {cycleWindows.map((window) => (
            <article key={`${window.label}-${window.startDate}-${window.endDate}`} className={`cycle-window-card ${window.direction}`}>
              <div className="cycle-window-header">
                <strong>{window.label}</strong>
                <span>{window.direction === "up" ? "上涨" : "下跌"}</span>
              </div>
              <p>{window.startDate} 至 {window.endDate || analysis.opportunity.currentPrice.toFixed(2)}</p>
              <div className="cycle-window-meta">
                <span>{window.tradingDays} 天</span>
                <span>{formatSigned(window.returnPct)}%</span>
                <span>{window.status === "ongoing" ? "进行中" : "已完成"}</span>
              </div>
            </article>
          ))}
        </div>
      ) : null}

      {!compact ? (
        <>
          <CyclePhaseChart analysis={analysis} />
          <div className="cycle-pivot-section">
            <div className="distribution-header">
              <div>
                <p className="section-label">关键拐点表</p>
                <strong>最近 6 个关键拐点</strong>
              </div>
            </div>
            <div className="cycle-pivot-table-wrap">
              <table className="cycle-pivot-table">
                <thead>
                  <tr>
                    <th>日期</th>
                    <th>类型</th>
                    <th>价格</th>
                    <th>相对前点</th>
                    <th>间隔</th>
                  </tr>
                </thead>
                <tbody>
                  {pivotRows.map((row) => (
                    <tr key={`${row.date}-${row.kind}`}>
                      <td>{row.date}</td>
                      <td>{row.kind}</td>
                      <td>{row.price}</td>
                      <td>{row.changePct}</td>
                      <td>{row.gapDays}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : null}
    </section>
  );
}

function CyclePhaseChart(props: { analysis: CycleAnalysis }) {
  const points = buildCycleChartPoints(props.analysis);
  if (points.length < 2) {
    return null;
  }

  const width = 420;
  const height = 180;
  const pointString = points.map((point) => `${point.x},${point.y}`).join(" ");

  return (
    <div className="cycle-phase-chart">
      <div className="distribution-header">
        <div>
          <p className="section-label">阶段波段图</p>
          <strong>关键拐点连接后的阶段路径</strong>
        </div>
      </div>
      <svg className="cycle-svg" viewBox={`0 0 ${width} ${height}`} role="img">
        <polyline className="cycle-svg-line" points={pointString} />
        {points.map((point) => (
          <g key={`${point.label}-${point.x}`}>
            <circle className={`cycle-svg-dot ${point.kind}`} cx={point.x} cy={point.y} r={point.kind === "current" ? 5 : 4} />
            <text className="cycle-svg-text" x={point.x} y={point.y - 10} textAnchor="middle">
              {point.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

function buildPivotRows(analysis: CycleAnalysis) {
  const recent = analysis.pivots.slice(-6);
  const offset = analysis.pivots.length - recent.length;
  return recent
    .map((pivot, index) => {
      const previous = offset + index > 0 ? analysis.pivots[offset + index - 1] : undefined;
      const previousPrice = previous?.price ?? pivot.price;
      const changePct = previous ? `${formatSigned(((pivot.price / previousPrice) - 1) * 100)}%` : "首个拐点";
      const gapDays = previous ? `${Math.max(1, pivot.index - previous.index)} 天` : "-";
      return {
        date: pivot.date,
        kind: pivot.kind === "high" ? "波峰" : "波谷",
        price: pivot.price.toFixed(2),
        changePct,
        gapDays
      };
    })
    .reverse();
}

function buildCycleChartPoints(analysis: CycleAnalysis) {
  const pivots = analysis.pivots.slice(-8);
  const basePoints = pivots.map((pivot) => ({
    key: `${pivot.date}-${pivot.kind}`,
    label: pivot.kind === "high" ? "H" : "L",
    kind: pivot.kind as "high" | "low",
    date: pivot.date,
    index: pivot.index,
    price: pivot.price
  }));
  const currentIndex = (pivots[pivots.length - 1]?.index ?? 0) + 8;
  const currentPoint = {
    key: `${analysis.opportunity.currentDate}-current`,
    label: "Now",
    kind: "current" as const,
    date: analysis.opportunity.currentDate,
    index: currentIndex,
    price: analysis.opportunity.currentPrice
  };
  const rawPoints = [...basePoints, currentPoint];

  const prices = rawPoints.map((point) => point.price);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const priceSpan = maxPrice - minPrice || 1;
  const xSpan = Math.max(rawPoints.length - 1, 1);

  return rawPoints.map((point, index) => ({
    ...point,
    x: 18 + (index / xSpan) * 384,
    y: 150 - ((point.price - minPrice) / priceSpan) * 112
  }));
}

function buildRecentCycleWindows(analysis: CycleAnalysis): CycleWindow[] {
  const completed = analysis.recentCycles
    .filter((item) => item.startDate && item.endDate)
    .slice(-2)
    .map((item, index, items) => ({
      ...item,
      label: items.length === 1 ? "完整周期" : `完整周期 ${index + 1}`
    }));

  if (analysis.currentCycle?.startDate) {
    return [
      ...completed,
      {
        ...analysis.currentCycle,
        label: "当前周期"
      }
    ];
  }

  return completed;
}

function getCycleDisplayStartDate(cycle: CycleAnalysis | undefined, candles: CandlePoint[]): string {
  if (!cycle) {
    return candles[Math.max(0, candles.length - 48)]?.date ?? "";
  }

  const cycleWindows = buildRecentCycleWindows(cycle);
  const firstWindow = cycleWindows[0];
  if (firstWindow?.startDate) {
    return firstWindow.startDate;
  }

  return candles[Math.max(0, candles.length - 48)]?.date ?? "";
}

function TechnicalsPanel(props: { profile: TechnicalIndicators }) {
  return (
    <section className="technical-panel">
      <div className="distribution-header">
        <div>
          <p className="section-label">技术监测</p>
          <strong>MACD 与 RSI 日线状态</strong>
        </div>
      </div>

      <div className="technical-grid">
        <article className={`technical-card ${props.profile.macd.tone}`}>
          <p className="section-label">MACD (10,200,7)</p>
          <strong>{props.profile.macd.signalLabel}</strong>
          <div className="technical-values">
            <span>DIF {formatSignedCompact(props.profile.macd.dif)}</span>
            <span>DEA {formatSignedCompact(props.profile.macd.dea)}</span>
            <span>柱体 {formatSignedCompact(props.profile.macd.histogram)}</span>
          </div>
          <p className="technical-caption">{props.profile.macd.biasLabel}</p>
        </article>

        <article className={`technical-card ${props.profile.rsi14.tone}`}>
          <p className="section-label">RSI ({props.profile.rsi14.period})</p>
          <strong>{props.profile.rsi14.signalLabel}</strong>
          <div className="technical-values">
            <span>当前 {props.profile.rsi14.value.toFixed(1)}</span>
            <span>阈值 50 / 80</span>
          </div>
          <p className="technical-caption">{props.profile.rsi14.biasLabel}</p>
        </article>
      </div>
    </section>
  );
}

function ChipDistributionDetail(props: { profile: ChipDistributionProfile; currentPrice: number }) {
  const { profile, currentPrice } = props;
  const topBands = [...profile.bands]
    .sort((left, right) => right.ratio - left.ratio)
    .slice(0, 12);
  const maxRatio = topBands[0]?.ratio ?? 0;

  return (
    <section className="detail-section">
      <div className="distribution-header">
        <div>
          <p className="section-label">主力筹码成本</p>
          <strong>{profile.summary}</strong>
        </div>
        <span className="distribution-pill balanced">
          {profile.tradeDate || "等待刷新"}
        </span>
      </div>

      <div className="detail-chip-row">
        <span className={`detail-chip ${profile.tone === "positive" ? "positive" : profile.tone === "negative" ? "negative" : profile.tone === "alert" ? "alert" : "subtle"}`}>
          筹码 {profile.shapeLabel}
        </span>
        <span className="detail-chip subtle">阶段 {profile.stageLabel}</span>
        <span className={`detail-chip ${profile.tone === "positive" ? "positive" : profile.tone === "negative" ? "negative" : profile.tone === "alert" ? "alert" : "subtle"}`}>
          {profile.riskLabel}
        </span>
      </div>

      <div className="detail-text-grid">
        <article className="detail-text-card">
          <p className="section-label">主力成本</p>
          <p>{profile.mainCost.toFixed(2)}</p>
        </article>
        <article className="detail-text-card">
          <p className="section-label">主力成本区</p>
          <p>{profile.mainCostZoneLow.toFixed(2)} - {profile.mainCostZoneHigh.toFixed(2)}</p>
        </article>
        <article className="detail-text-card">
          <p className="section-label">成本区宽度</p>
          <p>{profile.mainCostZoneWidthPct.toFixed(1)}%</p>
        </article>
        <article className="detail-text-card">
          <p className="section-label">平均成本</p>
          <p>{profile.averageCost.toFixed(2)}</p>
        </article>
        <article className="detail-text-card">
          <p className="section-label">获利盘</p>
          <p>{formatPercent(profile.winnerRatio)}</p>
        </article>
        <article className="detail-text-card">
          <p className="section-label">价格偏差</p>
          <p>{formatSigned(profile.currentPriceBiasPct)}%</p>
        </article>
        <article className="detail-text-card">
          <p className="section-label">70% 筹码区</p>
          <p>{profile.concentration70Low.toFixed(2)} - {profile.concentration70High.toFixed(2)}</p>
        </article>
        <article className="detail-text-card">
          <p className="section-label">90% 筹码区</p>
          <p>{profile.concentration90Low.toFixed(2)} - {profile.concentration90High.toFixed(2)}</p>
        </article>
      </div>

      {profile.controlEvidence.length > 0 ? (
        <div className="chip-evidence-grid">
          {profile.controlEvidence.map((item) => (
            <ChipEvidenceCard key={`${item.key}-${item.label}`} item={item} />
          ))}
        </div>
      ) : null}

      {topBands.length > 0 ? (
        <div className="chip-cost-list">
          {topBands.map((band) => {
            const isMainCost = Math.abs(band.price - profile.mainCost) <= profile.bucketSize / 2 + 0.0001;
            const isNearCurrent = Math.abs(band.price - currentPrice) <= profile.bucketSize / 2 + 0.0001;
            const isInMainZone = band.price >= profile.mainCostZoneLow - 0.0001 && band.price <= profile.mainCostZoneHigh + 0.0001;
            return (
              <div className={`chip-cost-row ${isInMainZone ? "zone" : ""}`} key={`${profile.tradeDate}-${band.price}`}>
                <span className={`chip-cost-price ${isMainCost ? "main" : isNearCurrent ? "current" : ""}`}>
                  {band.price.toFixed(2)}
                </span>
                <div className="chip-cost-bar-track">
                  <div
                    className={`chip-cost-bar ${isMainCost ? "main" : isNearCurrent ? "current" : isInMainZone ? "zone" : ""}`}
                    style={{ width: `${maxRatio > 0 ? (band.ratio / maxRatio) * 100 : 0}%` }}
                  />
                </div>
                <span className="chip-cost-ratio">{formatPercent(band.ratio)}</span>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="detail-empty">暂无相关热点。</p>
      )}
      <p className="distribution-caption">
        金黄色是主力成本峰，浅绿色是当前价格，蓝色区间是主力成本区      </p>
    </section>
  );
}

function ChipEvidenceCard(props: { item: ChipControlEvidence }) {
  const { item } = props;

  return (
    <article className={`chip-evidence-card ${item.tone}`}>
      <p className="chip-evidence-label">{item.label}</p>
      <strong className="chip-evidence-value">{item.value}</strong>
      <p className="chip-evidence-summary">{item.summary}</p>
    </article>
  );
}

function PriceBattery(props: { profile: PriceDistributionProfile; currentPrice: number }) {
  const summary = describeDistribution(props.profile);
  const currentBand = props.profile.bands[props.profile.currentBand];

  return (
    <section className="distribution-panel">
      <div className="distribution-header">
        <div>
          <p className="section-label">年内价格电量</p>
          <strong>{summary.title}</strong>
        </div>
        <span className={`distribution-pill ${summary.tone}`}>第 {props.profile.currentBand + 1} / 6 档</span>
      </div>

      <div
        className="battery-shell"
        aria-label={`当前价格 ${props.currentPrice.toFixed(2)}，位于年内第 ${props.profile.currentBand + 1} 档`}
      >
        <div className="battery-body">
          {props.profile.bands.map((band) => {
            const fillLevel = `${Math.max(10, Math.round(band.ratio * 100))}%`;
            const cellStyle = { "--fill-level": fillLevel } as CSSProperties;
            const isCurrent = band.index === props.profile.currentBand;
            const isDominant = band.index === props.profile.dominantBand;

            return (
              <div
                key={`${band.index}-${band.rangeLabel}`}
                className={["battery-cell", isCurrent ? "current" : "", isDominant ? "dominant" : ""].filter(Boolean).join(" ")}
                style={cellStyle}
                title={`第 ${band.index + 1} 档：${band.rangeLabel}，收盘出现 ${band.closeCount} 天`}
              >
                <span className="sr-only">
                  {`第 ${band.index + 1} 档，区间 ${band.rangeLabel}，收盘出现 ${band.closeCount} 天`}
                </span>
                <div className="battery-cell-fill" />
              </div>
            );
          })}
        </div>
        <div className="battery-cap" />
      </div>

      <div className="distribution-scale">
        <span>低位 {props.profile.yearLow.toFixed(2)}</span>
        <span>高位 {props.profile.yearHigh.toFixed(2)}</span>
      </div>

      <div className="distribution-meta">
        <span>样本 {props.profile.sampleSize} 天</span>
        <span>年内位置 {Math.round(props.profile.currentPositionPct * 100)}%</span>
        <span>当前档 {currentBand?.closeCount ?? 0} 天</span>
      </div>

      <p className="distribution-caption">
        金黄色是主力成本峰，浅绿色是当前价格，蓝色区间是主力成本区      </p>
    </section>
  );
}

function AmplitudeDistributionPanel(props: { profile: AmplitudeDistributionProfile }) {
  const summary = describeAmplitudeDistribution(props.profile);

  return (
    <section className="amplitude-panel">
      <div className="distribution-header">
        <div>
          <p className="section-label">振幅分布</p>
          <strong>{summary.title}</strong>
        </div>
        <span className={`distribution-pill ${summary.tone}`}>当前 {props.profile.currentBand + 1} / 6 档</span>
      </div>

      <div className="amplitude-meta">
        <span>{props.profile.boardType}</span>
        <span>{props.profile.marketCapBucket}</span>
        <span>估算市值 {props.profile.marketCapYi.toFixed(0)} 亿</span>
      </div>

      <div className="amplitude-bars" aria-label={`当前振幅 ${props.profile.currentAmplitude.toFixed(2)}%，所在第 ${props.profile.currentBand + 1} 档`}>
        {props.profile.bands.map((band) => {
          const fillHeight = `${Math.max(12, Math.round(band.ratio * 100))}%`;
          const barStyle = { "--bar-height": fillHeight } as CSSProperties;
          const isCurrent = band.index === props.profile.currentBand;
          const isDominant = band.index === props.profile.dominantBand;

          return (
          <div className="amplitude-bar-wrap" key={`${band.index}-${band.rangeLabel}`} title={`${band.rangeLabel}，出现 ${band.closeCount} 天`}>
              <div
                className={["amplitude-bar", isCurrent ? "current" : "", isDominant ? "dominant" : ""].filter(Boolean).join(" ")}
                style={barStyle}
              >
                <div className="amplitude-bar-fill" />
              </div>
              <span className="amplitude-label">{band.rangeLabel}</span>
            </div>
          );
        })}
      </div>

      <div className="distribution-meta">
        <span>样本 {props.profile.sampleSize} 天</span>
        <span>当前第 {props.profile.currentBand + 1} 档</span>
        <span>最大振幅上限 {props.profile.amplitudeCap.toFixed(0)}%</span>
      </div>

      <p className="distribution-caption">
        金黄色是主力成本峰，浅绿色是当前价格，蓝色区间是主力成本区      </p>
    </section>
  );
}

function SignalTag(props: { label: string; level: SignalLevel }) {
  return <span className={`signal-tag ${props.level}`}>{props.label}</span>;
}

function CandlestickChart({
  candles,
  bollinger,
  limitUpSignal,
  cycle
}: {
  candles: CandlePoint[];
  bollinger: BollingerProfile;
  limitUpSignal: WatchStock["limitUpSignal"];
  cycle?: CycleAnalysis;
}) {
  const width = 320;
  const height = 88;
  const displayStartDate = getCycleDisplayStartDate(cycle, candles);
  const safeCandles = candles.filter((item) => (
    Number.isFinite(item.open) &&
    Number.isFinite(item.high) &&
    Number.isFinite(item.low) &&
    Number.isFinite(item.close) &&
    (!displayStartDate || item.date >= displayStartDate)
  ));

  if (safeCandles.length === 0) {
    return null;
  }

  const candleDateSet = new Set(safeCandles.map((item) => item.date));
  const safeBands = bollinger.points.filter((item) => (
    Number.isFinite(item.middle) &&
    Number.isFinite(item.upper) &&
    Number.isFinite(item.lower) &&
    candleDateSet.has(item.date)
  ));
  const rangeValues = [
    ...safeCandles.flatMap((item) => [item.low, item.high]),
    ...safeBands.flatMap((item) => [item.lower, item.middle, item.upper])
  ];
  if (limitUpSignal.isHoldingAboveOpen && limitUpSignal.anchorOpen > 0) {
    rangeValues.push(limitUpSignal.anchorOpen);
  }
  const min = Math.min(...rangeValues);
  const max = Math.max(...rangeValues);
  const span = max - min || 1;
  const step = width / safeCandles.length;
  const bodyWidth = Math.max(1.6, Math.min(10, step * 0.58));
  const scaleY = (value: number) => height - ((value - min) / span) * (height - 10) - 5;
  const limitUpCloses = safeCandles.filter((item) => item.isLimitUpClose);
  const cycleWindows = cycle ? buildRecentCycleWindows(cycle) : [];
  const buildBandPath = (selector: (point: typeof safeBands[number]) => number) => safeBands
    .map((item, index) => {
      const centerX = index * step + step / 2;
      return `${centerX},${scaleY(selector(item))}`;
    })
    .join(" ");
  const cycleMarkers = cycleWindows
    .map((item) => {
      const index = safeCandles.findIndex((candle) => candle.date >= item.startDate);
      if (index < 0) {
        return null;
      }
      return {
        ...item,
        x: index * step + step / 2
      };
    })
    .filter((item): item is CycleWindow & { x: number } => item !== null);

  return (
    <div className="sparkline-wrap candlestick-wrap" aria-hidden="true">
      <svg className="sparkline candlestick-chart" viewBox={`0 0 ${width} ${height}`} role="img">
        {safeBands.length > 1 ? (
          <>
            <polyline className="bollinger-line outer" points={buildBandPath((item) => item.upper)} />
            <polyline className="bollinger-line middle" points={buildBandPath((item) => item.middle)} />
            <polyline className="bollinger-line outer" points={buildBandPath((item) => item.lower)} />
          </>
        ) : null}
        {cycleMarkers.map((item) => (
          <g key={`cycle-marker-${item.label}-${item.startDate}`}>
            <line className="cycle-marker-line" x1={item.x} x2={item.x} y1="5" y2={height - 6} />
          </g>
        ))}
        {limitUpSignal.isHoldingAboveOpen && limitUpSignal.anchorOpen > 0 ? (
          <g>
            <line className="limit-anchor-line" x1="6" x2={width - 6} y1={scaleY(limitUpSignal.anchorOpen)} y2={scaleY(limitUpSignal.anchorOpen)} />
            <text className="limit-anchor-text" x={width - 8} y={Math.max(10, scaleY(limitUpSignal.anchorOpen) - 4)} textAnchor="end">
              瀹堝紑 {limitUpSignal.anchorOpen.toFixed(2)}
            </text>
          </g>
        ) : null}
        {limitUpCloses.map((item) => {
          const lineY = scaleY(item.close);
          return (
            <g key={`limit-up-${item.date}-${item.close}`}>
              <line className="limit-up-line" x1="6" x2={width - 6} y1={lineY} y2={lineY} />
              <text className="limit-up-text" x={width - 8} y={Math.max(10, lineY - 4)} textAnchor="end">
                涨停 {item.close.toFixed(2)}
              </text>
            </g>
          );
        })}
        {safeCandles.map((item, index) => {
          const centerX = index * step + step / 2;
          const highY = scaleY(item.high);
          const lowY = scaleY(item.low);
          const openY = scaleY(item.open);
          const closeY = scaleY(item.close);
          const top = Math.min(openY, closeY);
          const bodyHeight = Math.max(2, Math.abs(openY - closeY));
          const tone = item.close >= item.open ? "up" : "down";

          return (
            <g key={`${item.date}-${index}`} className={`candlestick ${tone}`}>
              <line className="candlestick-wick" x1={centerX} x2={centerX} y1={highY} y2={lowY} />
              <rect
                className="candlestick-body"
                x={centerX - bodyWidth / 2}
                y={top}
                width={bodyWidth}
                height={bodyHeight}
                rx="1.5"
              />
            </g>
          );
        })}
      </svg>
      <div className="candlestick-indicator-tag">
        BOLL(30,2){limitUpCloses.length > 0 ? " / 涨停线" : ""}{limitUpSignal.isHoldingAboveOpen ? " / 守开线" : ""}
      </div>
      {cycleWindows.length > 0 ? (
        <div className="candlestick-cycle-meta">
          {cycleWindows.map((item) => (
            <span key={`${item.label}-${item.startDate}`} className={`candlestick-cycle-pill ${item.direction}`}>
              {item.label} {item.tradingDays}天 / {formatSigned(item.returnPct)}%
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function resolveCompanyInsight(value: CompanyInsight | undefined): CompanyInsight {
  const fallback = createDefaultCompanyInsight();
  if (!value || typeof value !== "object") {
    return fallback;
  }

  return {
    updatedAt: typeof value.updatedAt === "string" ? value.updatedAt : "",
    accountingBusiness: {
      ...fallback.accountingBusiness,
      ...(value.accountingBusiness ?? {}),
      segments: Array.isArray(value.accountingBusiness?.segments) ? value.accountingBusiness.segments : []
    },
    officialBusiness: {
      ...fallback.officialBusiness,
      ...(value.officialBusiness ?? {})
    },
    newsSensitivity: {
      ...fallback.newsSensitivity,
      ...(value.newsSensitivity ?? {}),
      matchedKeywords: Array.isArray(value.newsSensitivity?.matchedKeywords) ? value.newsSensitivity.matchedKeywords : [],
      items: Array.isArray(value.newsSensitivity?.items) ? value.newsSensitivity.items : []
    },
    researchFocus: {
      ...fallback.researchFocus,
      ...(value.researchFocus ?? {}),
      focusKeywords: Array.isArray(value.researchFocus?.focusKeywords) ? value.researchFocus.focusKeywords : [],
      items: Array.isArray(value.researchFocus?.items) ? value.researchFocus.items : []
    }
  };
}

function resolveThemeHotspot(value: ThemeHotspot | undefined): ThemeHotspot {
  return {
    boardType: value?.boardType === "industry" || value?.boardType === "etf" ? value.boardType : "concept",
    name: typeof value?.name === "string" ? value.name : "",
    code: typeof value?.code === "string" ? value.code : "",
    rank: typeof value?.rank === "number" ? value.rank : 0,
    changePct: typeof value?.changePct === "number" ? value.changePct : 0,
    riseCount: typeof value?.riseCount === "number" ? value.riseCount : 0,
    fallCount: typeof value?.fallCount === "number" ? value.fallCount : 0,
    leaderName: typeof value?.leaderName === "string" ? value.leaderName : "",
    leaderCode: typeof value?.leaderCode === "string" ? value.leaderCode : "",
    leaderChangePct: typeof value?.leaderChangePct === "number" ? value.leaderChangePct : 0,
    matchReason: typeof value?.matchReason === "string" ? value.matchReason : ""
  };
}

function resolveThemeLinkage(value: WatchStock["themeLinkage"]) {
  return {
    updatedAt: typeof value?.updatedAt === "string" ? value.updatedAt : "",
    industry: typeof value?.industry === "string" ? value.industry : "",
    concepts: Array.isArray(value?.concepts) ? value.concepts.filter((item): item is string => typeof item === "string") : [],
    matchedKeywords: Array.isArray(value?.matchedKeywords)
      ? value.matchedKeywords.filter((item): item is string => typeof item === "string")
      : [],
    hotBoards: Array.isArray(value?.hotBoards) ? value.hotBoards.map((item) => resolveThemeHotspot(item)) : [],
    relatedEtfs: Array.isArray(value?.relatedEtfs) ? value.relatedEtfs.map((item) => resolveThemeHotspot(item)) : [],
    summary: typeof value?.summary === "string" ? value.summary : "暂无板块联动结果"
  };
}

function getRecentLimitUpStats(stock: WatchStock) {
  const recentCandles = stock.candles.slice(-10);
  let latestIndex = -1;

  recentCandles.forEach((item, index) => {
    if (!item.isLimitUpClose) {
      return;
    }
    latestIndex = index;
  });

  const derivedCount = recentCandles.filter((item) => item.isLimitUpClose).length;
  const count = typeof stock.limitUpSignal?.recentLimitUpCount10 === "number"
    ? stock.limitUpSignal.recentLimitUpCount10
    : derivedCount;

  return {
    count,
    latestDaysAgo: latestIndex >= 0 ? recentCandles.length - 1 - latestIndex : Number.POSITIVE_INFINITY,
    hasHoldingAboveOpen: stock.limitUpSignal?.isHoldingAboveOpen === true,
    holdDays: typeof stock.limitUpSignal?.holdDays === "number" ? stock.limitUpSignal.holdDays : 0
  };
}

function sortStocksByRecentLimitUp(stocks: WatchStock[]) {
  return [...stocks].sort((left, right) => {
    const leftStats = getRecentLimitUpStats(left);
    const rightStats = getRecentLimitUpStats(right);
    if (leftStats.hasHoldingAboveOpen !== rightStats.hasHoldingAboveOpen) {
      return Number(rightStats.hasHoldingAboveOpen) - Number(leftStats.hasHoldingAboveOpen);
    }
    if (rightStats.hasHoldingAboveOpen && leftStats.hasHoldingAboveOpen && rightStats.holdDays !== leftStats.holdDays) {
      return rightStats.holdDays - leftStats.holdDays;
    }
    if (rightStats.count !== leftStats.count) {
      return rightStats.count - leftStats.count;
    }
    if (leftStats.latestDaysAgo !== rightStats.latestDaysAgo) {
      return leftStats.latestDaysAgo - rightStats.latestDaysAgo;
    }
    if (right.changePct !== left.changePct) {
      return right.changePct - left.changePct;
    }
    if (right.selectionScore.total !== left.selectionScore.total) {
      return right.selectionScore.total - left.selectionScore.total;
    }
    return left.symbol.localeCompare(right.symbol);
  });
}

function buildDisplayThemes(themeLinkage: ReturnType<typeof resolveThemeLinkage>) {
  const items: Array<{ label: string; value: string; tone: string }> = [];

  if (themeLinkage.industry) {
    items.push({ label: "琛屼笟", value: themeLinkage.industry, tone: "balanced" });
  }

  themeLinkage.concepts.slice(0, 3).forEach((concept, index) => {
    items.push({
      label: index === 0 ? "姒傚康" : "椋庢牸",
      value: concept,
      tone: index === 0 ? "alert" : "neutral"
    });
  });

  return items.slice(0, 4);
}

function resolveUsFocusItem(value: UsFocusItem | undefined): UsFocusItem {
  return {
    key: typeof value?.key === "string" ? value.key : "",
    name: typeof value?.name === "string" ? value.name : "",
    symbol: typeof value?.symbol === "string" ? value.symbol : "",
    category: typeof value?.category === "string" ? value.category : "",
    lastTradeDate: typeof value?.lastTradeDate === "string" ? value.lastTradeDate : "",
    close: typeof value?.close === "number" ? value.close : 0,
    prevClose: typeof value?.prevClose === "number" ? value.prevClose : 0,
    changePct: typeof value?.changePct === "number" ? value.changePct : 0,
    high: typeof value?.high === "number" ? value.high : 0,
    low: typeof value?.low === "number" ? value.low : 0,
    volume: typeof value?.volume === "number" ? value.volume : 0,
    tone: value?.tone === "positive" || value?.tone === "negative" || value?.tone === "alert" ? value.tone : "neutral",
    summary: typeof value?.summary === "string" ? value.summary : "暂无隔夜摘要",
    news: Array.isArray(value?.news) ? value.news : []
  };
}

function resolveMarketRadar(value: DashboardSnapshot["marketRadar"]): MarketRadar {
  return {
    updatedAt: typeof value?.updatedAt === "string" ? value.updatedAt : "",
    hottestBoards: Array.isArray(value?.hottestBoards) ? value.hottestBoards.map((item) => resolveThemeHotspot(item)) : [],
    hottestEtfs: Array.isArray(value?.hottestEtfs) ? value.hottestEtfs.map((item) => resolveThemeHotspot(item)) : [],
    usMarketPulse: {
      updatedAt: typeof value?.usMarketPulse?.updatedAt === "string" ? value.usMarketPulse.updatedAt : "",
      tradeDate: typeof value?.usMarketPulse?.tradeDate === "string" ? value.usMarketPulse.tradeDate : "",
      summary: typeof value?.usMarketPulse?.summary === "string" ? value.usMarketPulse.summary : "暂无隔夜美股晨报",
      items: Array.isArray(value?.usMarketPulse?.items) ? value.usMarketPulse.items.map((item) => resolveUsFocusItem(item)) : []
    },
    marketBreadth: {
      updatedAt: typeof value?.marketBreadth?.updatedAt === "string" ? value.marketBreadth.updatedAt : "",
      tradeDate: typeof value?.marketBreadth?.tradeDate === "string" ? value.marketBreadth.tradeDate : "",
      activityPct: typeof value?.marketBreadth?.activityPct === "number" ? value.marketBreadth.activityPct : 0,
      upCount: typeof value?.marketBreadth?.upCount === "number" ? value.marketBreadth.upCount : 0,
      downCount: typeof value?.marketBreadth?.downCount === "number" ? value.marketBreadth.downCount : 0,
      flatCount: typeof value?.marketBreadth?.flatCount === "number" ? value.marketBreadth.flatCount : 0,
      limitUpCount: typeof value?.marketBreadth?.limitUpCount === "number" ? value.marketBreadth.limitUpCount : 0,
      limitDownCount: typeof value?.marketBreadth?.limitDownCount === "number" ? value.marketBreadth.limitDownCount : 0,
      netAdvance: typeof value?.marketBreadth?.netAdvance === "number" ? value.marketBreadth.netAdvance : 0,
      advanceDeclineRatio: typeof value?.marketBreadth?.advanceDeclineRatio === "number" ? value.marketBreadth.advanceDeclineRatio : 0,
      breadthLow: typeof value?.marketBreadth?.breadthLow === "number" ? value.marketBreadth.breadthLow : 0,
      breadthHigh: typeof value?.marketBreadth?.breadthHigh === "number" ? value.marketBreadth.breadthHigh : 0,
      tone: (value?.marketBreadth?.tone === "positive" || value?.marketBreadth?.tone === "negative" || value?.marketBreadth?.tone === "alert") ? value.marketBreadth.tone : "neutral",
      signalLabel: typeof value?.marketBreadth?.signalLabel === "string" ? value.marketBreadth.signalLabel : "",
      summary: typeof value?.marketBreadth?.summary === "string" ? value.marketBreadth.summary : "",
      trendPoints: Array.isArray(value?.marketBreadth?.trendPoints) ? value.marketBreadth.trendPoints : []
    }
  };
}

function describeDistribution(profile: PriceDistributionProfile) {
  const bandCount = profile.bands.length || 6;
  const averageCount = profile.sampleSize / bandCount;
  const currentCount = profile.bands[profile.currentBand]?.closeCount ?? 0;

  let zoneLabel = "中位";
  if (profile.currentBand <= 1) {
    zoneLabel = "低位";
  } else if (profile.currentBand >= bandCount - 2) {
    zoneLabel = "高位";
  }

  if (currentCount >= averageCount * 1.15) {
    return { title: zoneLabel === "中位" ? "中枢密集" : `${zoneLabel}密集`, tone: "dense" };
  }

  if (currentCount <= averageCount * 0.7) {
    return { title: zoneLabel === "中位" ? "中位偏态" : `${zoneLabel}偏态`, tone: "skewed" };
  }

  return { title: zoneLabel === "中位" ? "中位常态" : `${zoneLabel}常态`, tone: "balanced" };
}

function describeAmplitudeDistribution(profile: AmplitudeDistributionProfile) {
  const currentBand = profile.currentBand;
  const dominantBand = profile.dominantBand;
  const currentLabel = profile.bands[currentBand]?.rangeLabel ?? "0.0%-0.0%";

  if (currentBand >= dominantBand + 2) {
    return { title: `高振幅异态${currentLabel}`, tone: "skewed" };
  }

  if (currentBand <= 1 && dominantBand <= 1) {
    return { title: `浣庢尟骞呭父鎬?${currentLabel}`, tone: "balanced" };
  }

  if (currentBand === dominantBand) {
    return { title: `常见振幅${currentLabel}`, tone: "dense" };
  }

  return { title: `过渡振幅${currentLabel}`, tone: "balanced" };
}

function formatSigned(value: number) {
  return value >= 0 ? `+${value.toFixed(2)}` : value.toFixed(2);
}

function formatSignedCompact(value: number) {
  return value >= 0 ? `+${value.toFixed(3)}` : value.toFixed(3);
}

function formatMoodLabel(value: string) {
  return moodLabelMap[value] ?? value;
}

function formatMarketLabel(value: string) {
  return marketLabelMap[value] ?? value;
}

function formatSectorLabel(value: string) {
  return sectorLabelMap[value] ?? value;
}

function formatSignalLabel(value: string) {
  return signalLabelMap[value] ?? value;
}

function formatSignalValue(label: string, value: string) {
  const normalizedLabel = formatSignalLabel(label);
  if (normalizedLabel === "量比" && value.endsWith("x")) {
    return `${value.slice(0, -1)} 倍`;
  }
  return value.replace("倍", " 倍");
}

function formatNoteText(value: string) {
  return noteTextMap[value] ?? value;
}

function formatThesisText(value: string) {
  return thesisTextMap[value] ?? value;
}

function formatWebsiteLabel(url: string) {
  try {
    const parsed = new URL(url);
    return parsed.hostname.replace(/^www\./, "");
  } catch {
    return url.replace(/^https?:\/\//, "").replace(/\/$/, "");
  }
}

function topScoreFactors(score: SelectionScore) {
  return [...score.factors].sort((left, right) => right.score - left.score).slice(0, 3);
}

function scoreTone(score: SelectionScore) {
  if (score.total >= 75) {
    return "positive";
  }
  if (score.total >= 55) {
    return "neutral";
  }
  return "negative";
}

function hotspotTone(changePct: number) {
  if (changePct >= 1.5) {
    return "positive";
  }
  if (changePct <= -1.5) {
    return "negative";
  }
  return "balanced";
}

function cycleTone(level: string) {
  if (level === "明显规律") {
    return "positive";
  }
  if (level === "可跟踪规律") {
    return "neutral";
  }
  if (level === "弱规律" || level === "规律不明显") {
    return "negative";
  }
  return "balanced";
}

function regimeChipTone(tone?: string) {
  if (tone === "positive") {
    return "positive";
  }
  if (tone === "negative") {
    return "negative";
  }
  if (tone === "alert") {
    return "alert";
  }
  return "balanced";
}

function insightLevelTone(level: string) {
  if (level === "高") {
    return "alert";
  }
  if (level === "中") {
    return "balanced";
  }
  return "dense";
}


function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function formatYi(value: number) {
  return `${value.toFixed(2)} 亿`;
}


export default App;


