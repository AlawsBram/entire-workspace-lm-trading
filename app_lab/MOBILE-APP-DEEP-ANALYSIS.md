# MOBILE APP DEEP ANALYSIS — Polymarket Android 2.8.5 (decompiled)

Source: `polymarket-decompiled-2.8.5` (jadx 1.5.0 decompile of `com.polymarket.android`
v2.8.5 / versionCode 21647, from APKMirror). Analysis date: 2026-09-27.
Companion to `ui_lab/DEVTOOLS-DEEP-INSPECTION.md` (web). Extracted artifacts:
`app_lab/extracted/uslive_rpc_methods.txt` (275 RPC methods),
`app_lab/extracted/polymarket_urls.txt` (95 URLs).

---

## 1. WHAT THIS APP ACTUALLY IS (the headline)

**It is NOT the .com trading site in a wrapper. It is the Polymarket US
exchange app** — the regulated American venue:

- Legal docs are served from `www.polymarketexchange.com/files/legal/latest/`
  — **rulebook, participant-agreement, risk-disclosure-statement** (all
  versioned under `/latest/` — prime regime-watch targets).
- Hosts: `polymarket.us`, `app.polymarket.us`, `auth0.polymarket.us`,
  `tyc.polymarket.us` (terms), `cdn.polymarket.us`, `docs.polymarket.us`.
- **Zero `updown` strings in the entire binary** — the 5m/15m crypto up-or-down
  rounds do not exist in this product. They live only on `.com` (web), which
  this app embeds via a WebView bridge where needed.

**Architecture surprise:** the app is built with **Skip.tools** — Kotlin
projections over a **Swift codebase** compiled to native libraries. The Java
decompile is mostly SDK wiring; the actual business logic sits in
`libUSLive.so` (84 MB, one Swift binary) + `libFoundation*.so`. Everything in
this report comes from string-extracting those binaries (330k strings) plus
the Java layer. Internal module map (by symbol count): `PolymarketGatewayUS`
(49k), `USViewModels` (39k), `AppData` (38k), `PolymarketUnifiedAPI` (20k),
`AppClients` (8k), `ChartLogic`, `LiveClientWebSocket`, `LiveClientConnect`.
Wire format: **ConnectRPC / Protobuf** (not REST JSON for core calls).

---

## 2. ENDPOINT INVENTORY (prod + staging + preprod)

**Websockets (market data):**
| endpoint | purpose |
|---|---|
| `wss://gateway-ws-markets.polymarket.us/v1/ws/subscriptions` | market-level realtime |
| `wss://gateway-ws-users.polymarket.us/v1/ws/subscriptions` | user-level realtime (fills, orders) |
| `wss://sports-api.polymarket.us/ws` | live sports data feed |
| `wss://ws-live-data.polymarket.com` | **.com-side live data WS** (the only .com realtime in the binary) |
| each has `-staging.` and `-preprod.` twins | full env trio shipped in prod binary |

**REST/RPC gateways:**
- `https://gateway.polymarket.us` (+ `gateway-staging`, `gateway-preprod`) — ConnectRPC gateway (275 methods below)
- `https://unified-api.polymarket.us` (+staging/preprod) — unified domain API (home feed, search, squads, realtime)
- `https://polymarket.us/api` — web-API passthrough; `https://polymarket.us/auth/mobile` — mobile auth flow
- `https://cdn.polymarket.us` — images/notification icons
- `https://docs.polymarket.us` (+ `docs-polymarket-us.mintlify.app/polymarket-learn/home`) — docs on Mintlify
- `https://docs.polymarket.us/incentives/user-programs` — US incentive program docs
- `https://polymarket-upload.s3.us-east-2.amazonaws.com` — media bucket (sports logos, NBA/NFL/NHL/MLB/IPL assets, play-by-play soccer event icons, referral art)

**Everything missing vs web:** no gamma-api, no clob.polymarket.com, no
data-api, no RTDS `ws-subscriptions` of the .com CLOB — the US venue runs its
own stack. The .com CLOB endpoints we trade against remain web-only.

---

## 3. THE 275-METHOD RPC CATALOG (highlights)

Full list in `app_lab/extracted/uslive_rpc_methods.txt`. Notables:

**Markets & trading**
- `MarketService/GetMarketBook`, `GetMarketBBO` — order book / best bid-offer
- **`MarketService/GetMarketSettlement`** — settlement query endpoint
- `OrdersService/CreateOrder|CreateOrderList|PreviewOrder|ModifyOrder|CancelOrder|ClosePositionOrder` — full order lifecycle incl. batch lists
- `CombosService/CreateComboRFQ|AcceptComboQuote|PreviewCombo|ValidateCombo` — **parlay/combo trading via RFQ**
- `PriceHistoryService/GetPriceHistory`, `LiveTradeService/GetLiveTradeHistory`, `AssetPricesService/GetAssetPriceHistory`
- `MarketLiquiditySyncService/EnqueueMarketLiquiditySync` (+ `StagingLiquiditySync` debug strings)
- `IntervalsService/GetIntervals`, `SeriesService/GetSeries`

**Account / risk / integrity**
- `IntegrityCheckService/MintAppAttestChallenge`, `RegisterAppAttestKey`, `GetConfigurationParams` — **device attestation built into the app** (Apple App Attest pattern)
- `AccountService/GetAccountRestriction`, **`RestrictAccount`** — server-side account restriction
- `MFAPasskeyService/*` — passkeys + SMS MFA; `AuthService/LoginOrRegister|CreateGrant|RedeemSession|RefreshToken`
- Full KYC suite: `KYCService/StartKYCVerification|StartKYCPrefill|KYCHook`, OTP email flows, `IntercomService/GetRequiredDocs|UploadDoc|SubmitRFI` (KYC docs via Intercom!)
- `UsersService/SetDepositLimit|GetDepositLimitAudit` — responsible-gaming limits with audit trail

**Money**
- `PaymentsService/*` — Stripe (SetupIntents, Apple Pay sessions), AeroSync bank link, wire details, **`ListStablecoinDeposits|ListStablecoinWithdrawals|ListEligibleCryptoWallets|RegisterCryptoWalletPayoutMethod`** — stablecoin rails + crypto-wallet payouts
- `TaxDocumentsService/ListTaxDocuments|GetTaxDocumentDownloadUrl` — tax docs generated in-app (US venue = tax reporting)

**Engagement machine**
- `PromosService` (campaign enrollment), `ReferralCodesService`, `IncentivesService/ListIncentives|GetIncentivesEarned`, `CompetitionsService/JoinCompetition|ListLeaderboard`, `WaitlistCodesService`, `CalendarService` (tags + curated), `ReactionsService`
- `ChatService/JoinEventChat|JoinMarketChat|JoinTeamChat` (chat infra = GetStream + Ably in the SDK stack)
- `SquadUnifiedService` — 30+ methods for "squads" (social group positions, invites, member position feeds)

---

## 4. MARKET MECHANICS FOUND IN THE BINARY

- **Resolution-source templates** baked into the binary. Crypto touch markets:
  *"The resolution source for this market is **Binance's BTCUSDT 1-minute
  candles**"* (+ "or the equivalent USD pair on Binance for the asset listed").
  Election markets: AP/Fox/NBC consensus. **US-app crypto markets resolve off
  Binance candles — different oracle than the .com Chainlink TWAP-stream
  rounds.** Two venues, two resolution systems.
- **Tick size is server-driven and mutable**: `tick_size`, `min_tick_size`,
  `tick_size_change` / `tickSizeChangeUpdate` fields — the venue can change
  tick granularity per market at runtime (regime-watch item).
- **Display rounding taxonomy** (matches the web finding that ¢-rounding is
  render-side): `centsWhole`, `centsOnePlace`, `centsTwoPlaces`,
  `centsAdaptive`, `centsDouble` — five distinct cents-formatting modes.
- **Demo content shipped in prod**: `demo-position-btc`, `demo-member-position-btc`,
  `will-btc-hit-100k`, "Will Bitcoin hit $150k this year?", `sample.jpg`,
  `https://placehold.co`, `https://test-videos.co.uk`, `https://example.com`.

## 5. SURVEILLANCE / TELEMETRY STACK (mobile edition)

Manifest permissions: fine+coarse **location**, contacts, phone state, camera,
mic, NFC, biometrics, advertising ID (Google + Huawei). SDKs present:
**Amplitude** (+ `amplitudeExperimentDeploymentKey` — A/B & feature flags run
through Amplitude Experiment, not LaunchDarkly), **AppsFlyer**, **Braze**
(+ `BrazeService/CreateAuthToken` — push tokens minted server-side),
**Radar** (location SDK, `radarPublishableKey`, RadarJobScheduler exported),
**Sentry**, Intercom, Firebase, **Socure** + **FingerprintJS** + **Riskified**
+ Checkout.com risk + ML Kit/`libxeno_native` (document/face vision for KYC),
Pairip (Play Integrity). The web surveillance inventory from the DevTools
report has a full mobile twin, plus location.

**WebView telemetry hook:** the app injects JS that monkey-patches
`XMLHttpRequest.open/send` in embedded web pages, emitting
`{httpMethod, url, status, durationMs}` for every request — full network
performance monitoring of anything rendered in the WebView.
`PolyWebBridgePolicy` decides per-URI whether the native bridge is injected
(logic lives in the Swift binaries, not inspectable from Java).

## 6. DEBUG / LEFTOVER FINDINGS

- `https://mutable-wisplike-fanfare.ngrok-free.dev` (×3) — **dev ngrok tunnel
  shipped in the production binary**.
- `EnvironmentOverride` + staging/preprod endpoint trios — runtime environment
  switching compiled in.
- `DebugSettingsViewModel`, `NetworkScenario` (rule-based network-condition
  simulation), `ClientChatMock`, `StagingLiquiditySyncAllMarkets`.
- Build path leak: `/__w/mobile-app/mobile-app/polymarket-shared/...` →
  built on **GitHub Actions**, repo `mobile-app`, shared package
  `polymarket-shared`, output `USLive`.
- Deep link: `polymarket://legal-agreements`; onelink hosts for attribution.
- Intercom push receiver exported; several payment-SDK activities exported
  (standard, but noted for the attack-surface record).

## 7. CROSS-CHECK vs OUR WEB FINDINGS (manipulation lens)

| web finding | mobile finding | verdict |
|---|---|---|
| DPoP token binding (sunbreak) on .com API | **0 DPoP strings in the binary** | DPoP is web-session friction only; the US app uses Auth0 grants + session redemption + device attestation instead |
| itode 250ms taker delay (server-side, .com) | nothing analogous visible | mobile app targets the US venue; .com microstructure rules don't surface here |
| Rounding = render-side on web | five explicit client-side cents formats | consistent: display rounding is presentation everywhere, settlement stays full-precision |
| past-results endpoint hidden gem | US venue has **`GetMarketSettlement`** + `GetAssetPriceHistory` | new calibration sources for US markets if they ever matter to us |
| Engagement/surveillance machine | full mobile twin + location + App Attest + XHR hooking | the asymmetry thesis holds and extends to mobile |
| 5m crypto rounds = Chainlink TWAP stream | US crypto touch markets = **Binance 1m candles** | different oracle per venue/product — never assume resolution mechanics transfer |
| Rule layer = regime-watch target | `polymarketexchange.com/files/legal/latest/{rulebook,participant-agreement,risk-disclosure-statement}` | **new regime-watch feeds** — versioned legal docs, diffable |

**Bottom line for our work:** nothing here changes the S1/maker setup (those
target .com 5m rounds, absent from this app by design). What it adds: (1) the
US venue is a live, separate, regulated product with its own gateway/WS stack —
worth tracking as the template of where Polymarket is going; (2) concrete new
regime-watch URLs (legal docs + incentive docs); (3) confirmation that the
manipulation-relevant layers (delays, DPoP, rounding) are venue/product-scoped,
not account-scoped — no evidence anywhere in the mobile binary of per-user
price treatment either.

## 8. RECOMMENDED FOLLOW-UPS — status

1. ✅ **DONE (2026-09-27)** — regime_watch now diffs the three
   `polymarketexchange.com/files/legal/latest/*` PDFs + `docs.polymarket.us/incentives/user-programs`
   (`us-legal-rulebook/participant/risk`, `us-incentives-docs` sources).
2. ✅ **DONE (2026-09-27)** — gateway probed read-only, no auth: HealthCheck →
   `{"status":"ok"}`; `GetConfigs` → **entire live config store (83 keys: feature
   flags + payment kill switches) — now watched as `us-gateway-configs`**;
   `GetMarketSettlement` → 200 with a valid slug (`{"settlement":1}`);
   `GetMarketBook` → 200 with full market data (openPx/closePx/state/stats);
   `GetSeries`/`GetEvents` → fully readable (sports-only series, no crypto rounds).
   `GetAssetPriceHistory` accepts `crypto:btc` but needs a `bucket` proto field
   whose schema isn't exposed — recorded, not needed for watch.
3. ✅ **DONE (2026-09-27)** — implemented as the `us-venue-5m-sentinel` regime_watch
   source: every cycle scans US series + events + configs for updown/5m/twap
   patterns; on detection it fires a Telegram alert: "full oracle re-audit
   (Binance candles vs Chainlink TWAP) required before transferring ANY strategy
   assumption." Current status: NONE-DETECTED.
