# DEVTOOLS DEEP INSPECTION — polymarket.com, live BTC 5m page (2026-09-26)

**Method:** headless Chromium on `polymarket.com/event/btc-updown-5m-*`, 30 s of a live round; dumped every DevTools panel programmatically (Application → cookies/localStorage/sessionStorage/IndexedDB/service workers/manifest; Network → 693 requests + 3 websockets; Sources → 188 app JS bundles string-scanned). Raw dumps in `inspection/*.json`. Then each item analyzed against everything we've established so far (audit, UI-vs-API, fee machine, regime watch).

---

## 1. APPLICATION TAB

### Cookies (42) — four functional families

| family | cookies | what it is | manipulation lens |
|---|---|---|---|
| **Access control / WAF** | `cf_clearance`, `__cf_bm`, `__cf_ob`, Cloudflare challenge + `cdn-cgi/rum` | Cloudflare bot-management; the gate that decides who even loads the site; also Real-User-Monitoring | This is the *geoblock/enforcement* layer (with `/api/geoblock/wallet-lists`). The venue can exclude any wallet/region silently. Rule-layer power, again. |
| **Persistent identity graph** | `ajs_anonymous_id` (Segment), `htjs_*` (Hightouch CDP), `AMP_*` (Amplitude), `_ga/_gcl_au` (Google), `_fbp`+`fr` (Meta), `_ttp/_twsid/tt_*` (TikTok), `_scid` (Snap), `_rdt_uuid` (Reddit), `_twpid`+`guest_id*` (X), `IDE` (DoubleClick), `TapAd_*` (**cross-device ID sync**), `pm_eid`, `pm_attr_first` | One anonymous visitor gets stitched IDs for ~10 ad platforms, including TapAd, whose entire business is linking your phone/laptop identities | No price effect. This is the **acquisition machine**: the venue can find and re-target you on every platform after one visit, and optimize ad delivery toward people who convert into repeat takers. The growth side of the fee machine. |
| **First-party session** | `pm_geo`, `pm_eid`, `intercom-*` | geo flag, entity id, support chat | `pm_geo` confirms client-side geo handling. |
| **Server-side Conversions APIs (CAPI)** | (no cookie; endpoints `/api/{meta,tiktok,twitter,reddit,snapchat}/capi`, `/api/impact/page-load`) | The *server* reports your conversions to ad platforms directly, server-to-server — survives ad-blockers and cookie deletion | The deepest tracking tier. "Deposit made", "trade placed" can be conversion events fed back into ad targeting. Engagement optimization with cookie-immunity. |

**Verdict:** nothing here touches prices or books. But this is the closest thing the platform has to "manipulation" in the behavioral sense: a full-funnel re-targeting loop (pixels + CAPI + TapAd + Braze push) aimed at bringing you back to a 288×/day product. It is the infrastructure behind the article's "designed for engagement, not information".

### LocalStorage / SessionStorage
- `poly_feature_flag_enrollments.v2` — client **A/B experiment enrollment** (variant per flag; observed: `google_one_tap`). Capability to show different UIs to different users exists; **no evidence it touches prices** (prices arrive via shared public websockets, same for every tab).
- `polymarket.cache.rq`, `polymarket.store.parlays`, `polymarket.cache.wagmi.v2.store` — react-query cache, combo-bet slip state, wallet state. Benign plumbing.
- `gist.web.*` (Customer.io), `intercom.intercom-state`, `htjs_sesh`, `AMP_*` — marketing/analytics session state. AMP's remote config confirms **session replay sampling: 2%** (`sessionReplay … sampleRate 0.02`) — a sampled subset of users' full screen interactions are recorded.
- `pm_balances_v2` cookie written by JS with 2dp-rounded balances — cosmetic rounding, display-only (matches finding: rounding lives in rendering, not settlement).

### IndexedDB (5)
| db | role | lens |
|---|---|---|
| `MagicAuthLocalStorageDB` (2 rec) | **Magic Link** email auth session keys on-device | email compromise = session compromise; custodial-adjacent. Present even logged-out (SDK preloaded). |
| `WALLET_CONNECT_V2_INDEXED_DB`, `mmconnect-kv-store` | WalletConnect / MetaMask persistence | standard wallet plumbing |
| `sunbreak-kv` (5 rec) + `sunbreak_dpop_meta_v1` localStorage | "sunbreak" = Polymarket's session/auth service; **DPoP** (proof-of-possession bound tokens) | actually good security practice (sender-constrained sessions); also means even anonymous browsers get a device-bound client identity server-side |
| `AMP_diagnostics_…` | Amplitude diagnostics / replay buffer | part of the 2% replay pipeline |

### Service workers & manifest
- **`/~partytown/partytown-sw.js`** — Partytown runs the whole third-party marketing stack in a web worker: the tracking becomes invisible in page-perf terms and keeps running off-thread. Performance trick + opacity.
- Manifest 403 to bot UAs (Cloudflare) — PWA installability for real users: home-screen icon, push-capable app shell. More engagement surface.

---

## 2. NETWORK TAB — the hidden first-party API layer

| endpoint | what it is | lens |
|---|---|---|
| `polymarket.com/api/crypto/crypto-price?symbol=BTC&variant=fiveminute&eventStartTime=…` | **the UI's price source** — returns `openPrice` at FULL precision with `cached:true, incomplete:true` | Confirms: a **server-side cache** sits between oracle and UI; the cents-rounding happens in JS at render. The cached flag is the staleness we measured (UI price = smoothed TWAP, refresh-lagged). |
| `polymarket.com/api/market/resolution/{conditionId}` | UI's resolution fetch (`data:null` until final) | A second, undocumented resolution path besides gamma. Two paths = two things to watch; our arbiter uses gamma + on-chain semantics. |
| `polymarket.com/api/past-results?symbol=BTC&variant=fiveminute…` | **full-precision open/close/outcome history of every round** | Research gold: bulk round history with `openPrice`, `closePrice`, `outcome`, `percentChange` — a proper backtest corpus the docs never advertised. ✅ **Built & backfilled — with one major catch found by follow-up audit:** its `outcome` field is derived (= sign(close−open)) and is wrong on 28–35% of sub-2bp rounds; authoritative outcomes come from the gamma series (full history to 2025-12-18) or the on-chain CTF payout vector. See `maker_lab/history/HISTORY-FINDINGS.md`. |
| `polymarket.com/api/geoblock/wallet-lists` | client-fetched enforcement lists | the exclusion mechanism, visible in the open. |
| `ws-subscriptions-frontend-clob.polymarket.com/ws/market` | **frontend-dedicated CLOB websocket**, separate from the public CLOB ws our stack uses | The UI's book/odds feed is a different pipe; part of why UI ¢ labels lag the public book by 2–13¢ (measured). |
| `polygon-mainnet.g.alchemy.com` | on-chain reads via Alchemy (third-party RPC sees the page's queries) | minor data-sharing note |
| `auth.magic.link` (iframe) + `api.sunbreak.com` | auth infra present even logged-out | identity plumbing |
| `wss://ws-live-data.polymarket.com` | RTDS — the same public feed our harness uses | ✔ shared truth source; UI and we drink from the same tap for the TWAP display |
| Intercom nexus ws, `cdp.customer.io`, Braze, Amplitude, GA, pixels | engagement/analytics chatter | see cookie family 2 |

---

## 3. SOURCES TAB — 188 JS bundles string-scanned

- **Rounding is render-side, tick-aware:** `getPrecisionFromTickSize`, `parseFloat(x.toFixed(r))` on `lastTradePrice`, `Math.round(100·outcomePrice)` for ¢ labels → the ¢ labels are rounded *last-trade* prices — exactly the lag/offset pattern we measured against the live book.
- `calculateWorstSellPrice` / slippage guards — client-side execution cosmetics for perps; irrelevant to our markets.
- **`priceMarketsUiEnabled` feature flag** (+`variant`, `eventStartTime`) — the 5-minute product surface itself is flag-gated; new regimes can ship as a flag flip. (Regime-watch's docs diff + sentinel fields cover the server side; UI flags are client-side presentation.)
- **No** client-side `seconds_delay` / `itode` / speed-bump logic → execution delays are enforced **server-side**, matching the docs. Our watcher's approach (read the market object) is the right one.
- No per-user price personalization logic found; prices come from shared feeds + the cached first-party endpoint.

---

## 4. THE MANIPULATION QUESTION — synthesized verdicts

1. **Price manipulation / discrimination against retail: no evidence.** Every user's UI is rendered from the same public RTDS feed + one cached first-party endpoint; rounding and smoothing are uniform, cosmetic-or-structural-but-equal. The asymmetries that matter are **not hidden in the browser** — they are in the rule layer (fees 1.75%, rebates 20%, delays, resolution docs) which we already monitor, and in information economics (bots on Binance feeds vs retail on a cached, smoothed, rounded display).
2. **The browser is where the engagement machine lives**: Braze/customer.io lifecycle pushes, Intercom, Partytown-hidden trackers, TapAd cross-device stitching, CAPI server-side conversions, PWA shell, 2% session replay. This is the operationalization of the Dyutam thesis ("designed for engagement, not information") — and the retail P&L distribution the EU measured is what this machine optimizes toward.
3. **Surveillance asymmetry mirrors the integrity gap**: the venue can reconstruct any user's full behavior (RUM + replay + CDP); retail has zero reciprocal visibility — which is why our stack measures everything itself (arbiter, regime watch, ui-lab) instead of trusting displays.
4. **Auth notes for your burner setup:** Magic email auth ties a wallet session to an email account; WalletConnect persists pairings; use neither for the burner — raw private key in `.env` (as in the runbook) remains the least-surprised path. DPoP/sunbreak is for their relayer sessions, not something you configure.
5. **New asset found:** `/api/past-results` exposes the full-precision round history the docs never mention — a free historical corpus for the arbiter and the maker simulator.

**Recommended additions to the stack** (cheap, high value):
- ~~`history_backfill.py` — pull `past-results` history into the lab for backtest calibration.~~ **Done** → `maker_lab/history_backfill.py` (run daily to keep the rolling 7-day corpus fresh).
- Keep `ui-lab` running as the standing UI-layer control (it would catch any future render-side change: new rounding, new caching, new flags).
- Nothing in trader/maker code changes as a result of this inspection.
