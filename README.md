# Stock averaging dashboard

Tracks one NSE/BSE stock's current price (CMP) against your average buy
price, asks Claude for a cautious, informational take on whether averaging
down makes sense, and shows it on a small dashboard — kept up to date
automatically by GitHub Actions.

## Setup

1. Push these files to a GitHub repo.
2. Edit `config.json` with your real ticker (`.NS` for NSE, `.BO` for BSE),
   quantity held, and average buy price.
3. Add an API key secret: repo **Settings -> Secrets and variables ->
   Actions -> New repository secret**, name it `ANTHROPIC_API_KEY`.
4. Enable Pages: **Settings -> Pages -> Source: Deploy from a branch ->
   `main` / `/docs`**.
5. Run it once by hand: **Actions tab -> "Stock averaging check" -> Run
   workflow**. The dashboard will be live at
   `https://<you>.github.io/<repo>/` a minute or two after that first run.

After that, it runs automatically on weekdays shortly after NSE market
close. Edit the `cron` line in `.github/workflows/stock-check.yml` to
change the schedule.

## How it works

- `analyze_stock.py` reads `config.json`, pulls the last two closes for
  your ticker via `yfinance`, computes P&L against your average buy price,
  and asks Claude (via a forced tool call, so the reply is always
  structured) for a verdict — then writes everything to `docs/data.json`.
- `docs/index.html` is a static page that just fetches `data.json` and
  renders it. No build step.
- The workflow re-runs the script on a schedule and commits the refreshed
  `docs/data.json`, so Pages always serves the latest numbers.

## Notes

- Prices come from Yahoo Finance — fine for a daily check-in, not built
  for live trading or minute-level data.
- The AI verdict is generated from price and P&L alone (no fundamentals,
  no news). It's informational, not financial advice — treat it as one
  input alongside your own research.
- To track a different stock later, just edit `config.json` and re-run
  the workflow.
