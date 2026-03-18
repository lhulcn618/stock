import { useEffect, useState, type CSSProperties } from "react";
import { getInitialSnapshot } from "./data/mock";
import { loadDashboardSnapshot, openExternalLink, refreshDashboardSnapshot } from "./tauriBridge";
import type {
  AmplitudeDistributionProfile,
  CycleAnalysis,
  CompanyInsight,
  DashboardSnapshot,
  PriceDistributionProfile,
  SelectionScore,
  SignalLevel,
  TechnicalIndicators,
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
  const [syncStatus, setSyncStatus] = useState("桌面端可通过 AkShare 刷新数据。");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [activeStock, setActiveStock] = useState<WatchStock | null>(null);

  useEffect(() => {
    let cancelled = false;

    loadDashboardSnapshot()
      .then((nextSnapshot) => {
        if (!cancelled) {
          setSnapshot(nextSnapshot);
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
    if (!activeStock) {
      return undefined;
    }

    const originalOverflow = document.body.style.overflow;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setActiveStock(null);
      }
    };

    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [activeStock]);

  const leaders = [...snapshot.stocks]
    .sort((left, right) => right.changePct - left.changePct)
    .slice(0, 3);
  const featuredStocks = [...snapshot.stocks]
    .sort((left, right) => right.selectionScore.total - left.selectionScore.total)
    .slice(0, 5);

  async function handleRefresh() {
    setIsRefreshing(true);
    setSyncStatus("正在刷新 AkShare 快照...");

    try {
      const nextSnapshot = await refreshDashboardSnapshot();
      setSnapshot(nextSnapshot);
      setSyncStatus(`快照已刷新：${nextSnapshot.syncTime}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "刷新失败。";
      setSyncStatus(message);
    } finally {
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

  return (
    <>
      <main className="app-shell">
        <section className="hero-panel">
          <div className="hero-copy">
            <p className="eyebrow">Tauri 2 自选跟踪台</p>
            <h1>把长期位置、波动和信息采集压缩成一个可操作面板。</h1>
            <p className="hero-text">
              围绕个人自选池的盯盘与复盘流程设计：先看价格周期、电池条、振幅分布和技术指标，再按按钮展开主营、新闻政策与券商研报视角。
            </p>
            <p className="sync-status">{syncStatus}</p>
          </div>

          <div className="hero-stats">
            <StatCard label="自选池" value={String(snapshot.watchlistCount)} />
            <StatCard label="强信号" value={String(snapshot.strongSignals)} />
            <StatCard label="平均涨跌" value={`${snapshot.avgChange.toFixed(2)}%`} />
            <StatCard label="最近同步" value={snapshot.syncTime} />
          </div>
        </section>

        <FeaturedSelectionBoard stocks={featuredStocks} />
        <CycleOverviewBoard stocks={snapshot.stocks} />

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
            <h2>每只股票都带有价格位置、振幅、技术指标和弹窗详情。</h2>
          </div>
          <button className="ghost-button" type="button" onClick={handleRefresh} disabled={isRefreshing}>
            {isRefreshing ? "刷新中..." : "用 AkShare 刷新"}
          </button>
        </section>

        <section className="card-grid">
          {snapshot.stocks.map((stock) => (
            <StockCard
              key={stock.symbol}
              stock={stock}
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

function FeaturedSelectionBoard(props: { stocks: WatchStock[] }) {
  return (
    <section className="featured-board">
      <div className="featured-header">
        <div>
          <p className="section-label">精选 5 股</p>
          <h2>按综合评分优先观察的高分股票</h2>
        </div>
        <p className="featured-caption">当前基于价格周期、振幅、量能、RSI 和 MACD 趋势评分。</p>
      </div>

      <div className="featured-grid">
        {props.stocks.map((stock, index) => (
          <article className="featured-card" key={`featured-${stock.symbol}`}>
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
          </article>
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

  return (
    <section className="cycle-board">
      <div className="featured-header">
        <div>
          <p className="section-label">周期总览</p>
          <h2>把波峰波谷节奏直接标到自选池里。</h2>
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
    </section>
  );
}

function StockCard(props: {
  stock: WatchStock;
  onOpenInsight: () => void;
  onOpenLink: (url: string) => Promise<void>;
}) {
  const { stock, onOpenInsight, onOpenLink } = props;
  const officialWebsite = stock.metadata.officialWebsite;
  const insight = resolveCompanyInsight(stock.companyInsight);
  const cycle = stock.cycleAnalysis;

  return (
    <article className="stock-card">
      <header className="stock-card-header">
        <div>
          <p className="section-label">
            {formatMarketLabel(stock.market)} / {formatSectorLabel(stock.sector)}
          </p>
          <h3>{stock.name}</h3>
          <span className="ticker">{stock.symbol}</span>
          <div className="score-pill-row">
            <span className={`score-pill ${scoreTone(stock.selectionScore)}`}>
              精选评分 {stock.selectionScore.total} / {stock.selectionScore.maxScore}
            </span>
            <span className="score-grade">{stock.selectionScore.grade}</span>
            {cycle ? (
              <span className={`score-pill ${cycleTone(cycle.level)}`}>
                周期 {cycle.level} · {cycle.score}
              </span>
            ) : null}
            <span className={`score-pill ${insightLevelTone(insight.newsSensitivity.level)}`}>
              新闻敏感度 {insight.newsSensitivity.level}
            </span>
          </div>
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

      <Sparkline data={stock.sparkline} />
      <PriceBattery profile={stock.priceDistribution} currentPrice={stock.price} />
      <AmplitudeDistributionPanel profile={stock.amplitudeDistribution} />
      <TechnicalsPanel profile={stock.technicals} />
      {cycle ? <CyclePanel analysis={cycle} compact /> : null}

      <div className="signal-row">
        {stock.signals.map((signal) => (
          <SignalTag
            key={`${stock.symbol}-${signal.label}`}
            label={`${formatSignalLabel(signal.label)}：${formatSignalValue(signal.label, signal.value)}`}
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

  return (
    <section
      className="detail-modal-backdrop"
      onClick={onClose}
      aria-label={`个股信息弹窗：${stock.name}`}
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

function CyclePanel(props: { analysis: CycleAnalysis; compact?: boolean }) {
  const { analysis, compact = false } = props;
  const pivotRows = buildPivotRows(analysis);
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

      <div className={`cycle-opportunity-card ${analysis.opportunity.tone}`}>
        <div className="cycle-opportunity-header">
          <div>
            <p className="section-label">当前阶段</p>
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
        <span>平均上升 {analysis.avgUpDays.toFixed(1)} 天</span>
        <span>平均下降 {analysis.avgDownDays.toFixed(1)} 天</span>
        <span>平均上升幅度 {formatSigned(analysis.avgUpReturnPct)}%</span>
        <span>平均下降幅度 {formatSigned(analysis.avgDownReturnPct)}%</span>
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
        格子越满，说明收盘价在该区间停留越久；金框是当前价格，亮点是全年最密集区。
      </p>
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
        <span className={`distribution-pill ${summary.tone}`}>当前 {props.profile.currentAmplitude.toFixed(2)}%</span>
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
        柱子越高，说明该振幅区间出现得越频繁；金框是当前振幅，亮点是历史最密集振幅区。
      </p>
    </section>
  );
}

function SignalTag(props: { label: string; level: SignalLevel }) {
  return <span className={`signal-tag ${props.level}`}>{props.label}</span>;
}

function Sparkline({ data }: { data: number[] }) {
  const width = 320;
  const height = 88;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;

  const points = data
    .map((value, index) => {
      const x = (index / Math.max(1, data.length - 1)) * width;
      const y = height - ((value - min) / span) * (height - 8) - 4;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className="sparkline-wrap" aria-hidden="true">
      <svg className="sparkline" viewBox={`0 0 ${width} ${height}`} role="img">
        <defs>
          <linearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(245, 183, 58, 0.42)" />
            <stop offset="100%" stopColor="rgba(245, 183, 58, 0)" />
          </linearGradient>
        </defs>
        <polyline points={points} fill="none" stroke="currentColor" strokeWidth="3" />
        <polygon points={`0,${height} ${points} ${width},${height}`} fill="url(#sparkFill)" />
      </svg>
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
    return { title: `高振幅异动 ${currentLabel}`, tone: "skewed" };
  }

  if (currentBand <= 1 && dominantBand <= 1) {
    return { title: `低振幅常态 ${currentLabel}`, tone: "balanced" };
  }

  if (currentBand === dominantBand) {
    return { title: `常见振幅区 ${currentLabel}`, tone: "dense" };
  }

  return { title: `过渡振幅区 ${currentLabel}`, tone: "balanced" };
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
