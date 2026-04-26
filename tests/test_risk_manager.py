from execution.risk_manager import RiskManager


def test_calculate_position_size_caps_risk() -> None:
    manager = RiskManager(
        risk_per_trade=0.005,
        max_daily_loss=0.02,
        max_consecutive_losses=3,
    )

    position = manager.calculate_position_size(
        capital=100000,
        entry_price=100,
        stop_loss=95,
    )

    assert position.quantity == 100
    assert position.risk_amount == 500
    assert position.capital_at_risk_pct == 0.005


def test_kill_switch_activates_on_daily_loss() -> None:
    manager = RiskManager(
        risk_per_trade=0.005,
        max_daily_loss=0.02,
        max_consecutive_losses=3,
    )

    assert manager.is_kill_switch_active(
        capital=100000,
        realized_daily_loss=2000,
        consecutive_losses=0,
    )
