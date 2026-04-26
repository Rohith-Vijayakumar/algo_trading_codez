from sqlalchemy.orm import Session

from data.models import Trade


class TradeManager:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_trade(
        self,
        symbol: str,
        trade_type: str,
        entry_price: float,
        stop_loss: float,
        target_price: float,
        quantity: int,
    ) -> Trade:
        if trade_type not in {"BUY", "SELL"}:
            raise ValueError("trade_type must be BUY or SELL")
        if quantity < 1:
            raise ValueError("quantity must be at least 1")

        trade = Trade(
            symbol=symbol.upper(),
            trade_type=trade_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            quantity=quantity,
        )
        self.session.add(trade)
        self.session.commit()
        self.session.refresh(trade)
        return trade
