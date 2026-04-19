import pandas as pd

try:
    import vectorbt as vbt
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"vectorbt not installed: {exc}")


def run_backtest(csv_path: str) -> None:
    df = pd.read_csv(csv_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp")

    price = df["price"]
    entries = df["long_signal"].astype(bool)
    exits = df["exit_signal"].astype(bool)

    pf = vbt.Portfolio.from_signals(price, entries, exits, fees=0.0015, slippage=0.002)

    print("Total Return:", pf.total_return())
    print("Win Rate:", pf.trades.win_rate())
    print("Expectancy:", pf.trades.expectancy())
    print("Max Drawdown:", pf.max_drawdown())


if __name__ == "__main__":
    # Expected columns: timestamp, price, long_signal, exit_signal
    run_backtest("signals_backtest.csv")
