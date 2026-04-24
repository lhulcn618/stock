# Stock Watch Desktop

一个面向 A 股自选池的桌面盯盘与复盘工具，基于 `Tauri 2 + Rust + React + Python` 构建。

## 项目简介

这个项目的目标不是做一个“全市场大而全”的行情终端，而是围绕固定自选池，帮助使用者长期熟悉个股的：

- 价格周期
- 波动区间
- 筹码成本
- 板块联动
- 技术指标
- 信息采集

当前桌面端已经支持：

- 自选池卡片看板
- 个股迷你 K 线
- 周期评级与波峰波谷分析
- 筹码分布与主力成本区
- MACD / RSI / 布林线
- 官网、新闻、研报、主营信息弹窗
- A 股上涨家数曲线

## 技术栈

- 桌面壳：`Tauri 2`
- 后端命令：`Rust`
- 前端：`React + TypeScript + Vite`
- A 股日线行情：`Baostock` 优先
- 元信息与扩展数据：`AkShare`
- 本地快照：`JSON`

## 关键目录

- 自选池：[`src/data/watchlist.ts`](/D:/stockapp/src/data/watchlist.ts)
- 行情快照：[`src/data/akshare-snapshot.json`](/D:/stockapp/src/data/akshare-snapshot.json)
- 周期报告：[`docs/cycles/watchlist-cycle-report.json`](/D:/stockapp/docs/cycles/watchlist-cycle-report.json)
- 桌面后端：[`src-tauri/src/lib.rs`](/D:/stockapp/src-tauri/src/lib.rs)
- 打包脚本：[`scripts/build-desktop-exe.cmd`](/D:/stockapp/scripts/build-desktop-exe.cmd)
- 轻量市场宽度刷新：[`scripts/refresh_market_breadth_snapshot.py`](/D:/stockapp/scripts/refresh_market_breadth_snapshot.py)

## 自选池维护

直接编辑 [`src/data/watchlist.ts`](/D:/stockapp/src/data/watchlist.ts)。

格式示例：

```ts
{ code: "603739", name: "蔚蓝生物" }
```

维护规则：

- 加股票：新增一行 `{ code, name }`
- 删股票：删除对应一行
- 改名称：直接修改 `name`

这个文件会同时驱动：

- 自选池列表展示
- 行情快照刷新
- 周期分析报告

## 数据刷新

手动刷新全量市场数据：

```bash
python scripts/fetch_akshare_watchlist.py
```

单独重算周期报告：

```bash
python scripts/generate_watchlist_cycle_report.py
```

只刷新 A 股上涨家数曲线：

```bash
python scripts/refresh_market_breadth_snapshot.py
```

说明：

- A 股日线价格/历史优先走 `Baostock`
- 官网、板块、ETF、美股、新闻、研报等信息仍由 `AkShare` 提供
- 桌面端中的“A股上涨家数曲线”每 `10` 分钟会自动轻量刷新一次

## 生成 Release EXE

### 前置环境

Windows 下建议先准备：

- `Node.js`
- `Python`
- `Rust`
- `Visual Studio C++ Build Tools`

### 推荐打包方式

安装依赖后执行：

```bash
npm install
npm run build:exe
```

产物位置：

- 最新版：[`builds/stock-watch-desktop-latest.exe`](/D:/stockapp/builds/stock-watch-desktop-latest.exe)
- 归档版：`builds/stock-watch-desktop-YYYYMMDD-HHMMSS.exe`

这套脚本会：

1. 构建前端产物
2. 编译 Tauri release 可执行文件
3. 复制到 `builds/`
4. 生成一个 `latest.exe` 和一个时间戳归档版本

### 当前仓库的兜底打包方式

如果前端源码构建有问题，但 `dist` 已经是可用状态，可以直接使用：

```bash
cmd /c scripts\windows-tauri-env.cmd npx tauri build --no-bundle --config src-tauri\tauri.skip-frontend.json
```

这个模式会跳过前端重编译，直接使用现有的 `dist` 目录打包桌面程序。

编译出的原始 exe 在：

- [`target-rustlld-serial/release/stock-watch-desktop.exe`](/D:/stockapp/target-rustlld-serial/release/stock-watch-desktop.exe)

如果需要对外发包，建议再复制到 `builds/` 目录。

## 使用建议

- 平时只维护 [`src/data/watchlist.ts`](/D:/stockapp/src/data/watchlist.ts)
- 刷行情前先确认 Python 环境正常
- 发布给别人测试时，优先给 [`builds/stock-watch-desktop-latest.exe`](/D:/stockapp/builds/stock-watch-desktop-latest.exe)
- 需要留历史版本时，用时间戳归档包，不要只保留 `latest.exe`

## 当前定位

这是一个“个人自选池长期跟踪工具”，核心价值是：

- 帮助你长期熟悉固定股票
- 快速识别价格周期与情绪位置
- 把盯盘、复盘、信息采集放到一个桌面端里

如果后面继续扩展，建议优先增强：

- 周期识别
- 情绪宽度
- 筹码阶段判断
- 板块联动强度
