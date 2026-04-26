from execution.risk_manager import (
    AssetClass,
    OpenPositionRisk,
    PortfolioRiskConfig,
    PortfolioRiskManager,
)


def test_approves_trade_within_portfolio_limits() -> None:
    manager = PortfolioRiskManager()
    open_positions = [
        OpenPositionRisk("RELIANCE", AssetClass.EQUITY, risk_amount=500),
    ]

    decision = manager.can_open_trade(
        capital=100000,
        new_trade_risk_amount=500,
        new_trade_asset_class=AssetClass.EQUITY,
        open_positions=open_positions,
        trades_taken_today=1,
        consecutive_losses=0,
    )

    assert decision.approved
    assert decision.reason == "Trade approved"
    assert decision.projected_total_risk_pct == 0.01


def test_rejects_trade_when_total_open_risk_limit_is_exceeded() -> None:
    manager = PortfolioRiskManager(PortfolioRiskConfig(max_total_open_risk=0.015))
    open_positions = [
        OpenPositionRisk("RELIANCE", AssetClass.EQUITY, risk_amount=1000),
    ]

    decision = manager.can_open_trade(
        capital=100000,
        new_trade_risk_amount=600,
        new_trade_asset_class=AssetClass.EQUITY,
        open_positions=open_positions,
        trades_taken_today=1,
        consecutive_losses=0,
    )

    assert not decision.approved
    assert decision.reason == "Total open risk limit exceeded"


def test_rejects_trade_when_asset_risk_limit_is_exceeded() -> None:
    manager = PortfolioRiskManager(PortfolioRiskConfig(max_crypto_open_risk=0.008))
    open_positions = [
        OpenPositionRisk("BTC", AssetClass.CRYPTO, risk_amount=500),
    ]

    decision = manager.can_open_trade(
        capital=100000,
        new_trade_risk_amount=400,
        new_trade_asset_class=AssetClass.CRYPTO,
        open_positions=open_positions,
        trades_taken_today=1,
        consecutive_losses=0,
    )

    assert not decision.approved
    assert decision.reason == "Crypto open risk limit exceeded"


def test_rejects_trade_after_daily_trade_limit() -> None:
    manager = PortfolioRiskManager(PortfolioRiskConfig(max_trades_per_day=2))

    decision = manager.can_open_trade(
        capital=100000,
        new_trade_risk_amount=500,
        new_trade_asset_class=AssetClass.EQUITY,
        open_positions=[],
        trades_taken_today=2,
        consecutive_losses=0,
    )

    assert not decision.approved
    assert decision.reason == "Daily trade limit reached"


def test_rejects_trade_during_loss_cooldown() -> None:
    manager = PortfolioRiskManager(PortfolioRiskConfig(cooldown_after_losses=2))

    decision = manager.can_open_trade(
        capital=100000,
        new_trade_risk_amount=500,
        new_trade_asset_class=AssetClass.EQUITY,
        open_positions=[],
        trades_taken_today=1,
        consecutive_losses=2,
    )

    assert not decision.approved
    assert decision.reason == "Cooldown active after consecutive losses"
