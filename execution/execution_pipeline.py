from dataclasses import dataclass
from typing import Any

from execution.risk_manager import (
    AssetClass,
    OpenPositionRisk,
    PortfolioRiskManager,
    RiskManager,
)
from execution.trade_manager import TradeManager
from strategy.trend_strategy import SignalType, StrategySignal


@dataclass(frozen=True)
class ExecutionRequest:
    signal: StrategySignal
    asset_class: AssetClass
    capital: float
    open_positions: list[OpenPositionRisk]
    trades_taken_today: int
    realized_daily_loss: float
    consecutive_losses: int


@dataclass(frozen=True)
class ExecutionDecision:
    approved: bool
    reason: str
    quantity: int = 0
    risk_amount: float = 0.0
    trade: Any | None = None


class ExecutionPipeline:
    def __init__(
        self,
        risk_manager: RiskManager,
        portfolio_risk_manager: PortfolioRiskManager,
        trade_manager: TradeManager,
    ) -> None:
        self.risk_manager = risk_manager
        self.portfolio_risk_manager = portfolio_risk_manager
        self.trade_manager = trade_manager

    def process_signal(self, request: ExecutionRequest) -> ExecutionDecision:
        signal = request.signal
        if signal.signal == SignalType.HOLD:
            return ExecutionDecision(approved=False, reason=signal.reason or "Signal is HOLD")

        if not signal.entry_price or not signal.stop_loss or not signal.target_price:
            return ExecutionDecision(
                approved=False,
                reason="Signal is missing entry, stop, or target",
            )

        if self.risk_manager.is_kill_switch_active(
            capital=request.capital,
            realized_daily_loss=request.realized_daily_loss,
            consecutive_losses=request.consecutive_losses,
        ):
            return ExecutionDecision(approved=False, reason="Kill switch active")

        position = self.risk_manager.calculate_position_size(
            capital=request.capital,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
        )
        portfolio_decision = self.portfolio_risk_manager.can_open_trade(
            capital=request.capital,
            new_trade_risk_amount=position.risk_amount,
            new_trade_asset_class=request.asset_class,
            open_positions=request.open_positions,
            trades_taken_today=request.trades_taken_today,
            consecutive_losses=request.consecutive_losses,
        )
        if not portfolio_decision.approved:
            return ExecutionDecision(
                approved=False,
                reason=portfolio_decision.reason,
                quantity=position.quantity,
                risk_amount=position.risk_amount,
            )

        trade = self.trade_manager.create_trade(
            symbol=signal.symbol,
            trade_type=signal.signal.value,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            target_price=signal.target_price,
            quantity=position.quantity,
        )
        return ExecutionDecision(
            approved=True,
            reason="Trade created",
            quantity=position.quantity,
            risk_amount=position.risk_amount,
            trade=trade,
        )
