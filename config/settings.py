from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./algo_trading.db"
    risk_per_trade: float = 0.005
    max_daily_loss: float = 0.02
    max_consecutive_losses: int = 3
    max_total_open_risk: float = 0.02
    max_equity_open_risk: float = 0.015
    max_crypto_open_risk: float = 0.01
    max_trades_per_day: int = 5
    cooldown_after_losses: int = 2

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
