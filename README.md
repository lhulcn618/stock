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
- Watchlist manually maintained in `src/data/watchlist.ts`

## AkShare Sync

1. Maintain the watchlist in `src/data/watchlist.ts` using `{ code, name }`.
2. Run `python scripts/fetch_akshare_watchlist.py` for manual refresh, or use the desktop app refresh button.
3. The script writes `src/data/akshare-snapshot.json`.
4. Run `python scripts/generate_watchlist_cycle_report.py` if you want to refresh the cycle report separately.
5. Frontend prefers the AkShare snapshot and falls back to placeholder data if the snapshot is empty.
6. Tauri exposes `get_dashboard_snapshot`, `get_cycle_report`, and `refresh_akshare_snapshot` so the desktop shell can trigger Python directly.

## Watchlist Maintenance

Edit `src/data/watchlist.ts` directly. Example:

```ts
{ code: "603739", name: "蔚蓝生物" }
```

- Add a stock: add one `{ code, name }` line
- Remove a stock: delete one line
- Rename for your own review workflow: edit `name`
- `watchlist_codes.txt` is now only a compatibility fallback and does not need manual maintenance

The same watchlist source also drives:

- `src/data/akshare-snapshot.json`
- `docs/cycles/watchlist-cycle-report.json`
- the desktop app watchlist cards and cycle modal

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
