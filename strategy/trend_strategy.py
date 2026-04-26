from dataclasses import dataclass
from enum import Enum

import pandas as pd


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class StrategySignal:
    signal: SignalType
    symbol: str
    entry_price: float | None = None
    stop_loss: float | None = None
    target_price: float | None = None
    reason: str = ""


@dataclass(frozen=True)
class StrategyConfig:
    lookback: int = 20
    volume_multiplier: float = 1.5
    reward_risk_ratio: float = 2.0
    breakout_buffer_pct: float = 0.001
    atr_period: int = 14
    min_stop_atr: float = 0.5
    max_stop_atr: float = 3.0
    min_average_volume: float = 1000


ASSET_CONFIGS = {
    "equity": StrategyConfig(
        lookback=20,
        volume_multiplier=1.5,
        reward_risk_ratio=2.0,
        breakout_buffer_pct=0.001,
        min_average_volume=100000,
    ),
    "crypto": StrategyConfig(
        lookback=24,
        volume_multiplier=1.3,
        reward_risk_ratio=1.8,
        breakout_buffer_pct=0.002,
        min_average_volume=100,
    ),
}


class TrendBreakoutStrategy:
    def __init__(
        self,
        config: StrategyConfig | None = None,
        asset_class: str | None = None,
    ) -> None:
        if config and asset_class:
            raise ValueError("Use either config or asset_class, not both")

        self.config = config or ASSET_CONFIGS.get(asset_class or "", StrategyConfig())

        if self.config.lookback < 3:
            raise ValueError("lookback must be at least 3")
        if self.config.volume_multiplier <= 0:
            raise ValueError("volume_multiplier must be greater than 0")
        if self.config.reward_risk_ratio <= 0:
            raise ValueError("reward_risk_ratio must be greater than 0")
        if self.config.breakout_buffer_pct < 0:
            raise ValueError("breakout_buffer_pct cannot be negative")
        if self.config.atr_period < 2:
            raise ValueError("atr_period must be at least 2")
        if self.config.min_stop_atr <= 0 or self.config.max_stop_atr <= 0:
            raise ValueError("ATR stop limits must be greater than 0")
        if self.config.min_stop_atr > self.config.max_stop_atr:
            raise ValueError("min_stop_atr cannot be greater than max_stop_atr")

    def generate_signal(self, symbol: str, candles: pd.DataFrame) -> StrategySignal:
        self._validate_candles(candles)

        min_candles = max(self.config.lookback, self.config.atr_period) + 1
        if len(candles) < min_candles:
            return StrategySignal(SignalType.HOLD, symbol, reason="Not enough candles")

        recent = candles.tail(self.config.lookback + 1)
        previous = recent.iloc[:-1]
        latest = recent.iloc[-1]

        resistance = float(previous["high"].max())
        support = float(previous["low"].min())
        recent_swing_low = float(previous["low"].tail(5).min())
        recent_swing_high = float(previous["high"].tail(5).max())
        average_volume = float(previous["volume"].mean())
        close = float(latest["close"])
        high = float(latest["high"])
        low = float(latest["low"])
        volume = float(latest["volume"])

        if average_volume < self.config.min_average_volume:
            return StrategySignal(
                SignalType.HOLD,
                symbol.upper(),
                reason="Average volume below liquidity threshold",
            )

        atr = self._calculate_atr(candles)
        uptrend = self._is_uptrend(previous)
        downtrend = self._is_downtrend(previous)
        volume_confirmed = volume >= average_volume * self.config.volume_multiplier
        upside_breakout = close > resistance * (1 + self.config.breakout_buffer_pct)
        downside_breakout = close < support * (1 - self.config.breakout_buffer_pct)

        if uptrend and upside_breakout and volume_confirmed:
            stop_loss = max(recent_swing_low, low)
            risk = close - stop_loss
            if not self._is_stop_valid(risk, atr):
                return StrategySignal(
                    SignalType.HOLD,
                    symbol.upper(),
                    reason="Stop distance outside ATR limits",
                )
            return StrategySignal(
                signal=SignalType.BUY,
                symbol=symbol.upper(),
                entry_price=close,
                stop_loss=stop_loss,
                target_price=close + risk * self.config.reward_risk_ratio,
                reason="Uptrend breakout with buffer, volume, and ATR confirmation",
            )

        if downtrend and downside_breakout and volume_confirmed:
            stop_loss = min(recent_swing_high, high)
            risk = stop_loss - close
            if not self._is_stop_valid(risk, atr):
                return StrategySignal(
                    SignalType.HOLD,
                    symbol.upper(),
                    reason="Stop distance outside ATR limits",
                )
            return StrategySignal(
                signal=SignalType.SELL,
                symbol=symbol.upper(),
                entry_price=close,
                stop_loss=stop_loss,
                target_price=close - risk * self.config.reward_risk_ratio,
                reason="Downtrend breakdown with buffer, volume, and ATR confirmation",
            )

        return StrategySignal(SignalType.HOLD, symbol.upper(), reason="No confirmed setup")

    def _is_uptrend(self, candles: pd.DataFrame) -> bool:
        closes = candles["close"].tail(5)
        return closes.iloc[-1] > closes.iloc[0] and closes.mean() > candles["close"].mean()

    def _is_downtrend(self, candles: pd.DataFrame) -> bool:
        closes = candles["close"].tail(5)
        return closes.iloc[-1] < closes.iloc[0] and closes.mean() < candles["close"].mean()

    def _calculate_atr(self, candles: pd.DataFrame) -> float:
        recent = candles.tail(self.config.atr_period + 1).copy()
        previous_close = recent["close"].shift(1)
        true_range = pd.concat(
            [
                recent["high"] - recent["low"],
                (recent["high"] - previous_close).abs(),
                (recent["low"] - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        return float(true_range.dropna().tail(self.config.atr_period).mean())

    def _is_stop_valid(self, risk: float, atr: float) -> bool:
        if risk <= 0 or atr <= 0:
            return False
        stop_atr = risk / atr
        return self.config.min_stop_atr <= stop_atr <= self.config.max_stop_atr

    def _validate_candles(self, candles: pd.DataFrame) -> None:
        required_columns = {"open", "high", "low", "close", "volume"}
        missing_columns = required_columns.difference(candles.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"candles is missing required columns: {missing}")
