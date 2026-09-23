"""
analyze_stock.py — fetches the current market price (CMP) for one NSE/BSE
stock, computes P&L against your average buy price, asks Claude whether
averaging down at this price is worth considering, and writes the result
to docs/data.json for the dashboard to read.

Config lives in config.json: { "ticker": "...", "quantity": N, "avg_buy_price": N }
Requires the ANTHROPIC_API_KEY environment variable (set as a repo secret
in GitHub Actions).
"""

import json
import datetime
from pathlib import Path

import yfinance as yf
from anthropic import Anthropic

CONFIG_PATH = Path("config.json")
OUTPUT_PATH = Path("docs/data.json")
MODEL = "claude-sonnet-4-6"

# A tool schema forces Claude to answer in a fixed, parseable shape instead
# of free text we'd have to hope is valid JSON.
VERDICT_TOOL = {
    "name": "give_verdict",
    "description": "Give a cautious, informational verdict on whether averaging down makes sense right now.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "description": "A short (2-4 word) framing, e.g. 'Worth considering', 'Too early', 'Needs more data' — never a direct buy/sell instruction.",
            },
            "reasoning": {
                "type": "string",
                "description": "2-3 sentences explaining the reasoning in plain language.",
            },
            "considerations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "3-5 short factors a holder should weigh themselves before deciding.",
            },
        },
        "required": ["verdict", "reasoning", "considerations"],
    },
}


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def fetch_price(ticker: str) -> tuple[float, float]:
    hist = yf.Ticker(ticker).history(period="5d")
    if len(hist) < 2:
        raise RuntimeError(f"Not enough price history for {ticker}")
    cmp_price = float(hist["Close"].iloc[-1])
    prev_close = float(hist["Close"].iloc[-2])
    day_change_pct = (cmp_price - prev_close) / prev_close * 100
    return cmp_price, day_change_pct


def ask_claude(ticker, cmp_price, avg_buy_price, pnl_pct, day_change_pct) -> dict:
    client = Anthropic()
    prompt = (
        f"A retail investor holds {ticker} at an average buy price of "
        f"Rs {avg_buy_price:.2f}. The current market price (CMP) is "
        f"Rs {cmp_price:.2f}, a {day_change_pct:+.2f}% move today. Their "
        f"position is currently at {pnl_pct:+.2f}% P&L. Based only on this "
        f"price and P&L picture (you have no fundamentals, no news, and no "
        f"technical data), give a cautious, informational take on whether "
        f"averaging down here is worth considering. This is not financial "
        f"advice — be explicit about that in your reasoning, and flag that "
        f"a real decision needs fundamentals, news, and the investor's own "
        f"risk tolerance and conviction in the stock."
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=600,
        tools=[VERDICT_TOOL],
        tool_choice={"type": "tool", "name": "give_verdict"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError("Claude did not return a verdict")


def main():
    config = load_config()
    ticker = config["ticker"]
    quantity = config["quantity"]
    avg_buy_price = config["avg_buy_price"]

    cmp_price, day_change_pct = fetch_price(ticker)

    invested_value = quantity * avg_buy_price
    current_value = quantity * cmp_price
    pnl_value = current_value - invested_value
    pnl_pct = pnl_value / invested_value * 100

    verdict = ask_claude(ticker, cmp_price, avg_buy_price, pnl_pct, day_change_pct)

    data = {
        "ticker": ticker,
        "cmp": round(cmp_price, 2),
        "day_change_pct": round(day_change_pct, 2),
        "quantity": quantity,
        "avg_buy_price": avg_buy_price,
        "invested_value": round(invested_value, 2),
        "current_value": round(current_value, 2),
        "pnl_value": round(pnl_value, 2),
        "pnl_pct": round(pnl_pct, 2),
        "ai_verdict": verdict["verdict"],
        "ai_reasoning": verdict["reasoning"],
        "ai_considerations": verdict["considerations"],
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(data, indent=2))
    print(f"Wrote {OUTPUT_PATH}: {ticker} CMP Rs {cmp_price:.2f}, verdict: {verdict['verdict']}")


if __name__ == "__main__":
    main()
