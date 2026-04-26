import pytest

from data.market_data import MarketDataError, MarketDataLoader


def test_load_csv_normalizes_columns_and_sorts_by_timestamp(tmp_path) -> None:
    csv_path = tmp_path / "candles.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Date,Ticker,Open,High,Low,Close,Vol",
                "2026-01-02,RELIANCE,102,106,101,105,1200",
                "2026-01-01,RELIANCE,100,104,99,103,1000",
            ]
        )
    )

    candles = MarketDataLoader().load_csv(csv_path)

    assert list(candles.columns) == [
        "timestamp",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]
    assert candles.iloc[0]["close"] == 103
    assert candles.iloc[1]["close"] == 105


def test_load_csv_filters_by_symbol(tmp_path) -> None:
    csv_path = tmp_path / "candles.csv"
    csv_path.write_text(
        "\n".join(
            [
                "timestamp,symbol,open,high,low,close,volume",
                "2026-01-01,RELIANCE,100,104,99,103,1000",
                "2026-01-01,TCS,200,204,198,203,2000",
            ]
        )
    )

    candles = MarketDataLoader().load_csv(csv_path, symbol="tcs")

    assert len(candles) == 1
    assert candles.iloc[0]["symbol"] == "TCS"
    assert candles.iloc[0]["close"] == 203


def test_load_csv_rejects_missing_required_columns(tmp_path) -> None:
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("timestamp,open,high,low,close\n2026-01-01,100,104,99,103\n")

    with pytest.raises(MarketDataError, match="missing required columns: volume"):
        MarketDataLoader().load_csv(csv_path)


def test_load_csv_rejects_invalid_price_relationships(tmp_path) -> None:
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text(
        "timestamp,open,high,low,close,volume\n"
        "2026-01-01,100,99,101,103,1000\n"
    )

    with pytest.raises(MarketDataError, match="high is below low"):
        MarketDataLoader().load_csv(csv_path)


def test_load_csv_rejects_unknown_symbol(tmp_path) -> None:
    csv_path = tmp_path / "candles.csv"
    csv_path.write_text(
        "timestamp,symbol,open,high,low,close,volume\n"
        "2026-01-01,RELIANCE,100,104,99,103,1000\n"
    )

    with pytest.raises(MarketDataError, match="No candles found for symbol: TCS"):
        MarketDataLoader().load_csv(csv_path, symbol="TCS")
