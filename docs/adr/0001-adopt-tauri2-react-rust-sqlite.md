# ADR-0001: Adopt Tauri 2, React, Rust, and SQLite for the desktop foundation

## Status

Accepted

## Context

We need a cross-platform desktop application for tracking a personal stock watchlist with daily visual summaries. The product benefits from:

- low memory use
- native packaging
- local-first persistence
- a responsive dashboard UI
- the ability to add market data providers without exposing secrets to the frontend

The current workspace is empty, and the local machine does not yet have Rust installed.

## Decision

Use:

- `Tauri 2` as the desktop shell
- `Rust` for native commands, sync orchestration, and persistence logic
- `React + TypeScript + Vite` for the UI layer
- `SQLite` as the local persistence engine

## Consequences

### Positive

- Lower runtime overhead than Electron for a desktop dashboard.
- Strong separation between UI and data/sync logic.
- Easier local-first behavior with SQLite.
- Good path to cross-platform distribution.

### Negative

- Tauri 2 setup depends on Rust, which is not installed yet in this environment.
- Team members unfamiliar with Rust may ramp up more slowly.
- Packaging and native plugin setup are more involved than a pure web app.

### Neutral

- The UI can move quickly with mock data before the real provider layer is finished.
- Provider selection remains open and should stay behind a Rust adapter boundary.

## Alternatives Considered

### Electron + React

Rejected for now because memory usage and package footprint are less favorable for a focused desktop watchlist tool.

### Web app + backend API

Rejected for MVP because it introduces auth, hosting, and operations before validating the local desktop workflow.

## References

- Tauri 2 documentation
- React and Vite documentation
- SQLite documentation
