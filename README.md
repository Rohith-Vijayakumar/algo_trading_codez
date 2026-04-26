# Algo Trading System

Risk-first algo trading framework for Indian equities, BTC, and ETH.

## Current Scope

- SQLAlchemy trade storage
- Fixed-risk position sizing
- Trade creation flow
- Price action strategy signal engine
- Backtest engine with PnL, win rate, drawdown, and equity curve metrics
- CSV market data loading and validation

## Core Rules

- Risk per trade must stay at or below 0.5% of capital.
- Daily loss limits and kill switches are mandatory before live execution.
- No martingale or revenge trading.
- Options trades must use defined risk.
- BTC and ETH share the same portfolio risk cap as equities.

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python main.py
```

## Run A Backtest

```powershell
python run_backtest.py --file data/reliance.csv --symbol RELIANCE --capital 100000 --asset-class equity
```
