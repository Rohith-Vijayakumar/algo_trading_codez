from dataclasses import dataclass
from enum import Enum


class AssetClass(str, Enum):
    EQUITY = "equity"
    CRYPTO = "crypto"


@dataclass(frozen=True)
class PositionSize:
    quantity: int
    risk_amount: float
    stop_distance: float
    capital_at_risk_pct: float


@dataclass(frozen=True)
class OpenPositionRisk:
    symbol: str
    asset_class: AssetClass
    risk_amount: float


@dataclass(frozen=True)
class PortfolioRiskDecision:
    approved: bool
    reason: str
    projected_total_risk_pct: float
    projected_asset_risk_pct: float


@dataclass(frozen=True)
class PortfolioRiskConfig:
    max_total_open_risk: float = 0.02
    max_equity_open_risk: float = 0.015
    max_crypto_open_risk: float = 0.01
    max_trades_per_day: int = 5
    cooldown_after_losses: int = 2


class RiskManager:
    def __init__(
        self,
        risk_per_trade: float,
        max_daily_loss: float,
        max_consecutive_losses: int,
    ) -> None:
        if risk_per_trade <= 0:
            raise ValueError("risk_per_trade must be greater than 0")
        if max_daily_loss <= 0:
            raise ValueError("max_daily_loss must be greater than 0")
        if max_consecutive_losses < 1:
            raise ValueError("max_consecutive_losses must be at least 1")

        self.risk_per_trade = risk_per_trade
        self.max_daily_loss = max_daily_loss
        self.max_consecutive_losses = max_consecutive_losses

    def calculate_position_size(
        self,
        capital: float,
        entry_price: float,
        stop_loss: float,
    ) -> PositionSize:
        if capital <= 0:
            raise ValueError("capital must be greater than 0")
        if entry_price <= 0 or stop_loss <= 0:
            raise ValueError("entry_price and stop_loss must be greater than 0")

        stop_distance = abs(entry_price - stop_loss)
        if stop_distance == 0:
            raise ValueError("stop_loss cannot equal entry_price")

        risk_amount = capital * self.risk_per_trade
        quantity = int(risk_amount // stop_distance)
        if quantity < 1:
            raise ValueError("capital is too small for this stop distance")

        actual_risk = quantity * stop_distance
        return PositionSize(
            quantity=quantity,
            risk_amount=actual_risk,
            stop_distance=stop_distance,
            capital_at_risk_pct=actual_risk / capital,
        )

    def is_kill_switch_active(
        self,
        capital: float,
        realized_daily_loss: float,
        consecutive_losses: int,
    ) -> bool:
        if capital <= 0:
            raise ValueError("capital must be greater than 0")

        daily_loss_pct = max(realized_daily_loss, 0) / capital
        return (
            daily_loss_pct >= self.max_daily_loss
            or consecutive_losses >= self.max_consecutive_losses
        )


class PortfolioRiskManager:
    def __init__(self, config: PortfolioRiskConfig | None = None) -> None:
        self.config = config or PortfolioRiskConfig()
        if self.config.max_total_open_risk <= 0:
            raise ValueError("max_total_open_risk must be greater than 0")
        if self.config.max_equity_open_risk <= 0:
            raise ValueError("max_equity_open_risk must be greater than 0")
        if self.config.max_crypto_open_risk <= 0:
            raise ValueError("max_crypto_open_risk must be greater than 0")
        if self.config.max_trades_per_day < 1:
            raise ValueError("max_trades_per_day must be at least 1")
        if self.config.cooldown_after_losses < 1:
            raise ValueError("cooldown_after_losses must be at least 1")

    def can_open_trade(
        self,
        capital: float,
        new_trade_risk_amount: float,
        new_trade_asset_class: AssetClass,
        open_positions: list[OpenPositionRisk],
        trades_taken_today: int,
        consecutive_losses: int,
    ) -> PortfolioRiskDecision:
        if capital <= 0:
            raise ValueError("capital must be greater than 0")
        if new_trade_risk_amount <= 0:
            raise ValueError("new_trade_risk_amount must be greater than 0")

        projected_total_risk = self._total_open_risk(open_positions) + new_trade_risk_amount
        projected_asset_risk = (
            self._asset_open_risk(open_positions, new_trade_asset_class)
            + new_trade_risk_amount
        )
        projected_total_risk_pct = projected_total_risk / capital
        projected_asset_risk_pct = projected_asset_risk / capital

        if trades_taken_today >= self.config.max_trades_per_day:
            return PortfolioRiskDecision(
                approved=False,
                reason="Daily trade limit reached",
                projected_total_risk_pct=projected_total_risk_pct,
                projected_asset_risk_pct=projected_asset_risk_pct,
            )

        if consecutive_losses >= self.config.cooldown_after_losses:
            return PortfolioRiskDecision(
                approved=False,
                reason="Cooldown active after consecutive losses",
                projected_total_risk_pct=projected_total_risk_pct,
                projected_asset_risk_pct=projected_asset_risk_pct,
            )

        if projected_total_risk_pct > self.config.max_total_open_risk:
            return PortfolioRiskDecision(
                approved=False,
                reason="Total open risk limit exceeded",
                projected_total_risk_pct=projected_total_risk_pct,
                projected_asset_risk_pct=projected_asset_risk_pct,
            )

        asset_limit = self._asset_limit(new_trade_asset_class)
        if projected_asset_risk_pct > asset_limit:
            return PortfolioRiskDecision(
                approved=False,
                reason=f"{new_trade_asset_class.value.title()} open risk limit exceeded",
                projected_total_risk_pct=projected_total_risk_pct,
                projected_asset_risk_pct=projected_asset_risk_pct,
            )

        return PortfolioRiskDecision(
            approved=True,
            reason="Trade approved",
            projected_total_risk_pct=projected_total_risk_pct,
            projected_asset_risk_pct=projected_asset_risk_pct,
        )

    def _total_open_risk(self, open_positions: list[OpenPositionRisk]) -> float:
        return sum(position.risk_amount for position in open_positions)

    def _asset_open_risk(
        self,
        open_positions: list[OpenPositionRisk],
        asset_class: AssetClass,
    ) -> float:
        return sum(
            position.risk_amount
            for position in open_positions
            if position.asset_class == asset_class
        )

    def _asset_limit(self, asset_class: AssetClass) -> float:
        if asset_class == AssetClass.EQUITY:
            return self.config.max_equity_open_risk
        if asset_class == AssetClass.CRYPTO:
            return self.config.max_crypto_open_risk
        raise ValueError(f"Unsupported asset class: {asset_class}")
