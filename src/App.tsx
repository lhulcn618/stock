import { useEffect, useState } from "react";
import { getInitialSnapshot } from "./data/mock";
import { loadDashboardSnapshot, refreshDashboardSnapshot } from "./tauriBridge";
import type { DashboardSnapshot, SignalLevel, WatchStock } from "./types";

function App() {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot>(getInitialSnapshot());
  const [syncStatus, setSyncStatus] = useState("Desktop mode can refresh via AkShare.");
  const [isRefreshing, setIsRefreshing] = useState(false);

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
          setSyncStatus("Using local snapshot. Desktop refresh is not available in browser mode.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const leaders = [...snapshot.stocks]
    .sort((a, b) => b.changePct - a.changePct)
    .slice(0, 3);

  async function handleRefresh() {
    setIsRefreshing(true);
    setSyncStatus("Refreshing AkShare snapshot...");

    try {
      const nextSnapshot = await refreshDashboardSnapshot();
      setSnapshot(nextSnapshot);
      setSyncStatus(`Snapshot refreshed at ${nextSnapshot.syncTime}.`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Refresh failed.";
      setSyncStatus(message);
    } finally {
      setIsRefreshing(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">Tauri 2 watchlist desk</p>
          <h1>Daily stock tracking with a calm trader's cockpit.</h1>
          <p className="hero-text">
            Built for a personal watchlist workflow: fast scan, clearer signals,
            and less spreadsheet fatigue.
          </p>
          <p className="sync-status">{syncStatus}</p>
        </div>

        <div className="hero-stats">
          <StatCard label="Watchlist" value={String(snapshot.watchlistCount)} />
          <StatCard label="Strong signals" value={String(snapshot.strongSignals)} />
          <StatCard label="Average move" value={`${snapshot.avgChange.toFixed(2)}%`} />
          <StatCard label="Last sync" value={snapshot.syncTime} />
        </div>
      </section>

      <section className="market-strip">
        <div>
          <p className="section-label">Market tone</p>
          <strong>{snapshot.mood}</strong>
        </div>
        <div>
          <p className="section-label">Top leaders</p>
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
          <p className="section-label">Watchlist board</p>
          <h2>High-conviction names worth checking before the close.</h2>
        </div>
        <button className="ghost-button" type="button" onClick={handleRefresh} disabled={isRefreshing}>
          {isRefreshing ? "Refreshing..." : "Refresh with AkShare"}
        </button>
      </section>

      <section className="card-grid">
        {snapshot.stocks.map((stock) => (
          <StockCard key={stock.symbol} stock={stock} />
        ))}
      </section>
    </main>
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

function StockCard({ stock }: { stock: WatchStock }) {
  return (
    <article className="stock-card">
      <header className="stock-card-header">
        <div>
          <p className="section-label">
            {stock.market} / {stock.sector}
          </p>
          <h3>{stock.name}</h3>
          <span className="ticker">{stock.symbol}</span>
        </div>
        <div className={stock.changePct >= 0 ? "pill up" : "pill down"}>
          {formatSigned(stock.changePct)}%
        </div>
      </header>

      <div className="price-row">
        <strong>{stock.price.toFixed(2)}</strong>
        <span>Momentum {stock.momentum}</span>
        <span>Vol {stock.volumeRatio.toFixed(2)}x</span>
      </div>

      <Sparkline data={stock.sparkline} />

      <div className="signal-row">
        {stock.signals.map((signal) => (
          <SignalTag
            key={`${stock.symbol}-${signal.label}`}
            label={`${signal.label}: ${signal.value}`}
            level={signal.level}
          />
        ))}
      </div>

      <p className="note">{stock.note}</p>
      <p className="thesis">{stock.thesis}</p>
    </article>
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
      const x = (index / (data.length - 1)) * width;
      const y = height - ((value - min) / span) * (height - 8) - 4;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className="sparkline-wrap" aria-hidden="true">
      <svg
        className="sparkline"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
      >
        <defs>
          <linearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(245, 183, 58, 0.42)" />
            <stop offset="100%" stopColor="rgba(245, 183, 58, 0)" />
          </linearGradient>
        </defs>
        <polyline points={points} fill="none" stroke="currentColor" strokeWidth="3" />
        <polygon
          points={`0,${height} ${points} ${width},${height}`}
          fill="url(#sparkFill)"
        />
      </svg>
    </div>
  );
}

function formatSigned(value: number) {
  return value >= 0 ? `+${value.toFixed(2)}` : value.toFixed(2);
}

export default App;
