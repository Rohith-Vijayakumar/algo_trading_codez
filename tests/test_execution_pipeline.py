from dataclasses import dataclass

from execution.execution_pipeline import ExecutionPipeline, ExecutionRequest
from execution.risk_manager import (
    AssetClass,
    OpenPositionRisk,
    PortfolioRiskConfig,
    PortfolioRiskManager,
    RiskManager,
)
from strategy.trend_strategy import SignalType, StrategySignal


@dataclass(frozen=True)
class FakeTrade:
    symbol: str
    trade_type: str
    entry_price: float
    stop_loss: float
    target_price: float
    quantity: int


class FakeTradeManager:
    def __init__(self) -> None:
        self.created_trades: list[FakeTrade] = []

    def create_trade(
        self,
        symbol: str,
        trade_type: str,
        entry_price: float,
        stop_loss: float,
        target_price: float,
        quantity: int,
    ) -> FakeTrade:
        trade = FakeTrade(
            symbol=symbol,
            trade_type=trade_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            quantity=quantity,
        )
        self.created_trades.append(trade)
        return trade


def build_pipeline(
    trade_manager: FakeTradeManager,
    portfolio_config: PortfolioRiskConfig | None = None,
) -> ExecutionPipeline:
    return ExecutionPipeline(
        risk_manager=RiskManager(
            risk_per_trade=0.005,
            max_daily_loss=0.02,
            max_consecutive_losses=3,
        ),
        portfolio_risk_manager=PortfolioRiskManager(portfolio_config),
        trade_manager=trade_manager,
    )


def build_request(
    signal: StrategySignal,
    open_positions: list[OpenPositionRisk] | None = None,
    trades_taken_today: int = 0,
    realized_daily_loss: float = 0,
    consecutive_losses: int = 0,
) -> ExecutionRequest:
    return ExecutionRequest(
        signal=signal,
        asset_class=AssetClass.EQUITY,
        capital=100000,
        open_positions=open_positions or [],
        trades_taken_today=trades_taken_today,
        realized_daily_loss=realized_daily_loss,
        consecutive_losses=consecutive_losses,
    )


def test_pipeline_creates_trade_when_signal_and_risk_checks_pass() -> None:
    trade_manager = FakeTradeManager()
    pipeline = build_pipeline(trade_manager)
    signal = StrategySignal(
        signal=SignalType.BUY,
        symbol="RELIANCE",
        entry_price=100,
        stop_loss=95,
        target_price=110,
    )

    decision = pipeline.process_signal(build_request(signal))

    assert decision.approved
    assert decision.reason == "Trade created"
    assert decision.quantity == 100
    assert decision.risk_amount == 500
    assert len(trade_manager.created_trades) == 1
    assert trade_manager.created_trades[0].symbol == "RELIANCE"


def test_pipeline_rejects_hold_signal_without_creating_trade() -> None:
    trade_manager = FakeTradeManager()
    pipeline = build_pipeline(trade_manager)
    signal = StrategySignal(signal=SignalType.HOLD, symbol="RELIANCE", reason="No setup")

    decision = pipeline.process_signal(build_request(signal))

    assert not decision.approved
    assert decision.reason == "No setup"
    assert trade_manager.created_trades == []


def test_pipeline_rejects_when_kill_switch_is_active() -> None:
    trade_manager = FakeTradeManager()
    pipeline = build_pipeline(trade_manager)
    signal = StrategySignal(
        signal=SignalType.BUY,
        symbol="RELIANCE",
        entry_price=100,
        stop_loss=95,
        target_price=110,
    )

    decision = pipeline.process_signal(
        build_request(signal, realized_daily_loss=2500)
    )

    assert not decision.approved
    assert decision.reason == "Kill switch active"
    assert trade_manager.created_trades == []


def test_pipeline_rejects_when_portfolio_risk_fails() -> None:
    trade_manager = FakeTradeManager()
    pipeline = build_pipeline(
        trade_manager,
        PortfolioRiskConfig(max_total_open_risk=0.007),
    )
    signal = StrategySignal(
        signal=SignalType.BUY,
        symbol="TCS",
        entry_price=100,
        stop_loss=95,
        target_price=110,
    )
    open_positions = [
        OpenPositionRisk("RELIANCE", AssetClass.EQUITY, risk_amount=500),
    ]

    decision = pipeline.process_signal(
        build_request(signal, open_positions=open_positions)
    )

    assert not decision.approved
    assert decision.reason == "Total open risk limit exceeded"
    assert decision.quantity == 100
    assert trade_manager.created_trades == []
