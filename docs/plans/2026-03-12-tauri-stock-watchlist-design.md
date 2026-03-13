# System: Stock Watch Desktop

## Requirements

### Functional

- Maintain a personal watchlist of stocks across multiple markets.
- Show daily tracking cards for each selected stock.
- Visualize short-term trend changes with compact charts.
- Highlight alerts such as breakout, drawdown, unusual volume, or custom notes.
- Support local-first usage with cached market data.
- Reserve a clean command boundary so Rust can own data sync, storage, and indicator calculation.

### Non-Functional

- Performance: dashboard first paint under 2 seconds on a normal laptop.
- Responsiveness: interactions should feel instant, with filtering under 100ms.
- Availability: local app should remain usable offline with last synced data.
- Portability: one codebase for Windows, macOS, and Linux via Tauri 2.
- Maintainability: frontend and Rust domains should remain loosely coupled through typed commands.
- Security: secrets for paid data providers should never live in frontend code.

### Constraints

- Current workspace is empty.
- Rust toolchain is not installed on this machine yet.
- MVP should prioritize local-first desktop value over multi-user cloud complexity.

## High-Level Architecture

```text
+---------------------------+        invoke / events        +----------------------------+
| React + TypeScript UI     | <---------------------------> | Tauri 2 Rust Core          |
|                           |                               |                            |
| - dashboard               |                               | - command handlers         |
| - watchlist filters       |                               | - market provider adapter  |
| - charts + notes          |                               | - sync scheduler           |
+-------------+-------------+                               +-------------+--------------+
              |                                                                 |
              | local state / cache                                              | SQL
              v                                                                 v
    +-------------------------+                                   +---------------------------+
    | UI view models          |                                   | SQLite / local storage    |
    | mock data for MVP       |                                   | watchlist, snapshots,     |
    | later: TanStack Query   |                                   | notes, sync logs          |
    +-------------------------+                                   +---------------------------+
```

## Architecture Recommendation

### Recommended Option

Use a local-first desktop architecture:

- `Tauri 2` for cross-platform packaging and native windowing
- `Rust` for market data ingestion, persistence, scheduling, and indicator computation
- `React + TypeScript` for fast dashboard rendering and interaction
- `SQLite` as the single local source of truth

This is the best fit because a self-selected watchlist app benefits more from startup speed, offline access, and local persistence than from a heavy backend-first design.

### Alternatives Considered

#### Electron + Node

Faster to start for web developers, but memory usage is higher and the native shell story is weaker than Tauri for this use case.

#### Pure web app + cloud backend

Good for multi-user collaboration, but it adds deployment and auth complexity before the core desktop workflow is proven.

## Core Modules

### Frontend

- `DashboardShell`: hero summary, sync status, market mood
- `WatchlistBoard`: grouped stock cards
- `SignalStrip`: breakout, RSI, turnover, or custom flags
- `TrendPanel`: compact sparkline and longer period chart
- `StockDetailDrawer`: notes, recent catalysts, and risk checklist

### Rust Core

- `commands`: typed functions exposed to Tauri
- `providers`: market data adapters with a common trait
- `storage`: SQLite repository layer
- `analysis`: indicator calculations and signal generation
- `sync`: scheduled refresh and retry logic

## Data Flow

1. UI loads dashboard and requests watchlist snapshot from Rust.
2. Rust reads SQLite and returns the latest local snapshot immediately.
3. A background sync updates quotes, volume, and derived indicators.
4. Rust emits sync status or data-ready events back to the frontend.
5. UI refreshes cards and charts without blocking the whole window.

## Data Model

### Watchlist Item

- symbol
- market
- display_name
- tags
- thesis
- risk_note
- sector

### Daily Snapshot

- trade_date
- close
- change_pct
- volume
- turnover_rate
- high_20d
- low_20d
- momentum_score

### Derived Signal

- signal_type
- score
- message
- severity

## Failure Modes

- Provider API unavailable: show last sync time and stale-data badge.
- Rate limited: queue retries with exponential backoff.
- Corrupt local data: keep raw sync log and recover from last valid snapshot.
- Frontend render issue: preserve shell and show per-panel fallbacks.

## Security Considerations

- Keep provider keys in Rust-side env or OS secure storage.
- Do not expose full provider credentials to frontend.
- Validate symbol and market parameters before network calls.
- Log sync failures without leaking secrets.

## Delivery Plan

### Phase 1

- Watchlist dashboard with mock data
- Tauri 2 shell scaffolding
- local layout, signals, mini charts

### Phase 2

- SQLite persistence
- real provider adapter
- sync history and manual refresh

### Phase 3

- alert rules
- calendar/event overlays
- export and backup

## Assumptions

- The first target user is a single investor using a desktop app personally.
- The initial release can be local-only.
- We should support A-share, Hong Kong, and US symbols through a provider abstraction rather than hard-coding one market.
