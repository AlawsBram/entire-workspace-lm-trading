<!-- source: https://moondev.com/roadmap (section #crypto-data) -->
<!-- captured: 2026-10-07 · downloader UI, symbol/timeframe lists & API endpoints -->

# 📈 Crypto Data — data sources

## 📊 OHLCV Data Downloader

> Download clean Open, High, Low, Close, Volume data for major cryptocurrencies.
> Perfect for backtesting and machine learning projects.

### Supported cryptocurrencies (30)

| Symbol | Name | Ticker |
|---|---|---|
| BTC-USD | Bitcoin | BTC |
| ETH-USD | Ethereum | ETH |
| SOL-USD | Solana | SOL |
| ADA-USD | Cardano | ADA |
| XRP-USD | XRP | XRP |
| DOGE-USD | Dogecoin | DOGE |
| BCH-USD | Bitcoin Cash | BCH |
| LINK-USD | Chainlink | LINK |
| XLM-USD | Stellar | XLM |
| LTC-USD | Litecoin | LTC |
| HBAR-USD | Hedera | HBAR |
| AVAX-USD | Avalanche | AVAX |
| SUI-USD | Sui | SUI |
| SHIB-USD | Shiba Inu | SHIB |
| DOT-USD | Polkadot | DOT |
| UNI-USD | Uniswap | UNI |
| TON-USD | Toncoin | TON |
| NEAR-USD | NEAR Protocol | NEAR |
| APT-USD | Aptos | APT |
| ICP-USD | Internet Computer | ICP |
| TAO-USD | Bittensor | TAO |
| AAVE-USD | Aave | AAVE |
| ETC-USD | Ethereum Classic | ETC |
| RENDER-USD | Render | RENDER |
| OP-USD | Optimism | OP |
| ARB-USD | Arbitrum | ARB |
| ATOM-USD | Cosmos | ATOM |
| IMX-USD | Immutable | IMX |
| FIL-USD | Filecoin | FIL |
| INJ-USD | Injective | INJ |

### Timeframes

`1 Minute · 5 Minutes · 15 Minutes · 1 Hour · 4 Hours · 6 Hours · 1 Day`

Plus a **"Weeks of Data"** selector.

### 💡 Data Format

> CSV files with columns: `timestamp, open, high, low, close, volume`. Data is pulled
> from **Coinbase** via the **Moon Dev API**.

### How the downloader works (from the page's JS)

- API key stored in browser localStorage as `moondev_api_key`, sent as `X-API-Key` header.
- Start: `POST https://moondev.com/api/data-downloader/download` (`Content-Type: application/json`)
- Progress poll: `GET https://moondev.com/api/data-downloader/status/<id>`
- Result lands in the site's `/downloads/` area.
- UI messages: "Please select symbol and timeframe" · "Preparing download..." ·
  "Downloading data from Coinbase..." · "Download complete! *N* data points saved."
- Error path: "Server returned an unexpected response. The download may be too large —
  try fewer weeks." · "Download failed - please try again" · "Connection error. Please try again."
