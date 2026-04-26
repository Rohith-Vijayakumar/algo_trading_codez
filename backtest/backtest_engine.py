from dataclasses import dataclass, field

import pandas as pd

from execution.risk_manager import RiskManager
from strategy.trend_strategy import SignalType, TrendBreakoutStrategy


@dataclass(frozen=True)
class BacktestTrade:
    symbol: str
    trade_type: SignalType
    entry_index: int
    exit_index: int
    entry_price: float
    exit_price: float
    stop_loss: float
    target_price: float
    quantity: int
    pnl: float
    exit_reason: str


@dataclass(frozen=True)
class BacktestResult:
    initial_capital: float
    final_capital: float
    total_pnl: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    max_drawdown_pct: float
    average_reward_risk: float
    hold_signals: int
    trades: list[BacktestTrade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)


class BacktestEngine:
    def __init__(
        self,
        strategy: TrendBreakoutStrategy,
        risk_manager: RiskManager,
        initial_capital: float,
    ) -> None:
        if initial_capital <= 0:
            raise ValueError("initial_capital must be greater than 0")

        self.strategy = strategy
        self.risk_manager = risk_manager
        self.initial_capital = initial_capital

    def run(self, symbol: str, candles: pd.DataFrame) -> BacktestResult:
        self._validate_candles(candles)

        capital = self.initial_capital
        equity_curve = [capital]
        trades: list[BacktestTrade] = []
        hold_signals = 0
        index = 0
        min_signal_candles = max(
            self.strategy.config.lookback,
            self.strategy.config.atr_period,
        ) + 1

        while index < len(candles):
            if index + 1 < min_signal_candles:
                index += 1
                continue

            signal_candles = candles.iloc[: index + 1]
            signal = self.strategy.generate_signal(symbol, signal_candles)
            if signal.signal == SignalType.HOLD:
                hold_signals += 1
                index += 1
                continue

            if not signal.entry_price or not signal.stop_loss or not signal.target_price:
                hold_signals += 1
                index += 1
                continue

            position = self.risk_manager.calculate_position_size(
                capital=capital,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
            )
            exit_index, exit_price, exit_reason = self._find_exit(
                signal.signal,
                signal.stop_loss,
                signal.target_price,
                candles.iloc[index + 1 :],
                start_index=index + 1,
                fallback_price=float(candles.iloc[-1]["close"]),
                fallback_index=len(candles) - 1,
            )
            pnl = self._calculate_pnl(
                signal.signal,
                signal.entry_price,
                exit_price,
                position.quantity,
            )
            capital += pnl
            trades.append(
                BacktestTrade(
                    symbol=symbol.upper(),
                    trade_type=signal.signal,
                    entry_index=index,
                    exit_index=exit_index,
                    entry_price=signal.entry_price,
                    exit_price=exit_price,
                    stop_loss=signal.stop_loss,
                    target_price=signal.target_price,
                    quantity=position.quantity,
                    pnl=pnl,
                    exit_reason=exit_reason,
                )
            )
            equity_curve.append(capital)
            index = exit_index + 1

        return self._build_result(
            final_capital=capital,
            trades=trades,
            hold_signals=hold_signals,
            equity_curve=equity_curve,
        )

    def _find_exit(
        self,
        signal_type: SignalType,
        stop_loss: float,
        target_price: float,
        future_candles: pd.DataFrame,
        start_index: int,
        fallback_price: float,
        fallback_index: int,
    ) -> tuple[int, float, str]:
        for offset, candle in enumerate(future_candles.itertuples(index=False), start=start_index):
            high = float(candle.high)
            low = float(candle.low)

            if signal_type == SignalType.BUY:
                if low <= stop_loss:
                    return offset, stop_loss, "STOP_LOSS"
                if high >= target_price:
                    return offset, target_price, "TARGET"

            if signal_type == SignalType.SELL:
                if high >= stop_loss:
                    return offset, stop_loss, "STOP_LOSS"
                if low <= target_price:
                    return offset, target_price, "TARGET"

        return fallback_index, fallback_price, "END_OF_DATA"

    def _calculate_pnl(
        self,
        signal_type: SignalType,
        entry_price: float,
        exit_price: float,
        quantity: int,
    ) -> float:
        if signal_type == SignalType.BUY:
            return (exit_price - entry_price) * quantity
        if signal_type == SignalType.SELL:
            return (entry_price - exit_price) * quantity
        raise ValueError(f"Unsupported signal type: {signal_type}")

    def _build_result(
        self,
        final_capital: float,
        trades: list[BacktestTrade],
        hold_signals: int,
        equity_curve: list[float],
    ) -> BacktestResult:
        winning_trades = sum(1 for trade in trades if trade.pnl > 0)
        losing_trades = sum(1 for trade in trades if trade.pnl < 0)
        total_trades = len(trades)
        win_rate = winning_trades / total_trades if total_trades else 0.0
        average_reward_risk = self._average_reward_risk(trades)
        max_drawdown_pct = self._max_drawdown_pct(equity_curve)

        return BacktestResult(
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_pnl=final_capital - self.initial_capital,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            max_drawdown_pct=max_drawdown_pct,
            average_reward_risk=average_reward_risk,
            hold_signals=hold_signals,
            trades=trades,
            equity_curve=equity_curve,
        )

    def _average_reward_risk(self, trades: list[BacktestTrade]) -> float:
        reward_risks = []
        for trade in trades:
            risk = abs(trade.entry_price - trade.stop_loss)
            reward = abs(trade.target_price - trade.entry_price)
            if risk > 0:
                reward_risks.append(reward / risk)
        return sum(reward_risks) / len(reward_risks) if reward_risks else 0.0

    def _max_drawdown_pct(self, equity_curve: list[float]) -> float:
        peak = equity_curve[0]
        max_drawdown = 0.0
        for equity in equity_curve:
            peak = max(peak, equity)
            drawdown = (peak - equity) / peak
            max_drawdown = max(max_drawdown, drawdown)
        return max_drawdown

    def _validate_candles(self, candles: pd.DataFrame) -> None:
        required_columns = {"open", "high", "low", "close", "volume"}
        missing_columns = required_columns.difference(candles.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"candles is missing required columns: {missing}")
