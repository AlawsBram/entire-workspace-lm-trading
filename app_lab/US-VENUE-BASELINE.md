# US VENUE BASELINE MEASUREMENTS — gateway.polymarket.us (2026-09-27, from Nairobi)

Passive, read-only, unauthenticated. Modest volume (8 calls/endpoint; one short
WS session). Companion to `MOBILE-APP-DEEP-ANALYSIS.md`.

## 1. HTTP latency profile (gateway.polymarket.us, ConnectRPC/JSON, via Cloudflare)

| endpoint | p50 | p90 | max | payload | success |
|---|---|---|---|---|---|
| `HealthService/HealthCheck` | 125 ms | 142 ms | 179 ms | 15 B | 8/8 |
| `ConfigService/GetConfigs` (83 keys) | 213 ms | 263 ms | 296 ms | ~110 KB | 8/8 |
| `SeriesService/GetSeries` | 115 ms | 140 ms | 157 ms | ~14 KB | 8/8 |
| `EventsService/GetEvents` | 176 ms | 215 ms | 224 ms | ~184 KB | 8/8 |
| `MarketService/GetMarketSettlement` | 126 ms | 138 ms | 164 ms | 52 B | 8/8 |

Round-trip from East Africa comparable to .com's public APIs; no geo-blocking
observed. Config store payload (~110 KB) includes payment kill switches — now
diffed daily by regime_watch (`us-gateway-configs`).

## 2. Market websocket — `wss://gateway-ws-markets.polymarket.us/v1/ws/subscriptions`

Measured behavior:
- **Anonymous connections accepted** — TLS+WS handshake ~230 ms, no auth challenge.
- **No server greeting** — server stays silent until the client subscribes.
- **JSON control plane** — malformed client messages get `{"error":"invalid_message"}`;
  unsubscribe is acked with `{"requestId":"...","unsubscribed":true}`.

**PROTOCOL RECOVERED (2026-09-27)** by disassembling the Swift symbols in
`libUSLive.so` (`AppData.WSMarketsUSRequest`, `PolymarketGatewayUS.Ws_Markets_V1_*`),
then verified with one short live session per channel (full schema in
`app_lab/extracted/us_markets_ws_protocol.json`):

```json
{"subscribe": {"requestId": "<uuid>",
               "subscriptionType": "SUBSCRIPTION_TYPE_MARKET_DATA_LITE",
               "marketSlugs": ["<market-slug>"],
               "responsesDebounced": false}}
{"unsubscribe": {"requestId": "<uuid>"}}
```

- Markets-WS subscription types: `MARKET_DATA`, `MARKET_DATA_LITE`, `TRADE`
  (users-WS additionally: ORDER, ORDER_SNAPSHOT, POSITION, ACCOUNT_BALANCE, RFQ —
  those presumably require auth).
- `MARKET_DATA_LITE` pushes quote snapshots: currentPx, lastTradePx, settlementPx,
  bestBid/Ask + bidDepth/askDepth, bid/askShares, long/shortQuote, openInterest,
  sharesTraded, state, nanosecond timestamps.
- `TRADE` pushes the public tape: price, quantity, tradeTime(ns), **maker side +
  intent** (ORDER_SIDE_SELL / ORDER_INTENT_SELL_LONG...) — maker aggression is
  visible on the US tape.
- Live slugs for subscribing: `LiveService/GetLivePage` → walk `markets[].slug`
  (352 live markets observed during a Sunday session).
- The same response vocabulary (`subscription_update/snapshot/rejected`,
  `heartbeat`, `account_balances_*`, `order_subscription_*`, `position_subscription`,
  `rfq_event`) exists for the users-WS — untested (requires a logged-in session).

## 3. Path handling (read-only, on already-public data only)

| variant | result |
|---|---|
| exact method path | 200 |
| trailing slash | 404 (`404 page not found` — Go mux) |
| double slash | 307 redirect |
| `%2f` inside path | 404 (not decoded into routing) |

Strict exact-path routing; no normalization confusion on the public surface.

## 4. Stack fingerprint

Go + ConnectRPC/protobuf behind Cloudflare (Go mux 404 string, `*asset_pricesv1.…`
pointer-type error leaks, grpc-go error wrapping). Not FastAPI/Python.

## 5. Product discoveries (2026-09-27, post-WS-crack)

- **BTC Up-or-Down rounds are ALREADY LIVE on the US venue**: 15m and 60m
  horizons, 15-minute cadence, slug `btc-updown-15m-YYYY-MM-DD-HHMMz`.
  They are **search-only**: invisible to GetSeries/GetEvents, discoverable via
  `unified-api.polymarket.us` SearchUnifiedService (response `bag` carries
  events+markets). No 5m round exists yet. Sentinel patched to watch
  unified-search and normalize round timestamps.
- **Oracle**: CF Benchmarks BRTI — 60 prices in the last minute at each
  boundary, simple average, rounded 2dp, ties settle Up. NOT Binance, NOT
  Chainlink. `settlementPx` in the lite WS frame carries the resolved value.
- **Weather markets live**: NYC/MIA/SFO/LAX/MDW daily-high temp, $1°F buckets
  (`tc-temp-{city}high-{date}-{bucket}`), resolving off NWS Climatological
  Report (Daily) per named station (e.g. KNYC). They stream on the same
  anonymous WS. Measured: NWS forecast "high near 66" vs buckets ≤64=37.5¢ /
  65-66=52.5¢ / 66-67=12.5¢; **bucket sum 1.060** (buy-side overround).
- Full strategy synthesis: `REALTIME-STACK-PLAYBOOK.md`.

## 6. Discipline notes

- Authenticated surfaces (orders, account, payments) NOT probed — no credentials,
  and probing without authorization is out of scope by policy.
- Config store is read-only client-side: catalog has GetConfig/GetConfigs only;
  no Set/Update config RPC exists in the 275-method surface. Bonus/promo values
  are display config; crediting is server-side behind auth+KYC+risk stack.
- Refresh cadence: regime_watch re-measures config/series/legal-doc drift every
  10 min on the VPS; re-run this latency baseline monthly or after any regime alert.
