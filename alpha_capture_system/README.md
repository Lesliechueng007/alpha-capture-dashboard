# Crypto Alpha Capture System (MVP)

一个面向加密货币二级市场的交易研究与执行闭环原型，覆盖：

- 长期跟踪资产池（BTC / ETH / SOL / BASE 生态 / 衍生品 / AI Agent）
- 基本面评分 + 资金面/交易面因子（价格动量、成交量异常、持仓变化）
- 规则化仓位分配与风险控制
- 回测执行（含手续费与滑点）
- 交易日志、决策记录、自动复盘建议

## 目录

- `config/`：资产池与策略参数
- `src/alpha_capture/`：核心引擎
- `scripts/run_backtest.py`：一键运行入口
- `reports/`：输出报告与日志

## 快速开始

```bash
cd /Users/sanyue/Documents/Playground/alpha_capture_system
python3 scripts/run_backtest.py
```

运行完成后可查看：

- `reports/backtest_report.md`
- `reports/trade_log.csv`
- `reports/decision_log.jsonl`

## 接入真实数据（Binance + CoinGecko）

`binance_coingecko` 数据源逻辑：

- 价格与成交量：优先 Binance 日线，失败时回退到 CoinGecko
- 链上生态代理数据：来自 CoinGecko（https://www.coingecko.com/）
- 衍生品持仓（Open Interest）：Binance Futures，缺失时用市值/成交量代理估算

运行方式：

```bash
python3 scripts/run_backtest.py --source binance_coingecko
```

如你希望实时数据失败时不回退模拟数据：

```bash
python3 scripts/run_backtest.py --source binance_coingecko --no-fallback
```

资产映射可在 `config/universe.json` 维护：

- `binance_spot_symbol`
- `binance_perp_symbol`
- `coingecko_id`

参数批量优化：

```bash
python3 scripts/optimize_strategy.py --source binance_coingecko
```

优化输出：

- `reports/optimization_results.csv`
- `reports/best_params.json`

阿尔法标的跟踪（当前含 HYPE）：

```bash
python3 scripts/update_alpha_watchlist.py --symbol HYPE
```

输出：

- `reports/alpha_watchlist_latest.md`
- `reports/alpha_watchlist_snapshot.json`

## Web 可视化看板

一键刷新看板数据：

```bash
python3 scripts/refresh_dashboard.py
```

本地网页预览：

```bash
python3 -m http.server 8080 --directory web
```

然后打开：

- `http://localhost:8080`

## 一键发布（GitHub Pages）

已配置工作流：

- 仓库根目录 `.github/workflows/deploy-alpha-dashboard.yml`

发布方式：

1. 将仓库推到 GitHub，并在仓库 `Settings -> Pages` 里选择 `Build and deployment: GitHub Actions`。
2. 打开 `Actions -> Deploy Alpha Dashboard`。
3. 点击 `Run workflow`（一键发布）。

说明：

- 每次 `Run workflow` 会自动拉取 CoinGecko 最新数据并构建网页。
- 推送到 `main` 分支相关路径也会自动触发部署。
- 页面地址通常是 `https://<你的GitHub用户名>.github.io/<仓库名>/`。

## 下一步迭代建议

- 接交易所真实行情源（如 Binance / Bybit）
- 引入链上资金流、稳定币净流入、期现基差等因子
- 分层回测（按赛道、按 regime）
- 做在线执行（paper trading -> small capital -> scaled）
