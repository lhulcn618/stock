# Stock Watch Desktop Handover

Updated: 2026-03-18

## 1. Project Goal

This project is a cross-platform desktop stock watchlist app built with `Tauri 2 + Rust + React + TypeScript + Python (AkShare)`.

The current goal is not trade execution. It is a desktop workspace for:

- tracking a manual watchlist
- refreshing daily market data and indicators
- reviewing cycle patterns and swing structure
- opening company-level research details in modal views

## 2. Current Constraints

- The primary watchlist source is `src/data/watchlist.ts`
- `watchlist_codes.txt` remains only as a compatibility fallback
- The UI should stay in Chinese
- After code changes, rebuild the desktop `exe`
- Extended company information should stay in modal views, not the main board

## 3. Current State

- Manual watchlist size: `40`
- Snapshot file: `src/data/akshare-snapshot.json`
- Cycle report file: `docs/cycles/watchlist-cycle-report.json`
- Cycle labels: `16` obvious-pattern stocks, `24` trackable-pattern stocks
- Official website metadata: covered for all `40` stocks in the current snapshot
- Company insight modal data: covered for all `40` stocks in the current snapshot

## 4. Data Flow

### 4.1 Market Data and Indicators

`src/data/watchlist.ts`
-> `scripts/fetch_akshare_watchlist.py`
-> `src/data/akshare-snapshot.json`
-> React frontend
-> Tauri desktop app

### 4.2 Cycle Analysis

`src/data/watchlist.ts`
-> `scripts/generate_watchlist_cycle_report.py`
-> `docs/cycles/watchlist-cycle-report.json`
-> React cycle overview and per-stock modal

### 4.3 Desktop Refresh Path

Refresh button
-> `Tauri invoke`
-> Rust command
-> Python snapshot refresh
-> Python cycle refresh
-> frontend reload

## 5. Main Features Already Built

### 5.1 Dashboard

- top overview area
- top-5 ranked stock list
- watchlist cards
- market mood summary

### 5.2 Stock Cards

- latest price and change
- annual price bucket distribution
- amplitude distribution
- MACD(10,200,7)
- RSI(9)
- cycle label and cycle score
- official website button
- company insight button

### 5.3 Modal Content

- accounting business breakdown
- official-business description
- news and policy sensitivity
- broker reports / investment narrative
- swing chart
- pivot table
- current phase / action / support-resistance summary

## 6. Key Files

### 6.1 Frontend

- `src/App.tsx`
- `src/styles.css`
- `src/types.ts`
- `src/tauriBridge.ts`
- `src/data/mock.ts`
- `src/data/cycle.ts`
- `src/data/watchlist.ts`

### 6.2 Python

- `scripts/fetch_akshare_watchlist.py`
- `scripts/generate_watchlist_cycle_report.py`
- `scripts/build-desktop-exe.cmd`

### 6.3 Tauri / Rust

- `src-tauri/src/lib.rs`
- `src-tauri/tauri.conf.json`

## 7. Watchlist Maintenance

Edit only `src/data/watchlist.ts` when maintaining the manual watchlist.

Example:

```ts
{ code: "603739", name: "WeiLan ShengWu" }
```

Recommended refresh sequence after edits:

```bash
python scripts/fetch_akshare_watchlist.py
python scripts/generate_watchlist_cycle_report.py
cmd /c npx tsc --noEmit
npm run build:exe
```

## 8. Known Issues

### 8.1 AkShare realtime spot endpoint is unstable

`stock_zh_a_spot_em()` still fails intermittently. Current behavior is to fall back to history data, cache, and the previous snapshot instead of failing the whole refresh.

### 8.2 Some external detail endpoints are noisy

News, research report, and realtime fields can return empty or malformed payloads. Current behavior is to keep the snapshot structure stable and fall back to empty samples.

### 8.3 Git safe.directory may be needed on this machine

If Git reports `dubious ownership`, run:

```bash
git config --global --add safe.directory D:/stockapp
```

## 9. Existing Stable Baseline

- `snapshot-2026-03-13-desktop-baseline`

A new snapshot tag should be used for the current state instead of rolling back directly to the 2026-03-13 baseline.
