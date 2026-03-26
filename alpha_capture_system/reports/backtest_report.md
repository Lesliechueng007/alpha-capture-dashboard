# Alpha Strategy Backtest Report

## Meta

- Start: 2026-02-09
- End: 2026-03-26
- Universe: BTC,ETH,SOL,BASE,DRIV,AIA,HYPE

## Metrics

- Total Return: -27.19%
- Annualized Return: -92.37%
- Annualized Vol: 33.22%
- Sharpe: -2.78
- Max Drawdown: 28.02%
- Win Rate: 37.78%

## Symbol Contribution (Return-Rate Approx)

- HYPE: -0.0085
- BTC: -0.0185
- BASE: -0.0238
- AIA: -0.0416
- SOL: -0.0545
- ETH: -0.0694
- DRIV: -0.0717

## Reflection

- Sharpe 偏低，建议先做 regime 分层（趋势/震荡）并在震荡阶段降低动量因子权重。
- 最大回撤较高，建议收紧单资产权重上限并提高紧急去杠杆比例。
- 胜率偏低，建议加入资金费率/基差过滤器减少逆势交易。
- 本轮贡献最高资产: HYPE (-0.008)；最低资产: DRIV (-0.072)。
- 下一轮迭代建议：优先替换弱贡献资产的信号触发条件，再做全局再优化。
