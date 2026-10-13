"""
hermes_metrics.py
==================
Turns a run_backtest() result into the "Required metrics" from the Hermes
skill, plus the screening/ranking gates (trade-sample gate, 2-3 trades/day
band, safety gates).
"""

from __future__ import annotations
import numpy as np
import pandas as pd


def compute_metrics(result: dict, initial_capital: float, start_ts, end_ts) -> dict:
    trades = result["trades"]
    n_trades = len(trades)
    calendar_days = max((end_ts - start_ts).days, 1)  # crypto = calendar days (24/7), per skill default
    trades_per_active_day = n_trades / calendar_days

    if n_trades == 0:
        return {
            "total_trades": 0, "trades_per_active_day": 0.0, "win_rate": np.nan,
            "avg_win": np.nan, "avg_loss": np.nan, "expectancy": np.nan,
            "profit_factor": np.nan, "net_profit": 0.0, "net_return_pct": 0.0,
            "max_drawdown_pct": 0.0, "sharpe": np.nan, "sortino": np.nan,
            "calmar": np.nan, "final_equity": result["final_equity"],
            "ambiguous_fills": result["ambiguous_fills"], "low_sample": True,
        }

    pnls = np.array([t["pnl"] for t in trades])
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]
    win_rate = len(wins) / n_trades
    avg_win = wins.mean() if len(wins) else 0.0
    avg_loss = losses.mean() if len(losses) else 0.0
    gross_profit = wins.sum() if len(wins) else 0.0
    gross_loss = -losses.sum() if len(losses) else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else np.inf
    expectancy = pnls.mean()
    net_profit = pnls.sum()
    net_return_pct = net_profit / initial_capital

    # Equity curve (marked at trade-close events only -- documented simplification;
    # continuous mark-to-market would need per-bar equity, omitted for engine speed).
    eq = pd.Series([e for _, e in result["equity_points"]])
    running_max = eq.cummax()
    drawdown = (eq - running_max) / running_max
    max_drawdown_pct = drawdown.min()

    # Sharpe/Sortino/Calmar approximated from per-trade returns, annualized by
    # trade frequency (documented simplification -- true Sharpe needs a daily
    # mark-to-market equity series).
    trade_returns = pnls / initial_capital
    trades_per_year = trades_per_active_day * 365
    ann_factor = np.sqrt(trades_per_year) if trades_per_year > 0 else 0.0
    ret_std = trade_returns.std(ddof=1) if n_trades > 1 else 0.0
    sharpe = (trade_returns.mean() / ret_std * ann_factor) if ret_std > 0 else np.nan
    downside = trade_returns[trade_returns < 0]
    down_std = downside.std(ddof=1) if len(downside) > 1 else 0.0
    sortino = (trade_returns.mean() / down_std * ann_factor) if down_std > 0 else np.nan
    calmar = (net_return_pct / abs(max_drawdown_pct)) if max_drawdown_pct < 0 else np.nan

    return {
        "total_trades": n_trades,
        "trades_per_active_day": round(trades_per_active_day, 4),
        "win_rate": round(win_rate, 4),
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "expectancy": round(expectancy, 4),
        "profit_factor": round(profit_factor, 4) if np.isfinite(profit_factor) else profit_factor,
        "net_profit": round(net_profit, 4),
        "net_return_pct": round(net_return_pct, 4),
        "max_drawdown_pct": round(float(max_drawdown_pct), 4),
        "sharpe": round(sharpe, 4) if np.isfinite(sharpe) else np.nan,
        "sortino": round(sortino, 4) if np.isfinite(sortino) else np.nan,
        "calmar": round(calmar, 4) if np.isfinite(calmar) else np.nan,
        "final_equity": round(result["final_equity"], 2),
        "ambiguous_fills": result["ambiguous_fills"],
        "low_sample": n_trades < 100,
    }


def passes_safety_gates(metrics: dict, require_non_negative: bool = True,
                         max_drawdown_pct: float = 0.20) -> tuple[bool, str]:
    """Hard gates from the skill: valid data, enough trades (flagged not blocked),
    drawdown within the plan's max_drawdown_pct (default 20%), non-negative net
    result after costs (if chosen)."""
    if metrics["total_trades"] == 0:
        return False, "no_trades"
    if metrics["max_drawdown_pct"] < -abs(max_drawdown_pct):
        return False, "max_drawdown_exceeded"
    if require_non_negative and metrics["net_profit"] < 0:
        return False, "negative_net_after_costs"
    return True, "ok"


def rank_score(metrics: dict) -> tuple:
    """Default ordering (per skill): out-of-sample net profit/CAGR, then profit
    factor, lower max drawdown, Sharpe/Sortino, stability, closeness to target
    trade frequency, fewer parameters. Here we approximate with a sortable tuple
    (higher is better; drawdown negated so 'higher/less-negative' sorts first)."""
    pf = metrics["profit_factor"]
    pf = pf if np.isfinite(pf) else 999.0
    sharpe = metrics["sharpe"] if np.isfinite(metrics["sharpe"]) else -999.0
    freq_closeness = -abs(metrics["trades_per_active_day"] - 2.5)  # closer to 2-3 band = better
    return (
        round(metrics["net_return_pct"], 6),
        round(pf, 6),
        round(metrics["max_drawdown_pct"], 6),  # already negative; less negative = better
        round(sharpe, 6),
        round(freq_closeness, 6),
    )
