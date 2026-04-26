from pathlib import Path

import pandas as pd


REQUIRED_OHLCV_COLUMNS = {"open", "high", "low", "close", "volume"}
COLUMN_ALIASES = {
    "date": "timestamp",
    "datetime": "timestamp",
    "time": "timestamp",
    "ticker": "symbol",
    "instrument": "symbol",
    "vol": "volume",
}


class MarketDataError(ValueError):
    pass


class MarketDataLoader:
    def load_csv(
        self,
        file_path: str | Path,
        symbol: str | None = None,
    ) -> pd.DataFrame:
        path = Path(file_path)
        if not path.exists():
            raise MarketDataError(f"Market data file does not exist: {path}")
        if not path.is_file():
            raise MarketDataError(f"Market data path is not a file: {path}")

        candles = pd.read_csv(path)
        candles = self._normalize_columns(candles)
        candles = self._filter_symbol(candles, symbol)
        candles = self._parse_timestamp(candles)
        self._validate_columns(candles)
        candles = self._coerce_ohlcv(candles)
        self._validate_values(candles)
        candles = self._sort(candles)

        ordered_columns = [
            column
            for column in ["timestamp", "symbol", "open", "high", "low", "close", "volume"]
            if column in candles.columns
        ]
        return candles[ordered_columns].reset_index(drop=True)

    def _normalize_columns(self, candles: pd.DataFrame) -> pd.DataFrame:
        normalized = candles.copy()
        normalized.columns = [
            COLUMN_ALIASES.get(str(column).strip().lower(), str(column).strip().lower())
            for column in normalized.columns
        ]
        return normalized

    def _filter_symbol(self, candles: pd.DataFrame, symbol: str | None) -> pd.DataFrame:
        if symbol is None:
            return candles
        if "symbol" not in candles.columns:
            raise MarketDataError("CSV must include a symbol column when symbol filter is used")

        filtered = candles[candles["symbol"].astype(str).str.upper() == symbol.upper()]
        if filtered.empty:
            raise MarketDataError(f"No candles found for symbol: {symbol.upper()}")
        return filtered.copy()

    def _parse_timestamp(self, candles: pd.DataFrame) -> pd.DataFrame:
        if "timestamp" not in candles.columns:
            return candles

        parsed = candles.copy()
        parsed["timestamp"] = pd.to_datetime(parsed["timestamp"], errors="coerce")
        if parsed["timestamp"].isna().any():
            raise MarketDataError("CSV contains invalid timestamp values")
        return parsed

    def _validate_columns(self, candles: pd.DataFrame) -> None:
        missing_columns = REQUIRED_OHLCV_COLUMNS.difference(candles.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise MarketDataError(f"CSV is missing required columns: {missing}")

    def _coerce_ohlcv(self, candles: pd.DataFrame) -> pd.DataFrame:
        coerced = candles.copy()
        for column in REQUIRED_OHLCV_COLUMNS:
            coerced[column] = pd.to_numeric(coerced[column], errors="coerce")
            if coerced[column].isna().any():
                raise MarketDataError(f"CSV contains non-numeric values in column: {column}")
        return coerced

    def _validate_values(self, candles: pd.DataFrame) -> None:
        if (candles[list(REQUIRED_OHLCV_COLUMNS)] < 0).any().any():
            raise MarketDataError("CSV contains negative OHLCV values")
        if (candles["high"] < candles["low"]).any():
            raise MarketDataError("CSV contains rows where high is below low")
        if (candles["open"] > candles["high"]).any() or (candles["open"] < candles["low"]).any():
            raise MarketDataError("CSV contains rows where open is outside high-low range")
        if (candles["close"] > candles["high"]).any() or (candles["close"] < candles["low"]).any():
            raise MarketDataError("CSV contains rows where close is outside high-low range")

    def _sort(self, candles: pd.DataFrame) -> pd.DataFrame:
        if "timestamp" in candles.columns:
            return candles.sort_values("timestamp")
        return candles
