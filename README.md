# Stock Watch Desktop

A cross-platform stock watchlist desktop app scaffold built for `Tauri 2 + Rust + React`.

## Product Goal

This project targets a desktop-first stock watchlist experience with:

- daily watchlist tracking
- trend visualization
- watchlist notes and tags
- cross-platform packaging through Tauri 2

## Recommended Stack

- Desktop shell: Tauri 2
- Backend: Rust commands for data sync, persistence, and indicators
- Frontend: React + TypeScript + Vite
- Local storage: SQLite
- Charts: lightweight SVG components first, then ECharts or Lightweight Charts
- Market data bridge: Python + AkShare

## MVP Scope

- Watchlist overview dashboard
- Daily change cards and sector grouping
- Per-stock mini trend chart
- Momentum / volume / note summary
- Local mock data now, provider integration next
- Watchlist codes stored in `watchlist_codes.txt`

## AkShare Sync

1. Maintain symbols in `watchlist_codes.txt`.
2. Run `python scripts/fetch_akshare_watchlist.py` for manual refresh, or use the desktop app refresh button.
3. The script writes `src/data/akshare-snapshot.json`.
4. Frontend prefers the AkShare snapshot and falls back to placeholder data if the snapshot is empty.
5. Tauri exposes `get_dashboard_snapshot` and `refresh_akshare_snapshot` so the desktop shell can trigger Python directly.

## Suggested Next Steps

1. Install Rust via `rustup`.
2. Run `npm install`.
3. Add Tauri CLI and generate icons.
4. Run `python scripts/fetch_akshare_watchlist.py` to refresh market data.
5. Replace JSON snapshot flow with Rust-managed persistence when Tauri is fully wired.

## Current Status

The workspace currently contains:

- architecture and ADR docs
- a React dashboard scaffold
- a Tauri 2 Rust shell scaffold
- an AkShare watchlist fetch script
- a Tauri command bridge for one-click desktop refresh

Rust is not installed in this environment yet, so the app has not been compiled here.
