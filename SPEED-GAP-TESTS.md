# Can the speed gap actually be closed? — testing all four proposals

**Measured:** 2026-10-22, 15:44–16:08 HKT, against live HKO and Polymarket endpoints.
**Method:** a 6-way source race polling every ~1 s across three publish cycles, plus archive forensics on Sep 19, plus real order signing.
**One caveat up front:** my network vantage point is US-West (Google Cloud, Oregon). Your VPS is in NL. Absolute latencies will differ — the *orderings* and the HKO publish lag should hold, but re-run the race from your box before you commit.

> I'm explaining this in simple language a 15 year old can understand:

---

## 0. Verdict on your four items

| # | Your proposal | Possible? | Verdict |
|---|---|---|---|
| **1** | A faster source than the text page | **Partly — and you had it backwards** | ✅ There IS a faster source, but **nothing is faster than the text page**. The text page is **34–40 s ahead of the CSVs we currently use**. Everything else (API, 1-min files, humidity, pressure) is **33–59 s slower**. |
| **2** | Pre-armed signed orders | ✅ Yes, technically clean | ⚠️ Works, but saves **0.69 ms** of a ~160 ms chain. **Not worth building as a speed measure.** |
| **3** | Hold at 2 s polling | ✅ Right instinct | ✅ Correct, but for a better reason than you gave — and it can be made **~7× cheaper** by polling only around the publish window. |
| **4** | Server location is a wash | ✅ For latency, yes | ❌ **Not a wash for access.** NL is *close-only on the frontend but the API is unrestricted*. US is fully blocked. And Polymarket offers **co-location in eu-west-2**. |

**The single biggest measured fact:** HKO publishes **7–8 minutes after the observation timestamp**. That dwarfs every millisecond you and I could ever engineer.

---

## 1. The publish lag — the number that reframes everything

I timestamped the exact moment each file first showed a new stamp:

| Observation stamp | File first showed it | Lag after the stamp |
|---|---|---|
| 15:30 | CSV `since_midnight` 15:48:13 | 18 m 13 s (missed the start) |
| **15:40** | CSV `since_midnight` 15:48:13 | **8 m 13 s** |
| **15:50** | **text page 15:57:15** | **7 m 15 s** |
| 15:50 | CSV `since_midnight` 15:57:55 | 7 m 55 s |
| **16:00** | **text page 16:07:42** | **7 m 42 s** |

Read that as a 15-year-old would: HKO stamps the data "15:50", but it does not appear on the internet until about **15:57**. Every bot in the world is blind for those seven minutes. **No amount of Rust, WebSockets or parallelism fixes that** — the data does not exist yet.

So the total lead time available to anybody is:

```
observation  →[7-8 min, fixed by HKO]→  published  →[your detection]→  your order
```

The only parts you control are the last two arrows.

---

## 2. Item 1 — is there a faster source? Yes, and it is not the one you expected

I raced six candidate sources, polling each about once per second, and recorded the first moment each showed the new stamp. The 15:50 cycle is the clean one (all six fired):

| Source | First showed 15:50 | vs text page | Fetch time |
|---|---|---|---|
| **`text_readings_e.htm` (the HTML page)** | **15:57:15.534** | **0.0 s** | 762 ms |
| `latest_1min_temperature.csv` | 15:57:49.110 | **+33.6 s** | 514 ms |
| **`latest_since_midnight_maxmin.csv` ← what our bot reads** | 15:57:55.495 | **+40.0 s** | 800 ms |
| `latest_1min_humidity.csv` | 15:58:10.442 | +54.9 s | 864 ms |
| `latest_1min_pressure.csv` | 15:58:14.025 | +58.5 s | 656 ms |
| `rhrread` API | 16:03:49 | n/a (hourly, and **no max/min data**) | 844 ms |

Second cycle confirmed it: the 16:00 stamp hit the text page at **16:07:42**, and no CSV had appeared before the race ended at 16:07:55 — i.e. the page was again first.

**And the values are identical.** Page at 15:50:

```
HK Observatory   30.7   57   30.7 / 26.0
                  temp  RH   max / min since midnight
```
CSV at 15:50: `202610221550,HK Observatory,30.7,26.0` — same numbers, 40 seconds earlier.

### What this means
- **Your bot currently reads the slowest of the five useful sources.** Switching the trigger from `latest_since_midnight_maxmin.csv` to `text_readings_e.htm` is a **free ~40-second gain**, one endpoint change, same government source, same cadence, identical values.
- Everything else you might try is **later**, not earlier. The API is hourly and lacks the max. The "1-minute" files are 1-minute *averages* published on a 10-minute cycle — the name is about the averaging window, not the update rate. HKO's own open-data plan states **"Every 10 Minutes"** for every regional-weather dataset.
- There is **no sub-10-minute public HKO feed**. That hypothesis is dead.

### The Sep 19 forensic — and why it probably *wasn't* the observation

Your note said: *"On Sep 19 the price already drifted at 14:24–14:26, before any source I know of publishes."*

From the price history (1-minute fidelity) and the government archive:

| Time | 32°C | 33°C | HKO max-since-midnight |
|---|---|---|---|
| 14:18 | 0.86 | 0.12 | 32.8 (stamp 14:10) |
| 14:23 | 0.795 | 0.15 | — |
| **14:24** | **0.535** | **0.65** | — |
| 14:27 | 0.115 | 0.84 | — |
| 14:28 | 0.005 | **0.965** | **33.1 (stamp 14:20)** |
| 14:30 | — | — | archive captured the 14:20 file |

The data that settled the market — max goes 32.8 → **33.1**, crossing into the winning 33°C bucket — carries the **14:20** stamp. With the **7–8 minute publish lag** measured above, that stamp would have reached the internet around **14:27–14:28**.

**The market moved at 14:24 — three to four minutes before the HKO number could have been published.**

So on this day the move was **not** a reaction to the HKO observation crossing. Your two hypotheses were "earlier feed" or "forecast-driven", and the timing rules *out* the observation path. That leaves forecast, a large trader, or on-the-ground information (someone in Hong Kong watching the sky). I could not test the forecast branch: the government archive keeps the regional CSVs but returns `NOT FOUND` for the RSS forecast bulletins and the forecast APIs, so that question genuinely needs your live recorder — exactly as you said.

**Net: don't build a faster-source hunt. Build the text-page switch and a recorder.**

---

## 3. Item 2 — pre-armed orders: clean, but it optimises the wrong millisecond

Technically this all checks out:

| Property | Measured |
|---|---|
| Sign one order locally (with `coincurve`) | **0.69 ms** |
| Same, without `coincurve` (pure-Python crypto) | 7.08 ms |
| Order struct | `salt`, `maker`, `signer`, `tokenId`, `makerAmount`, `takerAmount`, **`expiration: 0`**, `nonce: 0`, `feeRateBps`, `side`, `signatureType` |
| Does a pre-signed order expire? | **No** — `expiration: 0` means GTC until filled/cancelled |
| Does signing touch the network? | **No** — `create_order` is pure local |
| Salt | **Random per signature** (I initially mis-read this — verified twice; every call differs) |
| L2 auth headers | Fresh HMAC **per request**, stamped with `int(now())` — cannot be pre-built far ahead, but costs microseconds |
| POST `/order` round trip | **22 ms** |

### What pre-arming actually buys
```
trigger → sign (0.69 ms) → POST (22 ms) → ack
trigger → [pre-signed]  → POST (22 ms) → ack      saving: 0.69 ms = 3% of this leg
```
Your note said it would take "our part from about 2.5 s down to under 1 s". That 2.5 s is the **serial data-fetch chain** (HKO 834 ms + Open-Meteo 911 ms + Gamma 74 ms + …), and pre-arming does not touch it. Concurrency and the WebSocket do.

**Verdict:** build it as clean architecture (it makes the code simpler and removes a failure mode), but do not expect a speed win. And because the salt is random, two racing processes would produce two *different* valid orders — so the double-fill warning from the last audit stands.

---

## 4. Item 3 — 2 s polling: right call, better implementation

You argued 1 s doubles load on a public server for half a second. Agreed. But the measurements suggest something better than a flat 2 s loop:

- The publish moment is **predictable within about 30 s** (7 m 15 s, 7 m 42 s, 7 m 55 s after the stamp).
- Each poll of the text page costs **762 ms** of network and 8.7 KB.

So a flat 2 s loop is effectively **continuously fetching** — about 43,000 requests/day to HKO, to catch a publish whose timing you can predict to within a minute.

**Better:** poll every 2 s only between **stamp + 6:00** and **stamp + 9:00**, and once a minute otherwise.

| Scheme | Requests/day | Detection delay |
|---|---|---|
| Flat 2 s | ~43,200 | ≤2 s |
| Flat 5 s | ~17,280 | ≤5 s |
| **Windowed 2 s + 60 s heartbeat** | **~4,500** | ≤2 s |

You keep 2-second detection and cut the load ~90%. That is both faster *and* politer than what you proposed.

---

## 5. Item 4 — server location: right on latency, wrong on access

You said moving to HK flips the numbers and buys nothing. On pure latency that holds:

| Endpoint | From this box (US-West) |
|---|---|
| `data.weather.gov.hk` TCP connect | 2 ms |
| HKO text page (warm) | 762 ms |
| HKO CSV (warm) | 137–800 ms |
| `gamma-api.polymarket.com` | **10 ms** |
| `clob.polymarket.com` `/time` | **157 ms** |
| `clob.polymarket.com` `/book` | 159 ms |

The fetch leg (HKO) and the order leg (CLOB) trade off against each other, and both are dwarfed by the 7–8 minute publish lag. So: **agreed, no gain.**

**But it is not a wash for access**, and this is the part that could stop you dead:

I sent a test order to `POST /order` and got:

```
403 {"error":"Trading restricted in your region ..."}
GET https://polymarket.com/api/geoblock
{"blocked": true, "ip": "8.235.119.244", "country": "US", "region": "OR"}
```

From the current geoblock documentation:

| Jurisdiction | Status |
|---|---|
| **United States (US)** | **Close-only on frontend AND API** — no new orders |
| **Netherlands (NL)** | **Close-only on the *frontend* only — the API is NOT restricted** ✅ |
| Kenya (KE) | Not listed — not restricted |
| Germany, France, Italy, Poland, Singapore, UK, Australia… | Close-only on frontend and API |

Two practical consequences:

1. **Your NL VPS is fine for API trading** — the frontend restriction does not apply to API order placement. But it is worth knowing that the *frontend* is close-only there, so anything that scrapes or drives the website will hit walls the API won't.
2. **Never test from a US IP.** It will look like "the bot is broken" when it is actually a geoblock.

And one item directly relevant to "is location a wash":

> **Primary servers: `eu-west-2` (London). Closest non-georestricted region: `eu-west-1` (Ireland). Direct co-location in `eu-west-2` is available to individual traders via a KYC/KYB form.**

So if you ever *do* care about latency, the answer is not "move to Hong Kong", it is **`eu-west-1`**, or co-location in `eu-west-2`. NL→London is already ~8 ms, so realistically you'd buy single-digit milliseconds. Consistent with your conclusion — but now for a measured reason.

---

## 6. Revised priority, by measured value

| Rank | Change | Measured gain | Effort |
|---|---|---|---|
| **1** | **Switch the trigger to `text_readings_e.htm`** | **+34–40 s every publish** | ~20 lines |
| 2 | **Record every poll** (stamp, value, your receive time, market price) | Resolves the Sep 19 "forecast vs observation" question in ~2 weeks | ~50 lines |
| 3 | Windowed 2 s polling (stamp+6 → stamp+9) | Same detection, **−90% load on HKO** | ~20 lines |
| 4 | Concurrent fetches + `coincurve` (from the last audit) | 2,140 ms → ~145 ms on the *non-trading* paths | 1 day |
| 5 | Pre-armed signed orders | **0.69 ms** | 1 day — do it for cleanliness, not speed |
| 6 | WebSocket market data | Removes the 30-min-stale book | 2 days |
| ❌ | Rust / Go rewrite | 0.06% | months |
| ❌ | Migrate VPS for latency | ~0 (lag is 7–8 min) | — |
| ❌ | Hunt for a sub-10-minute HKO feed | **Does not exist** | — |

---

## 7. The uncomfortable conclusion

Your instinct that "if we find a page that updates even 30 s earlier, that is worth more than everything else combined" was **right about the size of the prize and wrong about its location** — the 30 s was there all along, in the page we were not reading, not in some secret feed.

But the whole speed thesis rests on an assumption the data does not support:

- The ladder is 3.4% overpriced (from the earlier study).
- The market is calibrated to within 0.8 pp.
- On Sep 19 the market moved **before** the deciding observation existed.

Speed gets you the *same price, sooner*. It does not turn a negative-expectancy trade into a positive one, and being first to a price that is already 3.4% too expensive just means you lose the spread faster.

The genuinely valuable output of this whole exercise is **the recorder**. In two weeks it will answer the one question none of my measurements can: *on a day like Sep 19, when the market moves before HKO publishes, what moved it?* That answer is either an edge or the end of the project — and either way it is worth more than 40 seconds.

---

## 8. Files

| File | What |
|---|---|
| `SPEED-GAP-TESTS.md` | this document |
| `weather-rules-test/source_race.py` | the 6-way source race (re-runnable from your VPS) |
| `weather-rules-test/source_race.log` | raw race output, per-publish ordering |
| `weather-rules-test/cadence_monitor.py` | publish-lag monitor |
| `weather-rules-test/cadence.log` | raw publish lags |
| `weather-rules-test/reaction_time.py` | market-reaction analysis |
| `weather-rules-test/results/reaction_time*.json` | reaction-time results |
| `weather-bot-started-hong-kong/hk_weather_bot/hkbot/sources.py` | add `fetch_text_page()` here |

### Sources
- HKO open-data update frequencies: <https://www.hko.gov.hk/en/abouthko/opendata_intro.htm>
- Polymarket geoblock + co-location: <https://docs.polymarket.com/api-reference/geoblock>
- Polymarket rate limits: <https://docs.polymarket.com/api-reference/rate-limits>
