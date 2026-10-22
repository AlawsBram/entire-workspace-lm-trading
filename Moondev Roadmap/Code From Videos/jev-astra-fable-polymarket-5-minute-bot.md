<!-- source: https://moondev.com/jev-astra-fable-polymarket-5-minute-bot -->
<!-- captured: 2026-10-07 -->
<!-- title: Jev, Astra, and Fable Polymarket 5-Minute Bot -->

Jev, Astra, and Fable Polymarket 5-Minute Bot | AI Consensus Trading Bot | Moon Dev

Moon Dev Open Source

# Jev, Astra, and Fable Polymarket 5-Minute Bot

Three different AIs see the same Bitcoin window and the same facts. Each says UP, DOWN or NOTHING. If **2 of 3 agree**, the bot places one $5 trade. Then it grades all three, including the one that lost the vote.

By Moon Dev · September 26, 2026

## The Idea in One Paragraph

Every five minutes, Polymarket opens a brand new market: will Bitcoin finish this 5-minute window UP or DOWN? That is 288 fresh binary markets a day, every day, forever. This bot asks three completely different AIs the same question with the exact same facts. Each one answers UP, DOWN, or NOTHING. If at least 2 of the 3 agree, the bot places one $5 trade on that side. Then it grades everybody, *including the AI that lost the vote*, so at the end you actually know which AI is any good at this.

⚡ JEV said **DOWN**
🛸 ASTRA said **UP**
📖 FABLE said **DOWN**
→ 2 of 3 say DOWN, so we buy DOWN

Let me be straight with you about what this is before you read another word. **This is an experiment, not a proven money printer.** The question it answers is narrow and specific: when you hand three different AI models an identical pile of facts about a very short-term Bitcoin market, do any of them call it better than a coin flip? Moon Dev's own earlier testing found this 5-minute book is remarkably efficient, which means the honest starting assumption is that all three of these models are coin flips paying a spread. The CSV file is the point of the whole build. Let it run, then read it.

What you are going to learn here: how to make several LLMs vote on a trade without tripling your risk, how to build a fact pack that does all the arithmetic in Python so the model only ever makes a judgment call, why a market that settles on a *time-weighted average* needs a completely different pricing model than one that settles on a closing price, how to run a shadow book that scores a model on trades it never actually took, and how to place orders from a Polymarket smart-contract wallet that the official Python SDK flat out cannot sign for. All 8 files are at the bottom of this page, complete.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/jev-astra-fable-polymarket-5-minute-bot)

## Meet the Three AIs

All three run through **OpenRouter on a single API key**. No second vendor, no second SDK, no extra signup. That matters more than it sounds: keeping every model behind one key is what makes adding a fourth contestant about a minute of work.

NameModelHow it answersSpeedCost⚡ Jevtypesafe/jev-1.13Not a chatbot. A *decisions* model: you send facts plus typed questions, it sends back values with probabilities. Nothing to parse.~0.4s~$0.0002/round
(about 6¢ a day)🛸 Astraopenai/gpt-6-astraReads the facts in English, writes back a short paragraph with its call.~4 to 5sabout $10 a day📖 Fableanthropic/claude-fable-5.1Same as Astra: reads in English, writes back a call.~6 to 12sabout $10 a day

Look at that cost column again, because it is the real experiment hiding inside this bot. **Jev is roughly 150x cheaper and 10x faster than the other two.** Astra and Fable are the expensive reasoning models that stop and think. Jev classifies. If the slow expensive thinkers cannot beat the fast cheap classifier on this task, that is a genuinely useful thing to know, and it is worth more than the $5 trades it costs to find out.

One gotcha that cost Moon Dev an hour: **Jev is not on the chat model list and never will be.** It is a decisions model, so it lives at a different endpoint entirely. Ask for it at /chat/completions and OpenRouter tells you off in plain English. It will also never show up in GET /api/v1/models. It is there, it just lives somewhere else.

## Why One Vote Instead of Three Bots

The obvious way to compare three models is to run three bots side by side. Do not do that. Three bots put three orders into every single window, which triples the money at risk to learn the exact same thing. You would be paying 3x to answer one question.

This bot asks all three the same question, pays for *one* answer, and still scores all three. Same data, one third of the risk. The trick that makes it work is the shadow book, which we will get to: a model that loses the vote still gets recorded, priced, and graded as if it had traded alone.

**The hard rule: one trade per window, ever.** The money at risk in any 5-minute window is $5 and never a multiple of it, no matter how many AIs vote or how loudly they agree.

## How One Round Works, Step by Step

**A new window opens.** Every 5 minutes Polymarket lists a new BTC up/down market. The bot finds it.

**Wait 150 seconds.** The market settles on the *average* price over the whole 5 minutes, not the last price. At 150 seconds, half of that average is already locked in, so the answer is starting to show.

**Gather the facts.** 24 hours of 5-minute Binance candles, the strike, the running average, a fair value from a probability model, what the order book thinks, every big Hyperliquid BTC position near liquidation, and the bot's own record.

**Ask all three at once.** In parallel, so the round waits for the slowest one, not all three added together.

**Count the votes.** 2 or 3 agree and that side wins. NOTHING counts as sitting out, not a vote against. One UP against one DOWN is a split room and no trade.

**Run the safety checks.** Skip the trade (but still log every vote) if it is past 240 seconds, nobody is selling that side, the side costs over $0.80, or the day is already down $30.

**Buy $5 of the winning side** at the current ask and wait up to 20 seconds for the fill.

**Hold to the end and grade it** against Polymarket's real resolution.

**Score everyone.** The real trade in real money, plus a shadow book for each AI.

That step 2 timing was tuned the hard way and it is worth understanding why, so let us start the code there.

## Step 1: The Knobs, and Why 150 Seconds

Every setting that actually changes behavior lives at the top of ai_5min_core.py. Read the comment on DECIDE_AT_SEC carefully, because it is a real lesson about this market that you would otherwise pay to learn.

The first version asked the AIs at 15 seconds into the window. It got zero trades in three rounds, and the models were *right* to refuse. Here is why: the market settles on the average price across all five minutes. At 15 seconds in, only 5% of that average is locked, so the margin from the strike was $8, $12, $19. All of that is inside the noise of the price feed. The probability model correctly sat at 0.50 and both reasoning models correctly said NOTHING.

Moving to 150 seconds, the halfway mark, means **half the answer is already locked in and cannot be undone.** Now the margin means something. The cost is a worse price, because by 150 seconds the order book has figured it out too and the side you want is more expensive. That trade-off is the experiment. Push it later for more certainty and a worse fill, earlier for the reverse.

Also note LIVE_TRADING. It is True, but an environment variable can force it off. That is not redundancy, it is a scar: setting a constant in a parent process does not reach child processes, so a "dry run" that spawned each brain as its own process placed a real $5 order. An environment variable is the only switch that crosses a process boundary.

ai_5min_core.py — the only knobs that matter

```python
ASSET = "BTC"              # 🪙 the 5-minute market we are calling
USD_SIZE = 5               # 💰 dollars per trade
# 🚦 False = do everything real EXCEPT send the order.
#
# 🚨 AI5_PAPER=1 IN THE ENVIRONMENT FORCES THIS OFF, and it exists because
#    setting this constant in one process does NOT reach the others. The fleet
#    runs each brain as its own process, so a parent that flips this flag and
#    then spawns children has flipped nothing — the children import this module
#    fresh, read True, and trade real money. That happened, and it cost a real
#    $5 order during what was supposed to be a dry run. The environment is the
#    only switch that crosses a process boundary, so it wins over the constant.
LIVE_TRADING = True and os.getenv("AI5_PAPER") != "1"
# 🧠 SECONDS INTO THE WINDOW BEFORE WE ASK. This was 15 and 15 was too early.
#
#    The market settles on the AVERAGE across five minutes. At 15 seconds in,
#    only 5% of that average is locked and the TWAP margin is always small: the
#    first three live rounds came in at $8, $12 and $19 from the strike. Those
#    are all inside the feed noise, so the model sat at 0.50 every time and
#    both reasoning brains correctly refused to trade a coin flip. Three rounds,
#    zero trades, and they were right to pass.
#
#    At the halfway mark HALF the answer is already locked in and cannot be
#    undone, so the margin means something and the probability moves off 0.50.
#
#    The cost is a worse price: by 150 seconds the book has worked it out too,
#    so the side you want is dearer. That trade-off is the experiment. Push it
#    later for more certainty and a worse fill, earlier for the reverse.
DECIDE_AT_SEC = 150
ENTRY_CUTOFF_SEC = 240     # ⏰ no new entry past here. A reasoning model can
                           #    think for a minute; if the answer lands with
                           #    under 60s left that is not a trade, it is a
                           #    lottery ticket with a spread on it.
FILL_WAIT_SEC = 20         # ⏱️ how long to watch for the fill before giving up
BAR_HOURS = 24             # 📈 how much 5-minute history the brain is shown
DAILY_STOP_USD = -30.0     # 🛑 realized loss for the day that stops new entries
MAX_ROUNDS_PER_BRAIN = 40  # 🛑 the walk-away stop. A brain that passes on
                           #    almost everything could run all night chasing
                           #    ten trades, so 40 windows (about 3h20m) is the
                           #    cap. Hitting it is a RESULT, not a crash.
PROVISIONAL_MIN_EDGE_USD = 30.0   # ⚡ how far the TWAP must sit from the strike
                           #    before we will call a window early off Binance.
                           #    Polymarket settles on CHAINLINK, and the two
                           #    feeds disagree by a few dollars, so a $10 margin
                           #    is a guess. $30 is outside the observed basis.
SETTLE_PATIENCE_SEC = 900  # ⏳ how long a finished run waits for its last rounds
                           #    to resolve before giving up on them. Polymarket
                           #    takes 5-8 minutes, so 15 is plenty of room.

# 💸 THE PRICE CEILING, and it is here because Moon Dev's own data put it here.
#    Re-mining 1,533 resolved fills: entries above 0.80 LOST money across 484 of
#    them. This is not a hunch and it is not the model second-guessing the brain,
#    it is a measured cliff. Set to 1.0 to turn it off and watch it bleed.
MAX_ENTRY_PRICE = 0.80
```
That MAX_ENTRY_PRICE = 0.80 ceiling is not a hunch. Moon Dev re-mined 1,533 resolved fills and found that entries above 0.80 lost money across 484 of them. It is a measured cliff. Buying a side at 0.85 to win 0.15 means you have to be right 85% of the time just to break even, and nobody is right 85% of the time about the next five minutes of Bitcoin.

## Step 2: The Settle Rule Everyone Gets Wrong

This is the single most expensive misunderstanding available in this market, so read it twice. These markets **do not settle on the closing price.** They settle on the **time-weighted average price** across the entire five minutes. Polymarket's own resolution text says the window resolves Up if the TWAP is greater than or equal to the price at the beginning of the range.

Three things follow from that, and every one of them changes how you trade it. Minutes already elapsed are *locked into* the average and cannot be undone. A spike in the last thirty seconds barely moves a five-minute average. And spot can be sitting below the strike while the average is still above it, and that market resolves UP.

Moon Dev tested both readings against real resolved rounds: TWAP versus open called 6 of 7 correctly, while close versus open managed 4 of 7, which is a coin flip. Note the use of **one-second candles** below, so the average is a real average and not five bars pretending to be one.

ai_5min_core.py — what the market actually settles on

```python
def twap_so_far(window_ts):
    """🌙 Moon Dev - the TIME-WEIGHTED AVERAGE PRICE so far in this window, and
    how many seconds of it have run.

    🚨 THIS IS WHAT THE MARKET ACTUALLY SETTLES ON, and getting it wrong is the
       most expensive mistake in this whole file. Polymarket's own resolution
       text says it plainly:

         "resolve to Up if the TIME-WEIGHTED AVERAGE PRICE (TWAP) of Bitcoin,
          generated by Chainlink, of the time range specified in the title is
          GREATER THAN OR EQUAL TO the price at the beginning of that range."

       Not the closing price. The AVERAGE across the whole five minutes. Tested
       on Moon Dev's own resolved rounds, TWAP-vs-open called 6 of 7 correctly
       while close-vs-open managed 4 of 7, which is a coin flip.

    One-second candles, so the average is a real average and not five bars
    pretending to be one. Returns (twap, seconds_elapsed, last_price)."""
    now = min(time.time(), window_ts + MARKET_DURATION)
    elapsed = int(now - window_ts)
    if elapsed < 5:
        return (None, elapsed, None)
    rows = klines("1s", min(1000, elapsed + 5), start_ms=window_ts * 1000)
    if not rows:
        return (None, elapsed, None)
    px = [float(b[4]) for b in rows
          if window_ts * 1000 <= int(b[0]) < (window_ts + MARKET_DURATION) * 1000]
    if not px:
        return (None, elapsed, None)
    return (sum(px) / len(px), len(px), px[-1])
```
Notice it returns None rather than guessing when it does not have enough data. That pattern is everywhere in this codebase: real data or no bet. A bot that invents numbers when a feed is down teaches you nothing, because you can never tell afterward which rows were real.

## Step 3: Pricing an Average, and the Basis That Humbles It

Because the market settles on an average, pricing it like a normal terminal bet is simply the wrong model. Two things change, and they pull in opposite directions. First, the part of the window already elapsed is a *fact* now, not a random variable. Second, an average wanders less than an endpoint: the integral of a random walk over the remaining time carries a 1/sqrt(3) against the terminal case. The average is **stickier** than the close, which is exactly why a window that looks like a coin flip on spot can be well decided on TWAP.

Now the part that actually matters. **Polymarket settles on a Chainlink price. Every number in this bot is measured on Binance.** Those two feeds do not agree, and on a five-minute window the gap is big enough to flip the answer. Moon Dev measured it on 14 resolved windows: under a $22 margin, Binance agreed with Polymarket only 3 of 7 times, which is worse than a coin flip. Over $66, it was never wrong. Every single miss happened under $60.

Before this correction existed, the model read an $11 cushion as a 99.7% probability and all three AIs bought it at 0.74. It lost. The book had it at 0.675 and the book was right. The fix is BASIS_USD, combined with the market's own uncertainty **in quadrature**, which is the correct way to add two independent errors. Late in a window the market uncertainty goes to nearly zero and the feed risk is all that is left, which is precisely when the naive model was most confident and most wrong.

ai_5min_core.py — fair value for a TWAP barrier, with feed risk priced in

```python
    # 🧮 FAIR VALUE FOR UP, AND IT IS A TWAP BARRIER, NOT A TERMINAL ONE.
    #
    #    The market settles on the AVERAGE price across the window, not the
    #    closing price, so pricing it like a terminal bet is simply the wrong
    #    model. Two things change, and they pull in opposite directions:
    #
    #    1. THE PART ALREADY RUN IS LOCKED IN. Whatever the average has been so
    #       far is a fact now, not a random variable. With `done` seconds gone,
    #       that fraction of the answer is already settled.
    #    2. AN AVERAGE WANDERS LESS THAN AN ENDPOINT. The integral of a random
    #       walk over the remaining time has variance sigma^2 * (left^3)/3,
    #       so as a share of the window the standard deviation carries a
    #       1/sqrt(3) against the terminal case. The average is STICKIER than
    #       the close, which is exactly why a market that looks like a coin
    #       flip on spot can be well decided on TWAP.
    #
    #    expected final TWAP = (done * twap_so_far + left * spot) / T
    #    sd of final TWAP    = sigma * spot * sqrt(left^3 / 3) / T
    def fair(sig):
        if sig <= 0:
            return 0.5
        mean = (done * twap + left * spot) / MARKET_DURATION
        market_sd = per_sec(sig) * spot * math.sqrt(left ** 3 / 3.0) / MARKET_DURATION
        # 📏 TWO INDEPENDENT UNCERTAINTIES, COMBINED IN QUADRATURE. One is where
        #    the price goes from here. The other is that we are reading a
        #    different price feed than the one that pays out. Late in a window
        #    the first goes to nearly zero and the SECOND IS ALL THAT IS LEFT,
        #    which is exactly when the old model was most sure and most wrong.
        sd = math.sqrt(market_sd ** 2 + BASIS_USD ** 2)
        # 🌙 ties resolve UP ("greater than or equal to"), so the strike itself
        #    is a win. At a zero cushion that is worth exactly nothing in a
        #    continuous model, but the rule is the rule and it is written here
        #    so nobody later assumes it was ">".
        return norm_cdf((mean - strike) / sd) if sd > 0 else (
            1.0 if mean >= strike else 0.0)
    p_up_24h, p_up_1h = fair(sig_24h), fair(sig_1h)
    twap_edge = twap - strike
```
Be honest about what that constant is: an estimate off 14 windows, not a measurement. The whole point of logging twap_minus_strike and resolution to the CSV is so you can re-fit it properly once you have a few hundred rows.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/jev-astra-fable-polymarket-5-minute-bot)

## Step 4: The Fact Pack, Where Python Does All the Math

Here is the design rule that makes this whole thing work, and it applies to any LLM you ever point at a trading problem: **every number the model needs is computed in Python before it is sent.** The ratios, the returns, the volatility, the probability, the liquidation totals. All finished facts by the time any model sees them.

Why bother? Jev reads literally and cannot divide. Astra and Fable can divide, but an LLM doing arithmetic in its head is a coin flip dressed up as a calculation. So the model is only ever asked for the *judgment* that the arithmetic cannot make. That is the job LLMs are actually good at, and it is the only job they are given here.

The pack also carries two volatility numbers rather than one, because the 24-hour figure is the regime and the 1-hour figure is right now, and in a 5-minute market they disagree constantly. Handing the model both and letting it judge beats us picking one in advance. Every one of the 288 candles is sent as a *percent moved* rather than four raw OHLC prices, because a percent is a fact the model can read and raw prices are arithmetic in disguise.

ai_5min_core.py — gathering the facts (opening half of gather)

```python
def gather(market):
    """🌙 Moon Dev - THE FACT PACK. Every number the brain gets, computed here.

    Returns the pack, or None when any feed is down. There is no half pack and
    there is no filled-in gap: a missing feed is a skipped round, on purpose."""
    ts = market["ts"]
    strike = strike_for(ts)
    spot = spot_now()
    bars = klines("5m", int(BAR_HOURS * 12))
    liq = near_liq()
    if strike is None or spot is None or bars is None:
        return None

    closes = [float(b[4]) for b in bars]
    highs = [float(b[2]) for b in bars]
    lows = [float(b[3]) for b in bars]
    rets = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]

    # 📏 TWO VOLS, not one. The 24-hour number is the regime, the 1-hour number
    #    is right now, and in a 5-minute market they disagree constantly. Handing
    #    the brain both and letting it judge beats us picking one in advance.
    sig_24h = statistics.pstdev(rets) if len(rets) > 2 else 0.0
    sig_1h = statistics.pstdev(rets[-12:]) if len(rets) > 13 else sig_24h
    per_sec = lambda s: s / math.sqrt(MARKET_DURATION)   # 5-min bar -> 1 second

    left = max(1.0, ts + MARKET_DURATION - time.time())
    done = MARKET_DURATION - left               # seconds of the window already run
    cushion = spot - strike                     # spot vs strike, NOT the settle rule
    twap, ticks, last = twap_so_far(ts)
    if twap is None:                            # too early in the window to average
        twap, ticks = spot, 0

    # 🧮 FAIR VALUE FOR UP, AND IT IS A TWAP BARRIER, NOT A TERMINAL ONE.
    #
    #    The market settles on the AVERAGE price across the window, not the
    #    closing price, so pricing it like a terminal bet is simply the wrong
    #    model. Two things change, and they pull in opposite directions:
    #
    #    1. THE PART ALREADY RUN IS LOCKED IN. Whatever the average has been so
    #       far is a fact now, not a random variable. With `done` seconds gone,
    #       that fraction of the answer is already settled.
    #    2. AN AVERAGE WANDERS LESS THAN AN ENDPOINT. The integral of a random
    #       walk over the remaining time has variance sigma^2 * (left^3)/3,
    #       so as a share of the window the standard deviation carries a
    #       1/sqrt(3) against the terminal case. The average is STICKIER than
    #       the close, which is exactly why a market that looks like a coin
    #       flip on spot can be well decided on TWAP.
    #
    #    expected final TWAP = (done * twap_so_far + left * spot) / T
    #    sd of final TWAP    = sigma * spot * sqrt(left^3 / 3) / T
    def fair(sig):
        if sig <= 0:
            return 0.5
        mean = (done * twap + left * spot) / MARKET_DURATION
        market_sd = per_sec(sig) * spot * math.sqrt(left ** 3 / 3.0) / MARKET_DURATION
        # 📏 TWO INDEPENDENT UNCERTAINTIES, COMBINED IN QUADRATURE. One is where
        #    the price goes from here. The other is that we are reading a
        #    different price feed than the one that pays out. Late in a window
        #    the first goes to nearly zero and the SECOND IS ALL THAT IS LEFT,
        #    which is exactly when the old model was most sure and most wrong.
        sd = math.sqrt(market_sd ** 2 + BASIS_USD ** 2)
        # 🌙 ties resolve UP ("greater than or equal to"), so the strike itself
        #    is a win. At a zero cushion that is worth exactly nothing in a
        #    continuous model, but the rule is the rule and it is written here
        #    so nobody later assumes it was ">".
        return norm_cdf((mean - strike) / sd) if sd > 0 else (
            1.0 if mean >= strike else 0.0)
    p_up_24h, p_up_1h = fair(sig_24h), fair(sig_1h)
    twap_edge = twap - strike

    up_bid, up_ask = book(market["tokens"]["Up"])
    down_bid, down_ask = book(market["tokens"]["Down"])
    book_p_up = implied_p_up(up_bid, up_ask, down_bid, down_ask)
```
One more subtlety worth stealing. implied_p_up below reads the order book through *both* tokens. Up and Down are the same dollar split two ways, so a Down bid of 0.99 is somebody offering to sell Up at 0.01. Late in a window one side of one token empties out constantly, and reading only the Up token would give you nothing on a book that is quoting perfectly well through Down.

ai_5min_core.py — reading the book from both sides, and summing the liquidation pools

```python
def norm_cdf(x):
    """🌙 Moon Dev - Phi. The odds a normal draw lands under x."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def implied_p_up(up_bid, up_ask, down_bid, down_ask):
    """🌙 Moon Dev - what the BOOK thinks P(Up) is, using both sides of it.

    Up and Down are the same dollar split two ways, so a Down bid of 0.99 is
    somebody offering to sell Up at 0.01. Late in a window one side of one token
    goes empty all the time, and reading only the Up token there gives you None
    on a book that is actually quoting perfectly well through Down.

    So: build the best Up bid and the best Up ask out of BOTH tokens, then take
    the middle of whatever survives. None only when the book is genuinely empty."""
    bids = [p for p in (up_bid, (1 - down_ask) if down_ask else None) if p]
    asks = [p for p in (up_ask, (1 - down_bid) if down_bid else None) if p]
    best_bid = max(bids) if bids else None
    best_ask = min(asks) if asks else None
    if best_bid and best_ask:
        return (best_bid + best_ask) / 2
    return best_bid or best_ask

def liq_side(rows, spot):
    """🌙 Moon Dev - one side of the liquidation book, already added up.

    Every sum here is done in PYTHON. The brain is asked which pool matters,
    never asked to add the pools."""
    total = sum(float(r.get("value") or 0) for r in rows)
    near = [r for r in rows if float(r.get("distance_pct") or 99) <= 1.0]
    dists = [float(r.get("distance_pct") or 99) for r in rows]
    return {
        "positions": len(rows),
        "total_value_usd": round(total),
        "value_within_1pct_usd": round(sum(float(r.get("value") or 0) for r in near)),
        "positions_within_1pct": len(near),
        "closest_distance_pct": round(min(dists), 3) if dists else None,
        "biggest_position_usd": round(max((float(r.get("value") or 0) for r in rows),
                                          default=0)),
    }
```
## Step 5: Asking All Three at Once, and Counting the Votes

The three models answer at wildly different speeds: Jev in about 0.4 seconds, Astra in 5, Fable in 12. Asked one after another that is 17 seconds of a 300 second window spent waiting, and the price moves while you wait. Asked in parallel, it costs whatever the slowest one costs. A plain ThreadPoolExecutor is all it takes.

Every model sees the *same* pack. That is the entire point of this bot: any difference in their answers is the model, never the data. Notice also that one model falling over cannot cost the round. It abstains, loudly, with the actual exception message included. A handler that prints only the exception type turns a one-line bug into a hunt, and it did exactly that once.

consensus_5min_bot.py — ask all three at once, wait for the slowest

```python
def collect(brains, pack, record):
    """🗳️ Moon Dev - ask all three AT ONCE and wait for the slowest.

    In parallel because they are wildly different speeds: Jev answers in about
    0.4 seconds, Astra in 5, Fable in 12. Asked one after another that is 17
    seconds of a 300 second window spent waiting, and the price moves while you
    wait. Asked together it costs whatever the slowest one costs.

    Every brain sees the SAME pack. That is the entire point of this bot: any
    difference in their answers is the brain, never the data."""
    def ask(cls):
        b = cls()
        t0 = time.time()
        try:
            side, p_up, conf, why, detail = b.decide(pack, record)
        except Exception as e:
            # 🌙 one brain falling over must not cost the round. It abstains,
            #    loudly, and the other two still vote.
            # 🚨 SAY WHAT ACTUALLY WENT WRONG. A handler that prints only the
            #    exception TYPE turns a one-line bug into a hunt, and it did.
            return {"brain": b, "side": None, "p_up": "", "conf": "",
                    "why": f"{b.NAME} failed: {type(e).__name__}: {e}",
                    "detail": {"latency_ms": (time.time() - t0) * 1000},
                    "failed": True}
        return {"brain": b, "side": side, "p_up": p_up, "conf": conf,
                "why": why, "detail": detail, "failed": False}

    with ThreadPoolExecutor(max_workers=len(brains)) as pool:
        return list(pool.map(ask, brains))
```
Now the vote itself. The rule that matters here is that **NOTHING is an abstention, not a vote against.** Two models saying DOWN and one saying NOTHING is a majority for DOWN, because nobody argued the other way. One UP against one DOWN is a split room and we sit it out no matter how many abstained. Set NEED_AGREE = 3 if you only want to trade when they are unanimous.

consensus_5min_bot.py — the voters and the tally

```python
VOTERS = [Jev, Astra, Fable]

# 🗳️ how many must agree before real money moves. Two of three is a majority.
#    Raise to 3 to only trade when they are unanimous.
NEED_AGREE = 2

LOG = os.path.join(DATA_DIR, "consensus_rounds.csv")
LEDGER_KEY = "consensus"

def tally(votes):
    """🗳️ Moon Dev - (winning side, up, down, pass, how many agreed).

    A NOTHING is an ABSTENTION, not a vote against. Two brains saying DOWN and
    one saying NOTHING is a majority for DOWN, because nobody argued the other
    way. One UP against one DOWN is a split room and we sit it out however many
    abstained."""
    up = sum(v["side"] == "Up" for v in votes)
    down = sum(v["side"] == "Down" for v in votes)
    passes = len(votes) - up - down
    if up >= NEED_AGREE and up > down:
        return ("Up", up, down, passes, up)
    if down >= NEED_AGREE and down > up:
        return ("Down", up, down, passes, down)
    return (None, up, down, passes, max(up, down))
```
Nothing in that code is hardcoded to three. Add a fourth model to VOTERS and the vote panel, the CSV columns, and the scorecards all adapt on their own.

## Step 6: The Shadow Books, or How to Grade a Loser

This is my favorite part of the build and the piece most worth stealing for your own work. Astra saying UP on a window the bot traded DOWN is *not thrown away*. The round records what Astra said, what UP was priced at, and what it would have paid. So one file answers four separate questions at once.

The honesty detail: each shadow entry is priced at the **actual ask on screen at the moment of the call**, not at a pretend perfect fill. That matters enormously. A model that keeps picking 0.85 favorites should look bad in this ledger even when it is usually right, because paying 85 cents to win 15 is genuinely bad, and any backtest that hides that is lying to you.

consensus_5min_bot.py — the shadow book, priced at the real ask

```python
def shadow(side, winner, up_ask, down_ask):
    """🕵️ Moon Dev - (entry it would have paid, was it right, what it returns).

    Priced at the ACTUAL ask on screen when the call was made, not at a
    pretend fill. A brain that keeps picking 0.85 favourites should look bad
    here even when it is usually right, because that is the truth about it.

    A brain that abstained returns 0: no trade, no gain, no loss. Being right
    about sitting out is scored on its own, further down."""
    if side is None:
        return ("", "", "")
    entry = up_ask if side == "Up" else down_ask
    if not entry:
        return ("", "", "")
    won = side == winner
    return (round(entry, 4), won, round((1 - entry) / entry if won else -1.0, 4))
```
The CSV header is deliberately wide: one row per window, with a full block of columns per model. The whole study is one file you can open in a spreadsheet and sort, with nothing to join and nothing to reconstruct six months later.

consensus_5min_bot.py — one wide row per window

```python
def header():
    """🌙 Moon Dev - ONE ROW PER WINDOW, WIDE. Every brain gets its own block
    of columns so the whole study is one file you can open in a spreadsheet and
    sort, with nothing to join and nothing to reconstruct later."""
    cols = ["round_ts", "time", "slug",
            "consensus", "votes_up", "votes_down", "votes_pass", "agreed",
            "traded", "entry_price", "shares", "usd_risked",
            "resolution", "consensus_won", "consensus_pnl", "consensus_roi",
            "strike", "twap_minus_strike", "spot_minus_strike", "secs_left",
            "p_up_model", "book_p_up", "book_resid", "up_ask", "down_ask",
            "liq_long_usd", "liq_short_usd"]
    for v in VOTERS:
        k = v.KEY
        # 🕵️ the shadow book: what this brain said, what its side cost at the
        #    time, whether it was right, and what it would have paid.
        cols += [f"{k}_side", f"{k}_p_up", f"{k}_conf", f"{k}_won",
                 f"{k}_shadow_entry", f"{k}_shadow_roi",
                 f"{k}_latency_ms", f"{k}_cost_usd", f"{k}_why"]
    return cols
```
And here is a subtle decision inside the scoreboard that protects the entire experiment. Every model is shown the *same* record line: how the consensus has done, not its own personal shadow record. Showing each model its own record would give them different fact packs, and identical packs is the one thing that makes this comparison worth anything.

consensus_5min_bot.py — every brain reads the same record

```python
    def summary(self):
        """📋 Moon Dev - the record, in plain English, for the brains to read.

        Every brain is shown the SAME line: how the VOTE has done. Not its own
        shadow book. Showing each one its personal record would give them
        different packs, and identical packs is the one thing that makes this
        comparison worth anything."""
        d = self.who["CONSENSUS"]
        if not self.rounds:
            return "no graded rounds yet, this is the first one"
        pct = f"{d['wins'] / d['calls'] * 100:.0f}%" if d["calls"] else "n/a"
        return (f"the majority vote has called {d['calls']} windows, {d['wins']} "
                f"right ({pct}), sat out {d['passes']}, and is "
                f"${d['pnl']:+.2f} on real trades across {self.rounds} rounds")
```
## The Four Scorecards

At the end, one CSV file (data/ai_5min/consensus_rounds.csv, one row per window) answers four questions:

Did the **consensus** make money? (real money)

Would **Jev alone** have made money? (shadow book)

Would **Astra alone** have made money? (shadow book)

Would **Fable alone** have made money? (shadow book)

## Step 7: Jev, the Model That Never Writes a Sentence

Astra and Fable write a paragraph and we fish the answer out with a regex. Jev never writes prose at all. You hand it state plus **typed questions** and the answers come back as values in one forward pass: a choice with calibrated probabilities, a 0-to-1 noul, a score. Nothing to parse, so nothing to mis-parse, and no round is ever lost to a reasoning model burning its whole token budget thinking and handing back null.

Because every question is answered in parallel inside a single request, the sixth question is effectively free in wall-clock time. That is why this asks six instead of one. It gets the call itself, plus a check on whether there is even enough information to judge, plus a read on the tape, the book, and the liquidation pools, plus a difficulty score. All for two hundredths of a cent.

jev_5min_bot.py — six typed questions in one request

```python
TRADE_AT = 0.58
TOO_THIN_VETO_AT = 0.70

QUESTIONS = {
    "call": {
        "type": "choice",
        "instructions": (
            "Which way does this 5-minute window settle? UP means the "
            "TIME-WEIGHTED AVERAGE price across the whole window ends at or "
            "above the strike. DOWN means the average ends below it. It is the "
            "AVERAGE, not the closing price, and the seconds already elapsed "
            "are locked into it. NOTHING means sit this window out, which "
            "costs nothing and is the right answer whenever the two sides look "
            "the same."),
        "criteria": {
            "up": "The average looks like it ends at or above the strike, and "
                  "the Up side is not already priced as if everyone knows it.",
            "down": "The average looks like it ends below the strike, and the "
                    "Down side is not already priced for it.",
            "nothing": "A coin flip, or the cheap side is cheap for a good "
                       "reason. Sitting out costs nothing.",
        },
    },
    "too_thin": {
        "type": "noul",
        "instructions": (
            "The information given is too thin to tell this 5-minute window "
            "apart from any other window whose average sits the same distance "
            "from its strike."),
        "criteria": {
            "true": "Nothing here distinguishes it. Any answer would be a guess.",
            "false": "There is something specific in this window to go on.",
        },
    },
    "tape": {
        "type": "choice",
        "instructions": (
            "Given the recent bars, the 24-hour range position and the "
            "volatility numbers, what does this market's behaviour most look "
            "like right now?"),
        "criteria": {
            "trending_up": "A persistent push higher that is still going.",
            "trending_down": "A persistent push lower that is still going.",
            "chopping": "Two-sided noise around a level. No direction.",
            "reversing": "A move rolling over or bouncing off an extreme.",
        },
    },
    "book_read": {
        "type": "choice",
        "instructions": (
            "The barrier model's fair value and the order book disagree by the "
            "amount shown. Who is more likely to be right here?"),
        "criteria": {
            "book_is_right": "The book is pricing something real that a random "
                             "walk model cannot see. Do not fade it.",
            "model_is_right": "The book looks lazy or thin and the model's "
                              "number is the better estimate.",
            "too_close": "They barely disagree. Nothing here either way.",
        },
    },
    "liq_pull": {
        "type": "choice",
        "instructions": (
            "Hyperliquid positions near liquidation are listed. Longs blow up "
            "below spot and sell into it, shorts blow up above spot and buy "
            "into it. Does either pool matter for the next few minutes?"),
        "criteria": {
            "pulls_down": "The long pool below is big and close enough to get "
                          "swept inside this window.",
            "pulls_up": "The short pool above is big and close enough to get "
                        "swept inside this window.",
            "no_pull": "Neither pool is close or big enough to move price in "
                       "the next few minutes, or the feed is missing.",
        },
    },
    "difficulty": {
        "type": "score",
        "instructions": "How hard a call is this window?",
        "criteria": [
            "Obvious. The cushion and the clock all but settle it.",
            "Leaning clearly one way.",
            "A real question with arguments on both sides.",
            "Close to a coin flip.",
            "Pure noise. Nobody could call this.",
        ],
    },
}
```
Reading the answer is then just arithmetic on typed values. Two thresholds do the gatekeeping: Jev has to be at least 58% sure to call a side at all, and a separate veto fires if Jev says the pack is 70% or more likely to be too thin to distinguish this window from any other. That second one is the interesting guard, because it lets the model say *"I have an opinion but you should not trust it"*, which is a distinction most prompt-and-parse setups cannot express.

jev_5min_bot.py — turning typed answers into a side

```python
class Jev(DecisionsBrain):
    NAME = "JEV"
    KEY = "jev"
    EMOJI = "⚡"
    MODEL = "typesafe/jev-1.13"
    TAGLINE = ("Jev answers in typed values, not paragraphs, in under half a "
               "second for two hundredths of a cent.")
    COST_PER_DAY = "$0.06"
    QUESTIONS = QUESTIONS

    def read(self, a):
        call = a.get("call") or {}
        probs = call.get("probabilities") or {}
        p_up = float(probs.get("up", 0.0))
        p_down = float(probs.get("down", 0.0))
        confidence = float(call.get("confidence", 0.0))

        thin = float((a.get("too_thin") or {}).get("noul", 0.0))
        tape = (a.get("tape") or {}).get("choice", "?")
        bookread = (a.get("book_read") or {}).get("choice", "?")
        liq = (a.get("liq_pull") or {}).get("choice", "?")
        hard = float((a.get("difficulty") or {}).get("score", 0.0))

        side = ("Up" if p_up >= TRADE_AT else
                "Down" if p_down >= TRADE_AT else None)
        why = (f"p(up) {p_up:.0%}, p(down) {p_down:.0%}, {tape} tape, "
               f"{bookread}, {liq}, difficulty {hard:.1f}/{DIFFICULTY_TOP}")
        if side is None:
            why = f"under the {TRADE_AT:.0%} line — {why}"

        if side and thin >= TOO_THIN_VETO_AT:
            why = (f"vetoed: Jev says the pack is too thin ({thin:.0%}) to "
                   f"tell this window apart — he wanted {side} at "
                   f"{max(p_up, p_down):.0%}")
            side = None

        return side, round(p_up, 4), round(confidence, 4), why, {
            "p_up": round(p_up, 4), "p_down": round(p_down, 4),
            "call_confidence": round(confidence, 4),
            "too_thin": round(thin, 4),
            "tape": tape, "book_read": bookread, "liq_pull": liq,
            "difficulty": round(hard, 3),
        }
```
## Step 8: The Chat Brains, and Parsing a Paragraph Safely

Astra and Fable share one class. The system prompt below is doing a lot of work, and most of it is talking the model *out of* trading. It hammers the TWAP settle rule, forbids recomputing arithmetic, and states the honest prior plainly: this book is efficient, NOTHING is the correct answer for most windows, and it costs nothing.

There is one instruction in there worth calling out because it is a trap almost everyone walks into. The feed-gap warning tells the model the basis risk is **already priced into** the probability it was handed, so do not discount for it a second time. Without that line, a careful model reasons its way into double-counting the same risk and passes on everything.

openrouter_brain.py — the shared system prompt

```python
SYSTEM = """You are calling a 5-minute Bitcoin up-or-down market on Polymarket \
for Moon Dev. Real money follows your answer.

THE SETTLE RULE, AND MOST PEOPLE GET THIS WRONG. The market resolves UP if the \
TIME-WEIGHTED AVERAGE PRICE of BTC across the whole 5-minute window is GREATER \
THAN OR EQUAL TO the strike (the price at the start of the window). It is NOT \
the closing price. It is the AVERAGE. Three things follow from that:
- Minutes already elapsed are locked into the average and cannot be undone.
- A spike in the last thirty seconds barely moves a five-minute average.
- Spot can be below the strike while the average is still above it, and that \
market resolves UP.
Trade the average, not the last price. You buy one side at the ask shown and \
hold it to expiry. There is no exit.

EVERY NUMBER YOU NEED IS ALREADY COMPUTED FOR YOU. The returns, the volatility, \
the fair value and the liquidation totals were all worked out in Python before \
you saw them. Do not recompute anything and do not do arithmetic in your head. \
Your job is the judgement the arithmetic cannot make.

Three things worth knowing before you answer:
- This book is efficient most of the time. Moon Dev has tested fleets of bots \
against it and the honest prior is that any given window is a coin flip paying \
a spread. NOTHING is the correct answer for most windows and it costs nothing.
- When the model says a 4-cent side is worth 15 cents, that is usually the \
model being wrong, not the book. The cheap side rots as the clock runs out.
- These numbers come from Binance; Polymarket settles on Chainlink. That feed \
gap is ALREADY built into the P(Up) you are given, which is why it sits closer \
to 0.5 than the raw TWAP suggests. Do not subtract for it again. Judge the \
probability you are handed against the price you would pay.
- NOTHING is for windows with no edge, not for windows with ordinary \
uncertainty. Every one of these is uncertain. If the probability and the price \
disagree enough to be worth five dollars, that is a call, not a coin flip.
- Buying a side at 0.85 to win 0.15 needs to be right 85% of the time just to \
break even. Price is part of the call, not a detail.

Answer in at most three short sentences of reasoning, then these two lines \
exactly, nothing after them:
DECISION: UP or DOWN or NOTHING
CONFIDENCE: a whole number from 50 to 100, how sure you are of that decision"""
```
Then the parsing, which has two defenses worth copying. First, **the last valid keyword wins.** A model that writes "I considered DOWN but the cushion says UP" must not be read as DOWN, and taking the last match is the only rule that survives that sentence. Second, a reasoning model can burn its entire budget thinking and return content of null. That is not a yes and not a no, it is a NOTHING, and it gets logged as one so a bad stretch is visible in the CSV instead of looking like a quiet afternoon of no opinions.

openrouter_brain.py — last keyword wins

```python
def read_answer(text):
    up = text.upper()
    m = re.search(r"DECISION:\s*\**\s*(UP|DOWN|NOTHING)", up)
    if m:
        word = m.group(1)
    else:
        words = re.findall(r"\b(UP|DOWN|NOTHING)\b", up)
        word = words[-1] if words else "NOTHING"
    c = re.search(r"CONFIDENCE:\s*\**\s*(\d{1,3})", up)
    confidence = min(100, int(c.group(1))) if c else 0
    side = {"UP": "Up", "DOWN": "Down"}.get(word)
    return side, confidence
```
With all that shared, the individual bot files become almost nothing. Here is Astra, complete, minus its docstring. Fable is the same four lines with a different model string. That is the payoff of putting the machinery in one place: adding a fourth contestant is genuinely about a minute of work.

astra_5min_bot.py — the entire bot

```python
from ai_5min_core import start
from openrouter_brain import OpenRouterBrain

class Astra(OpenRouterBrain):
    NAME = "ASTRA"
    KEY = "astra"
    EMOJI = "🛰️"
    MODEL = "openai/gpt-6-astra"
    TAGLINE = "GPT-6 Astra reads the tape in English and writes back a call."
    MIN_CONFIDENCE = 0

if __name__ == "__main__":
    start(Astra())
```
[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/jev-astra-fable-polymarket-5-minute-bot)

## Step 9: The Four Gates Before Any Money Moves

A majority is necessary but nowhere near sufficient. Four gates stand between the vote and the order, and the important design choice is that **a blocked trade still logs every vote and still runs every shadow book.** You lose the trade, you never lose the data point. That is what keeps the experiment intact on days the bot barely trades.

The gates: too late in the window, nobody offering that side, the side costs more than the measured 0.80 cliff, or the day is already down $30. There is also a guard above them that prevents ever holding two positions in one window, which matters because the bot is designed to survive restarts.

consensus_5min_bot.py — every gate, with the votes still logged

```python
    if side is None:
        hold_out(end, ts, board, pending, "no majority")
        return rec

    # 🚨 never two positions in one window, however the vote went
    held = open_load(_Ledger).get(market["slug"])
    if held and held.get("traded"):
        say(f"🛑  ALREADY IN THIS WINDOW from an earlier run: "
            f"{held['shares']:.2f} {tag(held['side'])} @{NB}{BOLD}"
            f"{held['price']:.2f}{OFF}. NOT buying again.", YELLOW + BOLD)
        rec.update(traded=True, consensus=held["side"],
                   entry_price=held["price"], shares=held["shares"],
                   usd_risked=round(held["price"] * held["shares"], 2))
        hold_out(end, ts, board, pending, "adopted")
        return rec

    if time.time() > ts + ENTRY_CUTOFF_SEC:
        say(f"⛔  The vote took too long, only {clock(end - time.time())} left. "
            f"Logging every call, skipping the trade.", YELLOW)
        hold_out(end, ts, board, pending, "too late")
        return rec

    token = market["tokens"][side]
    _, ask = book(token)
    if ask is None:
        say(f"⛔  Nobody is offering {side}. Nothing to buy.", YELLOW)
        hold_out(end, ts, board, pending, "no ask")
        return rec
    if ask > MAX_ENTRY_PRICE:
        say(f"⛔  {side} is {ask:.2f}, over the {MAX_ENTRY_PRICE:.2f} ceiling. "
            f"Every call still logged.", YELLOW)
        hold_out(end, ts, board, pending, "over ceiling")
        return rec

    today = today_pnl()
    if today <= DAILY_STOP_USD:
        say(f"🛑  Daily stop hit: ${today:.2f} today. Every call is still "
            f"logged and every shadow book still runs, but no money moves.",
            RED + BOLD)
        hold_out(end, ts, board, pending, "daily stop")
        return rec
```
When it does trade, the order goes in and the bot watches for the fill for 20 seconds. If nothing fills, it cancels, because an order left resting into the next window is a position you did not decide to take.

ai_5min_core.py — place, watch for the fill, cancel if it never comes

```python
def enter(token, side, ask, size):
    chime(HUNT_SOUND)
    try:
        r = place(token, "BUY", round(ask, 4), size, post_only=False)
    except Exception as e:
        say(f"❌  Could not place the order: {type(e).__name__}", RED)
        return {"skip_reason": f"order error {type(e).__name__}"}
    if not r.get("orderID"):
        say("❌  The exchange did not take that order.", RED)
        return {"skip_reason": "order rejected"}
    order_id = r.get("orderID")
    say("📤  Order sent. Watching for the fill.", GREEN)
    deadline = time.time() + FILL_WAIT_SEC
    while time.time() < deadline:
        got = fill_of(order_id)
        have, avg = got if got else position_in(token)
        if got and have > 0 and not avg:
            avg = ask
        if have > 0:
            chime(FILL_SOUND)
            say(f"✅  FILLED {have:.2f} {tag(side)} @{NB}{BOLD}{avg:.2f}{OFF}",
                GREEN + BOLD)
            return {"traded": True, "side": side, "price": avg, "shares": have}
        time.sleep(2)
    say(f"⚠️  Nothing filled in {FILL_WAIT_SEC}s. Cancelling so nothing rests "
        f"into the next window.", YELLOW)
    chime(CANCEL_SOUND)
    try:
        cancel_all_on(token)
    except Exception:
        say("❌  Could not confirm the cancel. Check the site.", RED)
    return {"side": side, "price": ask, "shares": size, "skip_reason": "no fill"}
```
## Step 10: Grading Honestly, and Never Losing a Paid Trade

Settlement grades the real trade and all three shadow books in one pass, against Polymarket's actual resolution rather than the bot's own opinion of who won. Only then does the row get written to the CSV and dropped from the open-position file.

consensus_5min_bot.py — grade the real trade and all three shadow books

```python
def settle(rec, board):
    """🏁 Moon Dev - grade the consensus AND all three shadow books at once."""
    winner = get_resolution(rec["slug"])
    if winner is None:
        return False

    rec["resolution"] = winner
    traded = rec["traded"] is True
    price, shares = _f(rec["entry_price"]), _f(rec["shares"])
    side = rec["consensus"] or None
    won = bool(side) and side == winner
    pnl = ((shares * (1 - price) if won else -shares * price)
           if traded and price else 0.0)
    rec["consensus_won"] = won if side else ""
    rec["consensus_pnl"] = round(pnl, 2) if traded else ""
    rec["consensus_roi"] = (round(pnl / (price * shares), 4)
                            if traded and price * shares else "")

    # 🕵️ the three shadow books, priced at the ask that was on screen.
    for v in VOTERS:
        k = v.KEY
        entry, w, roi = shadow(rec[f"{k}_side"] or None, winner,
                               _f(rec["up_ask"]), _f(rec["down_ask"]))
        rec[f"{k}_shadow_entry"] = entry
        rec[f"{k}_won"] = w
        rec[f"{k}_shadow_roi"] = roi

    append_csv(LOG, header(), [rec[c] for c in header()])
    open_drop(_Ledger, rec["slug"])
```
Finally, the piece that separates a toy from something you can leave running. **Ctrl+C raises KeyboardInterrupt. Nothing else does.** A kill, a closed terminal, a logout, a laptop going to sleep: those send SIGTERM or SIGHUP and end the process instantly, skipping every bit of cleanup. That means a live position with no CSV row and no ledger entry. Money spent, nothing recorded, no way to reconstruct it.

Turning those signals into the same interrupt Ctrl+C raises means every exit path runs the same drain. Pair that with the fact that one bad window can no longer kill a 30-round overnight run, and you have something that finishes the study it started.

consensus_5min_bot.py — every exit grades what it already paid for

```python
def _graceful(signum, _frame):
    """🌙 Moon Dev - a kill signal must still grade what we already paid for.

    🚨 Ctrl+C RAISES KeyboardInterrupt. NOTHING ELSE DOES. A `kill`, a closed
       terminal, a logout, a machine going to sleep: all of those send SIGTERM
       or SIGHUP, which end the process instantly and skip every bit of cleanup
       below. That means a live position with no CSV row and no ledger entry:
       money spent, nothing recorded, and no way to reconstruct it.

       Turning those signals into the same interrupt Ctrl+C raises means every
       exit runs the same drain, whatever ended the run."""
    raise KeyboardInterrupt(f"signal {signum}")

def install_signals():
    for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT):
        try:
            signal.signal(sig, _graceful)
        except (ValueError, OSError, AttributeError):
            pass        # 🌙 not every platform has every signal. Never fatal.
```
## Step 11: The Signing Fix That Makes Any of This Possible

If you have tried to trade Polymarket programmatically on a newer account and hit a wall, this section alone is worth the page. Newer Polymarket accounts are DepositWallet smart contracts. They sign via EIP-1271, which the exchange calls signature type 3. **Polymarket's own Python SDK cannot place orders for them.** It hardcodes the order's signer field to your EOA address, but the exchange needs both maker and signer to be the wallet, with an ERC-7739 wrapped signature the wallet will validate on chain.

You hit it as a 400 saying *the order signer address has to be the address of the API KEY*. There are open upstream issues claiming deposit-wallet users are completely blocked from programmatic order placement. They are not. This is the missing ~60 lines.

The approach is nice and surgical: build the order with the SDK exactly as normal, so you keep its correct amounts, rounding and salt, then rewrite the signer and swap in a signature the contract accepts.

poly_1271.py — the ERC-7739 wrapper a DepositWallet accepts

```python
def erc7739_sign(private_key, wallet, chain_id, app_domain_sep, contents_hash, contents_type):
    """🌙 Moon Dev - the ERC-7739 nested-EIP-712 signature a DepositWallet accepts.

    `contents_type` must start with the struct name (implicit mode), e.g.
    b"Order(uint256 salt,...)". Returns raw bytes, not hex."""
    contents_name = contents_type.split(b"(")[0]
    type_hash = keccak(
        b"TypedDataSign(" + contents_name +
        b" contents,string name,string version,uint256 chainId,"
        b"address verifyingContract,bytes32 salt)" + contents_type)
    struct_hash = keccak(abi_encode(
        ["bytes32", "bytes32", "bytes32", "bytes32", "uint256", "address", "bytes32"],
        [type_hash, contents_hash, keccak(WALLET_DOMAIN_NAME.encode()),
         keccak(WALLET_DOMAIN_VERSION.encode()), chain_id, wallet, WALLET_DOMAIN_SALT]))
    digest = keccak(b"\x19\x01" + app_domain_sep + struct_hash)
    signature = Account._sign_hash(digest, private_key).signature
    return (bytes(signature) + app_domain_sep + contents_hash + contents_type +
            len(contents_type).to_bytes(2, "big"))

def order_struct_hash(order):
    """🌙 Moon Dev - EIP-712 struct hash of a signed V2 order object."""
    return keccak(abi_encode(
        ["bytes32", "uint256", "address", "address", "uint256", "uint256", "uint256",
         "uint8", "uint8", "uint256", "bytes32", "bytes32"],
        [keccak(ORDER_TYPE), int(order.salt), order.maker, order.signer, int(order.tokenId),
         int(order.makerAmount), int(order.takerAmount), int(order.side),
         int(order.signatureType), int(order.timestamp),
         bytes.fromhex(order.metadata[2:]), bytes.fromhex(order.builder[2:])]))

def resign_as_wallet(order, private_key, wallet, chain_id, neg_risk):
    """🌙 Moon Dev - rewrite an SDK-built order into a valid POLY_1271 order.

    The SDK sets signer to your EOA; EIP-1271 needs the WALLET to be the signer,
    with a signature its isValidSignature accepts. Mutates and returns the order."""
    contracts = get_contract_config(chain_id)
    exchange = contracts.neg_risk_exchange_v2 if neg_risk else contracts.exchange_v2
    order.signer = wallet
    app_domain_sep = domain_separator(
        EXCHANGE_DOMAIN_NAME, EXCHANGE_DOMAIN_VERSION, chain_id, exchange)
    signature = erc7739_sign(private_key, wallet, chain_id, app_domain_sep,
                             order_struct_hash(order), ORDER_TYPE)
    order.signature = "0x" + signature.hex()
    return order

def create_and_post_order(client, order_args, options, order_type, post_only,
                          private_key, wallet, chain_id):
    """🌙 Moon Dev - drop-in replacement for client.create_and_post_order() on a
    DepositWallet. Build with the SDK, re-sign as the wallet, then post."""
    order = client.create_order(order_args, options=options)
    resign_as_wallet(order, private_key, wallet, chain_id, options.neg_risk)
    return client.post_order(order, order_type=order_type, post_only=post_only)
```
One detail that trips people up: L1 auth, meaning creating your API credentials, still binds to the EOA. That is what Polymarket's docs specify and it is correct. Only the *order* needs the wallet as signer.

## Real Results So Far (Live, and a Tiny Sample)

From Moon Dev's own log, September 22 and 26, 2026, across 78 resolved windows:

BookCallsWin rateAvg price paidResult on $5 per callConsensus (real money)30 trades36.7% (11 won)$0.34+$10.64 on $146.65 risked⚡ Jev alone (shadow)6674.2%$0.69+$41.02🛸 Astra alone (shadow)5527.3%$0.28+$36.42📖 Fable alone (shadow)2835.7%$0.42−$43.70

A few things are genuinely interesting in there. The consensus **wins less than half the time and still makes money**, because it mostly buys cheap sides at around 34 cents. An average win paid +$9.50 and an average loss cost −$4.94. Of the 30 trades, 19 were all three AIs agreeing and 11 were 2 of 3. Jev wins most often but pays high prices. Astra wins least but buys the cheapest sides. Fable passed on most windows (50 of them) and lost on what it did trade.

**Now the honest part, and please do not skip it.** This is 2 days and 30 trades. That is far too few to call an edge, and anyone who tells you otherwise is selling something. Moon Dev's own earlier testing found this 5-minute market is very efficient, so the starting assumption is still that all three models are close to coin flips paying a spread. A 36.7% win rate on 30 samples has enormous error bars around it. **The CSV is the point. Let it run, then read it.**

## Putting It All Together

Eight files, and they stack cleanly. At the bottom, poly_1271.py makes a DepositWallet able to sign orders at all, and poly_core.py wraps every piece of Polymarket plumbing (account, market lookup, order book, orders, resolution) while making zero trading decisions.

In the middle, ai_5min_core.py is the engine: it gathers the facts, holds the settings, places the order, holds to expiry, and grades against the real resolution. openrouter_brain.py provides the two ways of talking to a model, and the three tiny bot files pick which model to be.

On top, consensus_5min_bot.py is the one you run. Because the round machinery lives entirely in the core, all three models are a fair fight *by construction*: same facts, same $5, same CSV columns, same screen. The only variable in the experiment is the model, which is exactly what you want from an experiment.

FileLinesIts jobconsensus_5min_bot.py765The main file you run. Runs the vote, counts it, places the one trade, keeps the four scorecards, draws the screen.ai_5min_core.py1544The engine. Facts, settings, order placement, holding to expiry, grading.openrouter_brain.py316How the bot talks to the AIs. The chat kind and the decisions kind.jev_5min_bot.py254Jev. Six typed questions, a 58% threshold, and a too-thin veto.astra_5min_bot.py45Astra. Picks the model. Everything else is shared.fable_5min_bot.py40Fable. Same as Astra with a different model.poly_core.py428Polymarket wiring plus the screen helpers and sounds. Makes no trading decisions.poly_1271.py156The signing fix for smart-contract DepositWallets.

Two lines in poly_core.py point at folders on Moon Dev's own computer: the SOUNDS path for the chimes, and the chat-agent .env path. They are not secrets, just local paths. If you do not have those folders you simply get no sounds, and **the bot runs perfectly fine without them**. play_sound never raises on a missing file. You can also set AI5_SILENT=1 to mute it deliberately.

## Settings Worth Knowing

SettingValueWhat it doesUSD_SIZE5Dollars per tradeDECIDE_AT_SEC150Seconds into the window before asking the AIsENTRY_CUTOFF_SEC240No new trade after this pointMAX_ENTRY_PRICE0.80Never pay more than 80 cents for a sideDAILY_STOP_USD−30Stop trading for the day after losing $30LIVE_TRADINGTrueSet AI5_PAPER=1 in your environment to run with no real ordersNEED_AGREE2In consensus_5min_bot.py. Set to 3 to trade only when all three agree.

## Setup and How to Run It

All 8 files go in the same folder. Install the dependencies first:

dependencies

```python
pip install requests web3 py_clob_client_v2 eth-abi eth-account eth-utils
```
Then make a .env file in the project root with these names. The values are your own and you never share them, which is exactly why the code only ever reads them *by name* and no key appears anywhere in these 8 files:

.env — names only, never values

```python
OPENROUTER_API_KEY=        # runs all three AIs
MOONDEV_API_KEY=           # liquidation data

# Polymarket
pm_crack_hft_adderess=
pm_crack_hft_privatekey=
pm_crack_hft_apiKey=
pm_crack_hft_secret=
pm_crack_hft_passphrase=
pm_crack_hft_builderkey=
```
Test your connection, then **paper trade first**. Please actually do this step:

test, then paper trade

```python
python bots/polymarket/bots/test_connection.py

AI5_PAPER=1 python bots/polymarket/bots/consensus_5min_bot.py
```
When you are ready to run it for real:

running the consensus bot

```python
python bots/polymarket/bots/consensus_5min_bot.py        # runs until 30 trades are in the log
python bots/polymarket/bots/consensus_5min_bot.py 50     # or pick your own number
python bots/polymarket/bots/consensus_5min_bot.py 0      # run until you stop it
```
That number is a *total*, not a fresh count. Asking for 50 when the log already holds 10 means forty more, not another fifty. Each AI can also run as its own standalone bot:

each brain, solo

```python
python bots/polymarket/bots/jev_5min_bot.py
python bots/polymarket/bots/astra_5min_bot.py
python bots/polymarket/bots/fable_5min_bot.py
```
Ctrl+C is safe at any time. It grades anything already paid for before it exits, and the next run picks up any trade still open.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/jev-astra-fable-polymarket-5-minute-bot)

## The Complete Code, All 8 Files

Here is every file, complete and unedited, in dependency order. There are no keys or secrets anywhere in here: every credential is read by name from a .env file that is never shared. Drop all 8 into the same folder.

[You can also find these in the GitHub folder: [github.com/Moon-Dev-Crew/moon-dev-trading-bots/tree/main/bots/polymarket/bots](https://github.com/Moon-Dev-Crew/moon-dev-trading-bots/tree/main/bots/polymarket/bots)

### consensus_5min_bot.py

1 of 8 — the main file you run. The vote, the one trade, the four scorecards.

consensus_5min_bot.py

```python
"""
================================================================================
🗳️ MOON DEV's CONSENSUS 5-MINUTE BOT: three AIs vote, the majority trades
================================================================================
Every five minutes, all three brains look at the SAME window with the SAME
facts and each says UP, DOWN or NOTHING. If two or three agree, that side gets
ONE five dollar trade. Everybody is graded, including whoever lost the vote.

    ⚡ JEV    said DOWN
    🛰️ ASTRA  said UP
    📖 FABLE  said DOWN      ->  2 of 3 say DOWN, so we buy DOWN

WHY THIS SHAPE AND NOT THREE BOTS RUNNING AT ONCE
Running three bots side by side puts three orders in the same window and
triples the money at risk to learn the same thing. This asks all three the same
question, pays for ONE answer, and still scores all three. Same data, a third
of the risk.

🕵️ EVERY BRAIN IS SCORED EVEN WHEN IT LOSES THE VOTE. Astra saying UP on a
   window we traded DOWN is not thrown away: the round records what Astra said,
   what UP was priced at, and what it WOULD have paid. So at the end you can
   answer all four questions off one file:

     1. did the CONSENSUS make money
     2. would JEV alone have made money
     3. would ASTRA alone have made money
     4. would FABLE alone have made money

   Only #1 is real money. The other three are shadow books, priced at the
   actual ask on the screen at the moment of the call, so they are honest about
   what they would have paid rather than assuming a perfect fill.

🚨 ONE TRADE PER WINDOW. EVER. The money at risk in any window is USD_SIZE and
   never a multiple of it, no matter how many brains are voting.

RUN  python bots/polymarket/bots/consensus_5min_bot.py        # 10 traded rounds
     python bots/polymarket/bots/consensus_5min_bot.py 30     # or however many
     python bots/polymarket/bots/consensus_5min_bot.py 0      # until you stop it

Ctrl+C is safe at any time: it grades whatever it already paid for before it
exits, and the next run picks up anything still open.

Built by Moon Dev 🌙
================================================================================
"""

import os
import sys
import csv
import time
import signal
import traceback
from concurrent.futures import ThreadPoolExecutor

from datetime import datetime

from ai_5min_core import (say, out, rule, row, pin, tag, sticky, unstick, clock,
                          when, phase_name, chime, gather, enter, book,
                          shares_for, market_meta, window_now, get_market,
                          get_resolution, balance, append_csv,
                          open_load, open_add, open_drop, wait_until,
                          DATA_DIR, MARKET_DURATION, USD_SIZE, LIVE_TRADING,
                          DECIDE_AT_SEC, ENTRY_CUTOFF_SEC, MAX_ENTRY_PRICE,
                          DAILY_STOP_USD, SETTLE_PATIENCE_SEC,
                          ROUND_SOUND, UP_SOUND, DOWN_SOUND, DENIED_SOUND,
                          NB, GREEN, RED, YELLOW, CYAN, MAG, BOLD, DIM, OFF)

from jev_5min_bot import Jev
from astra_5min_bot import Astra
from fable_5min_bot import Fable

# 🗳️ THE VOTERS. Add a fourth and everything below adapts: the vote panel, the
#    CSV columns, the scorecards. Nothing here is hardcoded to three.
VOTERS = [Jev, Astra, Fable]

# 🗳️ how many must agree before real money moves. Two of three is a majority.
#    Raise to 3 to only trade when they are unanimous.
NEED_AGREE = 2

LOG = os.path.join(DATA_DIR, "consensus_rounds.csv")
LEDGER_KEY = "consensus"

class _Ledger:
    """🌙 Moon Dev - the vote is not a brain, but the shared plumbing expects
    one: the open-position file keys off KEY, and the status bar prints NAME
    and EMOJI. This is the consensus wearing a brain's clothes."""
    KEY = LEDGER_KEY
    NAME = "VOTE"
    EMOJI = "🗳️"
    MODEL = " + ".join(v.NAME for v in VOTERS)

def header():
    """🌙 Moon Dev - ONE ROW PER WINDOW, WIDE. Every brain gets its own block
    of columns so the whole study is one file you can open in a spreadsheet and
    sort, with nothing to join and nothing to reconstruct later."""
    cols = ["round_ts", "time", "slug",
            "consensus", "votes_up", "votes_down", "votes_pass", "agreed",
            "traded", "entry_price", "shares", "usd_risked",
            "resolution", "consensus_won", "consensus_pnl", "consensus_roi",
            "strike", "twap_minus_strike", "spot_minus_strike", "secs_left",
            "p_up_model", "book_p_up", "book_resid", "up_ask", "down_ask",
            "liq_long_usd", "liq_short_usd"]
    for v in VOTERS:
        k = v.KEY
        # 🕵️ the shadow book: what this brain said, what its side cost at the
        #    time, whether it was right, and what it would have paid.
        cols += [f"{k}_side", f"{k}_p_up", f"{k}_conf", f"{k}_won",
                 f"{k}_shadow_entry", f"{k}_shadow_roi",
                 f"{k}_latency_ms", f"{k}_cost_usd", f"{k}_why"]
    return cols

# ─── 🗳️ MOON DEV - THE VOTE ─────────────────────────────────────────────────
def collect(brains, pack, record):
    """🗳️ Moon Dev - ask all three AT ONCE and wait for the slowest.

    In parallel because they are wildly different speeds: Jev answers in about
    0.4 seconds, Astra in 5, Fable in 12. Asked one after another that is 17
    seconds of a 300 second window spent waiting, and the price moves while you
    wait. Asked together it costs whatever the slowest one costs.

    Every brain sees the SAME pack. That is the entire point of this bot: any
    difference in their answers is the brain, never the data."""
    def ask(cls):
        b = cls()
        t0 = time.time()
        try:
            side, p_up, conf, why, detail = b.decide(pack, record)
        except Exception as e:
            # 🌙 one brain falling over must not cost the round. It abstains,
            #    loudly, and the other two still vote.
            # 🚨 SAY WHAT ACTUALLY WENT WRONG. A handler that prints only the
            #    exception TYPE turns a one-line bug into a hunt, and it did.
            return {"brain": b, "side": None, "p_up": "", "conf": "",
                    "why": f"{b.NAME} failed: {type(e).__name__}: {e}",
                    "detail": {"latency_ms": (time.time() - t0) * 1000},
                    "failed": True}
        return {"brain": b, "side": side, "p_up": p_up, "conf": conf,
                "why": why, "detail": detail, "failed": False}

    with ThreadPoolExecutor(max_workers=len(brains)) as pool:
        return list(pool.map(ask, brains))

def tally(votes):
    """🗳️ Moon Dev - (winning side, up, down, pass, how many agreed).

    A NOTHING is an ABSTENTION, not a vote against. Two brains saying DOWN and
    one saying NOTHING is a majority for DOWN, because nobody argued the other
    way. One UP against one DOWN is a split room and we sit it out however many
    abstained."""
    up = sum(v["side"] == "Up" for v in votes)
    down = sum(v["side"] == "Down" for v in votes)
    passes = len(votes) - up - down
    if up >= NEED_AGREE and up > down:
        return ("Up", up, down, passes, up)
    if down >= NEED_AGREE and down > up:
        return ("Down", up, down, passes, down)
    return (None, up, down, passes, max(up, down))

def show_votes(votes, side, up, down, passes):
    """🗳️ Moon Dev - THE PANEL. Who said what, and what it added up to.

    This is the shot you want on screen. One glance says which brains agreed,
    which one is the odd one out, and whether that was enough to trade."""
    out()
    rule(MAG)
    say("🗳️  THE VOTE", MAG + BOLD)
    for v in votes:
        b = v["brain"]
        agree = ("" if side is None else
                 f"  {GREEN}{BOLD}✓ with the majority{OFF}" if v["side"] == side
                 else f"  {DIM}outvoted{OFF}" if v["side"] else
                 f"  {DIM}abstained{OFF}")
        conf = f" {DIM}{v['conf']}{OFF}" if v["conf"] != "" else ""
        row(f"{b.EMOJI} {BOLD}{b.NAME:<6}{OFF} {tag(v['side'])}{conf}{agree}")
    row("")
    counts = (f"{GREEN}{BOLD}▲{up}{OFF}  {RED}{BOLD}▼{down}{OFF}  "
              f"{DIM}—{passes}{OFF}")
    if side:
        row(f"{counts}   →  {BOLD}MAJORITY{OFF} {tag(side)}")
    else:
        row(f"{counts}   →  {YELLOW}{BOLD}NO MAJORITY, sitting out{OFF}")
    rule(MAG)
    chime(UP_SOUND if side == "Up" else
          DOWN_SOUND if side == "Down" else DENIED_SOUND)

# ─── 🕵️ MOON DEV - THE SHADOW BOOKS ─────────────────────────────────────────
def shadow(side, winner, up_ask, down_ask):
    """🕵️ Moon Dev - (entry it would have paid, was it right, what it returns).

    Priced at the ACTUAL ask on screen when the call was made, not at a
    pretend fill. A brain that keeps picking 0.85 favourites should look bad
    here even when it is usually right, because that is the truth about it.

    A brain that abstained returns 0: no trade, no gain, no loss. Being right
    about sitting out is scored on its own, further down."""
    if side is None:
        return ("", "", "")
    entry = up_ask if side == "Up" else down_ask
    if not entry:
        return ("", "", "")
    won = side == winner
    return (round(entry, 4), won, round((1 - entry) / entry if won else -1.0, 4))

# ─── 📋 MOON DEV - THE FOUR SCORECARDS ──────────────────────────────────────
class Board:
    """📋 Moon Dev - the consensus plus every brain, side by side, live.

    Four books. One of them spent real money; the other three are what would
    have happened. All four are graded against the same resolutions."""

    def __init__(self):
        self.rounds = 0
        self.who = {"CONSENSUS": self._blank()}
        for v in VOTERS:
            self.who[v.NAME] = self._blank()
        self.load()

    @staticmethod
    def _blank():
        return {"calls": 0, "wins": 0, "passes": 0, "pass_right": 0,
                "risked": 0.0, "pnl": 0.0, "need_num": 0.0, "streak": []}

    def _score(self, name, side, winner, entry, roi, real_pnl=None):
        d = self.who[name]
        if side is None:
            d["passes"] += 1
            d["pass_right"] += 0          # graded separately, below
            d["streak"] = (d["streak"] + ["."])[-12:]
            return
        d["calls"] += 1
        won = side == winner
        d["wins"] += won
        d["streak"] = (d["streak"] + ["W" if won else "L"])[-12:]
        if entry:
            # 🌙 shadow books all bet the SAME notional, so their returns are
            #    comparable to each other and to the real one.
            stake = USD_SIZE
            d["risked"] += stake
            d["need_num"] += entry * stake
            d["pnl"] += (real_pnl if real_pnl is not None else roi * stake)

    def load(self):
        if not os.path.exists(LOG):
            return
        with open(LOG) as f:
            for r in csv.DictReader(f):
                if not r.get("resolution"):
                    continue
                self.rounds += 1
                self._score("CONSENSUS", r.get("consensus") or None,
                            r["resolution"], _f(r.get("entry_price")),
                            _f(r.get("consensus_roi")), _f(r.get("consensus_pnl")))
                for v in VOTERS:
                    self._score(v.NAME, r.get(f"{v.KEY}_side") or None,
                                r["resolution"], _f(r.get(f"{v.KEY}_shadow_entry")),
                                _f(r.get(f"{v.KEY}_shadow_roi")))

    def add(self, row_dict, winner):
        self.rounds += 1
        self._score("CONSENSUS", row_dict["consensus"] or None, winner,
                    _f(row_dict["entry_price"]), _f(row_dict["consensus_roi"]),
                    _f(row_dict["consensus_pnl"]))
        for v in VOTERS:
            self._score(v.NAME, row_dict[f"{v.KEY}_side"] or None, winner,
                        _f(row_dict[f"{v.KEY}_shadow_entry"]),
                        _f(row_dict[f"{v.KEY}_shadow_roi"]))

    def summary(self):
        """📋 Moon Dev - the record, in plain English, for the brains to read.

        Every brain is shown the SAME line: how the VOTE has done. Not its own
        shadow book. Showing each one its personal record would give them
        different packs, and identical packs is the one thing that makes this
        comparison worth anything."""
        d = self.who["CONSENSUS"]
        if not self.rounds:
            return "no graded rounds yet, this is the first one"
        pct = f"{d['wins'] / d['calls'] * 100:.0f}%" if d["calls"] else "n/a"
        return (f"the majority vote has called {d['calls']} windows, {d['wins']} "
                f"right ({pct}), sat out {d['passes']}, and is "
                f"${d['pnl']:+.2f} on real trades across {self.rounds} rounds")

    def line(self, name):
        d = self.who[name]
        if not d["calls"] and not d["passes"]:
            return f"{DIM}nothing graded yet{OFF}"
        pct = f"{d['wins'] / d['calls'] * 100:.0f}%" if d["calls"] else "n/a"
        c = GREEN if d["pnl"] > 0 else (RED if d["pnl"] < 0 else DIM)
        roi = f" {c}{d['pnl'] / d['risked']:+.0%}{OFF}" if d["risked"] else ""
        need = (f"  {DIM}need{NB}{d['need_num'] / d['risked']:.0%}{OFF}"
                if d["risked"] else "")
        return (f"{BOLD}{d['wins']}/{d['calls']}{OFF} ({pct})  "
                f"{DIM}{d['passes']}{NB}pass{OFF}  {c}{BOLD}${d['pnl']:+.2f}{OFF}"
                f"{roi}{need}  {''.join(d['streak'])}")

    def show(self):
        out()
        rule(CYAN)
        say("📋  THE FOUR BOOKS  " + DIM + "(only the top one spent real money)"
            + OFF, CYAN + BOLD)
        row(f"💰 {BOLD}CONSENSUS{OFF}  {self.line('CONSENSUS')}")
        for v in VOTERS:
            row(f"{v.EMOJI} {DIM}shadow{OFF} {v.NAME:<6} {self.line(v.NAME)}")
        rule(CYAN)

    def bar(self, target, traded):
        bits = [f"💰{self.line_short('CONSENSUS')}"]
        for v in VOTERS:
            bits.append(f"{v.EMOJI}{self.line_short(v.NAME)}")
        goal = f"{traded}/{target}" if target else str(traded)
        return (f"{CYAN}{BOLD}🗳️{goal}{OFF} " + " ".join(bits))

    def line_short(self, name):
        d = self.who[name]
        c = GREEN if d["pnl"] > 0 else (RED if d["pnl"] < 0 else DIM)
        return f"{d['wins']}/{d['calls']}{c}{d['pnl']:+.0f}{OFF}"

def today_pnl():
    """🛑 Moon Dev - real dollars won or lost since midnight, for the daily
    stop. Shadow books do not count: they never spent anything."""
    if not os.path.exists(LOG):
        return 0.0
    start = datetime.now().replace(hour=0, minute=0, second=0,
                                   microsecond=0).timestamp()
    total = 0.0
    with open(LOG) as f:
        for r in csv.DictReader(f):
            if r.get("resolution") and _f(r.get("round_ts")) >= start:
                total += _f(r.get("consensus_pnl"))
    return total

def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0

# ─── 🌙 MOON DEV - ONE ROUND ────────────────────────────────────────────────
def run_round(market, board, pending):
    ts = market["ts"]
    end = ts + MARKET_DURATION

    out()
    rule()
    say(f"🗳️  ROUND {when(ts)} BTC  ·  three AIs vote", CYAN + BOLD)
    row(f"{len(VOTERS)} brains, {NEED_AGREE} must agree, {BOLD}one ${USD_SIZE} "
        f"trade{OFF} if they do.")
    out(f"{DIM}https://polymarket.com/event/{market['slug']}{OFF}")
    rule()
    chime(ROUND_SOUND)

    wait_until(_Ledger, ts, ts + DECIDE_AT_SEC,
               f"{CYAN}{phase_name('GATHERING', 'DATA')}{OFF}")
    say("📡  Pulling the bars, the TWAP and everyone else's positions.", CYAN)
    pack = gather(market)
    if pack is None:
        say("⛔  A feed is down. Real data or no bet, so this round is skipped.",
            YELLOW + BOLD)
        return None

    p, b = pack["price"], pack["book"]
    tw = p["twap_minus_strike_usd"]
    row(f"🎯 strike {BOLD}{p['strike_window_open']:,}{OFF}  TWAP "
        f"{(GREEN if tw >= 0 else RED)}{BOLD}{tw:+,.2f}{OFF}"
        f"{DIM}({p['seconds_of_twap_locked_in']}s locked){OFF}  spot "
        f"{p['cushion_usd']:+,.2f}")
    row(f"📖 up {b['up_ask']}  down {b['down_ask']}  "
        f"{DIM}model P(Up) {pack['fair_value']['p_up_using_1h_vol']:.2f}{OFF}")

    say(f"🗳️  All {len(VOTERS)} brains are deciding at once.", MAG + BOLD)
    pin(_Ledger, ts, f"{MAG}{phase_name('VOTING', 'VOTE')}{OFF}", end - time.time())
    votes = collect(VOTERS, pack, board)
    side, up, down, passes, agreed = tally(votes)
    show_votes(votes, side, up, down, passes)
    for v in votes:
        if v["why"]:
            row(f"{v['brain'].EMOJI}{DIM}│{OFF} {v['why'][:150]}")

    rec = {c: "" for c in header()}
    rec.update({
        "round_ts": ts, "time": when(ts), "slug": market["slug"],
        "consensus": side or "", "votes_up": up, "votes_down": down,
        "votes_pass": passes, "agreed": agreed, "traded": False,
        "strike": p["strike_window_open"], "twap_minus_strike": tw,
        "spot_minus_strike": p["cushion_usd"],
        "secs_left": pack["market"]["seconds_left_in_window"],
        "p_up_model": pack["fair_value"]["p_up_using_1h_vol"],
        "book_p_up": b["market_implied_p_up"],
        "book_resid": b["book_minus_model_p_up"],
        "up_ask": b["up_ask"], "down_ask": b["down_ask"],
        "liq_long_usd": pack["liquidations"].get("longs_below_spot", {})
                                            .get("total_value_usd", ""),
        "liq_short_usd": pack["liquidations"].get("shorts_above_spot", {})
                                             .get("total_value_usd", ""),
    })
    for v in votes:
        k = v["brain"].KEY
        rec[f"{k}_side"] = v["side"] or ""
        rec[f"{k}_p_up"] = v["p_up"]
        rec[f"{k}_conf"] = v["conf"]
        rec[f"{k}_why"] = (v["why"] or "")[:300]
        rec[f"{k}_latency_ms"] = v["detail"].get("latency_ms", "")
        rec[f"{k}_cost_usd"] = v["detail"].get("cost_usd", "")

    if side is None:
        hold_out(end, ts, board, pending, "no majority")
        return rec

    # 🚨 never two positions in one window, however the vote went
    held = open_load(_Ledger).get(market["slug"])
    if held and held.get("traded"):
        say(f"🛑  ALREADY IN THIS WINDOW from an earlier run: "
            f"{held['shares']:.2f} {tag(held['side'])} @{NB}{BOLD}"
            f"{held['price']:.2f}{OFF}. NOT buying again.", YELLOW + BOLD)
        rec.update(traded=True, consensus=held["side"],
                   entry_price=held["price"], shares=held["shares"],
                   usd_risked=round(held["price"] * held["shares"], 2))
        hold_out(end, ts, board, pending, "adopted")
        return rec

    if time.time() > ts + ENTRY_CUTOFF_SEC:
        say(f"⛔  The vote took too long, only {clock(end - time.time())} left. "
            f"Logging every call, skipping the trade.", YELLOW)
        hold_out(end, ts, board, pending, "too late")
        return rec

    token = market["tokens"][side]
    _, ask = book(token)
    if ask is None:
        say(f"⛔  Nobody is offering {side}. Nothing to buy.", YELLOW)
        hold_out(end, ts, board, pending, "no ask")
        return rec
    if ask > MAX_ENTRY_PRICE:
        say(f"⛔  {side} is {ask:.2f}, over the {MAX_ENTRY_PRICE:.2f} ceiling. "
            f"Every call still logged.", YELLOW)
        hold_out(end, ts, board, pending, "over ceiling")
        return rec

    today = today_pnl()
    if today <= DAILY_STOP_USD:
        say(f"🛑  Daily stop hit: ${today:.2f} today. Every call is still "
            f"logged and every shadow book still runs, but no money moves.",
            RED + BOLD)
        hold_out(end, ts, board, pending, "daily stop")
        return rec

    size = shares_for(USD_SIZE, ask)
    out()
    say(f"💰  BUY {size:.2f} {tag(side)} @{NB}{BOLD}{ask:.2f}{OFF} "
        f"={NB}{BOLD}${ask * size:.2f}{OFF}   {DIM}({agreed} of "
        f"{len(VOTERS)} agreed){OFF}", GREEN + BOLD)
    row(f"🎯 pays {BOLD}{(1 - ask) / ask:+.0%}{OFF} if right, {RED}-100%{OFF} "
        f"if wrong  →  needs to be right {BOLD}{ask:.0%}{OFF} of the time")

    if LIVE_TRADING:
        got = enter(token, side, ask, size)
        if got.get("traded"):
            rec.update(traded=True, entry_price=round(got["price"], 4),
                       shares=round(got["shares"], 2),
                       usd_risked=round(got["price"] * got["shares"], 2))
            open_add(_Ledger, {"ts": ts, "slug": market["slug"], "side": side,
                               "price": got["price"], "shares": got["shares"],
                               "p_up": "", "confidence": "", "why": "consensus",
                               "detail": {}, "traded": True, "skip_reason": "",
                               "pack": None})
    else:
        say("📝  LIVE_TRADING is off, so no order was sent. Every call and "
            "every shadow book is still real.", YELLOW)
        rec.update(entry_price=round(ask, 4), shares=size,
                   usd_risked=round(ask * size, 2))

    hold_out(end, ts, board, pending, side)
    return rec

def hold_out(end, ts, board, pending, what):
    """🌙 Moon Dev - wait the window out, grading older rounds while we wait."""
    next_beat, next_settle = 0.0, time.time() + 15
    while time.time() < end:
        if pending and time.time() > next_settle:
            next_settle = time.time() + 15
            pending[:] = [r for r in pending if not settle(r, board)]
        if time.time() > next_beat:
            next_beat = time.time() + 30
            row(f"⏱  {what}  {clock(end - time.time())} left")
        pin(_Ledger, ts, f"{YELLOW}{phase_name('SETTLES IN', 'SETTLE')}{OFF}",
            end - time.time())
        time.sleep(0.5)

# ─── 🏁 MOON DEV - SETTLEMENT ───────────────────────────────────────────────
def settle(rec, board):
    """🏁 Moon Dev - grade the consensus AND all three shadow books at once."""
    winner = get_resolution(rec["slug"])
    if winner is None:
        return False

    rec["resolution"] = winner
    traded = rec["traded"] is True
    price, shares = _f(rec["entry_price"]), _f(rec["shares"])
    side = rec["consensus"] or None
    won = bool(side) and side == winner
    pnl = ((shares * (1 - price) if won else -shares * price)
           if traded and price else 0.0)
    rec["consensus_won"] = won if side else ""
    rec["consensus_pnl"] = round(pnl, 2) if traded else ""
    rec["consensus_roi"] = (round(pnl / (price * shares), 4)
                            if traded and price * shares else "")

    # 🕵️ the three shadow books, priced at the ask that was on screen.
    for v in VOTERS:
        k = v.KEY
        entry, w, roi = shadow(rec[f"{k}_side"] or None, winner,
                               _f(rec["up_ask"]), _f(rec["down_ask"]))
        rec[f"{k}_shadow_entry"] = entry
        rec[f"{k}_won"] = w
        rec[f"{k}_shadow_roi"] = roi

    append_csv(LOG, header(), [rec[c] for c in header()])
    open_drop(_Ledger, rec["slug"])
    board.add(rec, winner)

    out()
    rule(GREEN if winner == "Up" else RED)
    say(f"🏁  {rec['time']} SETTLED {tag(winner)}", BOLD)
    if side:
        mark = (f"{GREEN}{BOLD}✅ RIGHT{OFF}" if won else
                f"{RED}{BOLD}❌ WRONG{OFF}")
        row(f"consensus said {tag(side)}  {mark}"
            + (f"   ${price * shares:.2f} at risk  "
               f"{(GREEN if won else RED)}{BOLD}{pnl:+.2f}"
               f"{NB}({pnl / (price * shares):+.0%}){OFF}"
               if traded and price * shares else f"   {DIM}not traded{OFF}"))
    else:
        row(f"{DIM}no majority, nothing traded{OFF}")
    # 🕵️ who was right, including whoever lost the vote
    for v in VOTERS:
        k = v.KEY
        s = rec[f"{k}_side"]
        if not s:
            row(f"{v.EMOJI} {DIM}{v.NAME} abstained{OFF}")
            continue
        ok = rec[f"{k}_won"] is True
        roi = _f(rec[f"{k}_shadow_roi"])
        row(f"{v.EMOJI} {v.NAME} said {tag(s)}  "
            f"{GREEN if ok else RED}{BOLD}{'RIGHT' if ok else 'WRONG'}{OFF}  "
            f"{DIM}shadow {roi:+.0%} at {_f(rec[f'{k}_shadow_entry']):.2f}{OFF}")
    rule(GREEN if winner == "Up" else RED)
    board.show()
    return True

def drain(pending, board):
    """🌙 Moon Dev - never exit holding an ungraded round we paid for."""
    if not pending:
        return
    deadline = time.time() + SETTLE_PATIENCE_SEC
    say(f"⏳  Waiting on {len(pending)} round(s) to resolve before stopping.",
        CYAN + BOLD)
    while pending and time.time() < deadline:
        pending[:] = [r for r in pending if not settle(r, board)]
        if not pending:
            break
        sticky(f"{CYAN}⏳ settling {len(pending)}{OFF} │ giving up in "
               f"{clock(deadline - time.time())}")
        time.sleep(15)
    unstick()
    for r in pending:
        say(f"⚠️  {r['slug']} never resolved in time. Not in the CSV.", YELLOW)

# ─── 🌙 MOON DEV - STAYING ALIVE ────────────────────────────────────────────
def _graceful(signum, _frame):
    """🌙 Moon Dev - a kill signal must still grade what we already paid for.

    🚨 Ctrl+C RAISES KeyboardInterrupt. NOTHING ELSE DOES. A `kill`, a closed
       terminal, a logout, a machine going to sleep: all of those send SIGTERM
       or SIGHUP, which end the process instantly and skip every bit of cleanup
       below. That means a live position with no CSV row and no ledger entry:
       money spent, nothing recorded, and no way to reconstruct it.

       Turning those signals into the same interrupt Ctrl+C raises means every
       exit runs the same drain, whatever ended the run."""
    raise KeyboardInterrupt(f"signal {signum}")

def install_signals():
    for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT):
        try:
            signal.signal(sig, _graceful)
        except (ValueError, OSError, AttributeError):
            pass        # 🌙 not every platform has every signal. Never fatal.

def main():
    target = 30
    if len(sys.argv) > 1:
        if not sys.argv[1].isdigit():
            say(f"'{sys.argv[1]}' is not a number of trades.", RED)
            return
        target = int(sys.argv[1])

    rule()
    say("🗳️  MOON DEV's CONSENSUS 5-MINUTE BOT", CYAN + BOLD)
    row("Three AIs see the same window and the same facts. "
        f"{NEED_AGREE} must agree before money moves.")
    row(" · ".join(f"{v.EMOJI} {v.NAME}" for v in VOTERS))
    row(f"{BOLD}One ${USD_SIZE} trade per window{OFF}, never more, however many "
        f"brains vote.")
    row("Everybody is graded, including whoever loses the vote.")
    row(f"{BOLD}Stopping once the log holds {target} traded rounds.{OFF}"
        if target else f"{BOLD}Running until you stop it.{OFF}")
    row(f"{DIM}log {LOG}{OFF}")
    rule()

    for cls in VOTERS:
        try:
            cls().check()
        except Exception as e:
            say(f"❌  {e}", RED + BOLD)
            return
    if not LIVE_TRADING:
        say("📝  LIVE_TRADING is OFF. Votes and shadow books are real, orders "
            "are not.", YELLOW + BOLD)

    board = Board()
    board.show()

    # 🌉 THE TARGET IS A TOTAL, NOT A FRESH COUNT. Asking for 25 when the log
    #    already holds 10 means fifteen more, not another twenty five. Every
    #    other bot in this folder counts that way and a number that quietly
    #    means something different depending on which file you ran is how a
    #    study ends up with the wrong sample size in the write-up.
    done_already = 0
    if os.path.exists(LOG):
        with open(LOG) as f:
            done_already = sum(1 for r in csv.DictReader(f)
                               if r.get("traded") == "True")
    owed = max(0, target - done_already) if target else 0
    if target:
        if done_already:
            say(f"🌉  {done_already} traded round(s) already in the log. "
                f"Taking {owed} more to reach {target}.", CYAN + BOLD)
        if not owed:
            say(f"✅  Already at {done_already} traded rounds. Nothing to do. "
                f"Ask for more than {target} to keep going.", GREEN + BOLD)
            return
    try:
        say(f"💵  Your balance is ${balance():,.2f}.", CYAN)
    except Exception as e:
        say(f"Could not read your balance ({type(e).__name__}).", RED)
        return

    # 🌉 anything left open by a previous run gets picked up and graded
    pending = []
    for slug, r in sorted(open_load(_Ledger).items(),
                          key=lambda kv: kv[1].get("ts", 0)):
        rec = {c: "" for c in header()}
        rec.update({"round_ts": r["ts"], "time": when(r["ts"]), "slug": slug,
                    "consensus": r["side"], "traded": True,
                    "entry_price": r["price"], "shares": r["shares"],
                    "usd_risked": round(r["price"] * r["shares"], 2)})
        pending.append(rec)
    if pending:
        say(f"🌉  Picking up {len(pending)} position(s) from the last run.",
            CYAN + BOLD)

    install_signals()
    traded = played = 0
    last_ts, next_settle = None, 0.0
    hiccups = 0
    try:
        while True:
            if pending and time.time() > next_settle:
                next_settle = time.time() + 15
                pending = [r for r in pending if not settle(r, board)]

            ts = window_now()
            if ts == last_ts:
                pin(_Ledger, ts, f"{DIM}{phase_name('NEXT ROUND IN', 'NEXT')}{OFF}",
                    ts + MARKET_DURATION - time.time())
                sticky(board.bar(target, traded))
                time.sleep(1)
                continue

            market = get_market(ts, "BTC")
            if not market:
                say("No BTC market posted for this window yet. Waiting.", YELLOW)
                time.sleep(2)
                continue
            if time.time() > ts + ENTRY_CUTOFF_SEC:
                say("Joined this window too late to call it. Waiting.", YELLOW)
                last_ts = ts
                continue

            last_ts = ts
            for s in ("Up", "Down"):
                try:
                    market_meta(market["tokens"][s])
                except Exception:
                    pass

            # 🚨 A BAD WINDOW MUST NOT END A THIRTY ROUND RUN. One timed-out
            #    API call, one malformed book, one blip: the old code let that
            #    propagate and the whole unattended study stopped hours early
            #    with nothing on screen to say why. Now the window is skipped,
            #    the error is printed in full, and the next window runs.
            #    KeyboardInterrupt is deliberately NOT caught here, so Ctrl+C
            #    and kill signals still stop cleanly.
            try:
                rec = run_round(market, board, pending)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                hiccups += 1
                say(f"⚠️  This window blew up: {type(e).__name__}: {e}", RED + BOLD)
                for line in traceback.format_exc().strip().split("\n")[-4:]:
                    row(f"{DIM}{line[:150]}{OFF}")
                say(f"↩️  Skipping it and carrying on. {hiccups} hiccup(s) so "
                    f"far, {traded} trades still good.", YELLOW)
                time.sleep(2)
                continue
            played += 1
            if rec is None:
                continue
            pending.append(rec)
            if rec["traded"] is True:
                traded += 1
                say(f"📊  {done_already + traded} of {target} traded rounds "
                    f"({played} windows seen this run).", CYAN + BOLD)
                if owed and traded >= owed:
                    break
    except KeyboardInterrupt:
        unstick()
        say(f"⌨️  Ctrl+C after {traded} traded rounds. Grading what is still "
            f"open before stopping.", YELLOW + BOLD)

    drain(pending, board)
    out()
    rule(MAG)
    say(f"🏁  DONE: {traded} traded rounds out of {played} windows."
        + (f"  {hiccups} window(s) skipped on errors." if hiccups else ""),
        MAG + BOLD)
    rule(MAG)
    board.show()
    say(f"📄  {LOG}", CYAN)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        unstick()
    finally:
        unstick()
```
### ai_5min_core.py

2 of 8 — the engine. Facts, settings, orders, holding, grading.

ai_5min_core.py

```python
"""
================================================================================
🌙 MOON DEV's AI 5-MINUTE CORE: one round, three different brains
================================================================================
Every five minutes Polymarket opens a new BTC up-or-down market. This file runs
that round end to end: it gathers the facts, hands them to a BRAIN, buys the
side the brain picked, holds to expiry, and grades the call against the real
resolution.

The brain is the only thing that changes. jev_5min_bot.py, astra_5min_bot.py
and fable_5min_bot.py are each about 120 lines and all they do is answer one
question: UP, DOWN, or NOTHING. Everything else on screen and on disk is this
file, so the three bots are a fair fight by construction.

WHAT THE BRAIN IS SHOWN (all of it real, none of it faked)
  📈 the last 24 hours of 5-minute bars from Binance, all 288 of them
  🎯 the STRIKE — the Binance 1-minute open at the top of this window, which is
     the number Polymarket settles against — and how far spot sits above it
  🧮 a fair value for Up from the barrier model, and how far the BOOK is from it
  🐋 every BTC position on Hyperliquid sitting near liquidation, from the Moon
     Dev API, split into the pool above spot and the pool below it
  📋 this bot's own record so far, wins, losses and dollars

🚨 EVERY NUMBER THE BRAIN NEEDS IS COMPUTED HERE, IN PYTHON, BEFORE IT IS SENT.
   Jev reads literally and cannot divide. Astra and Fable can, but an LLM doing
   arithmetic in its head is a coin flip dressed as a calculation. So the ratios,
   the returns, the vol and the probability are finished facts by the time any
   model sees them, and the model is only ever asked for a JUDGEMENT.

🚨 THE CONTEXT IS THE BINDING CONSTRAINT. Jev takes 32k tokens, and the pack
   costs about 5,900 of them as JSON. It is measured before every send and the
   oldest bars are dropped until it fits. Nothing is ever silently truncated:
   the trim is printed and recorded.

🌙 ALL THREE BOTS RUN ON ONE OPENROUTER_API_KEY. Astra and Fable go to
   /chat/completions, Jev goes to /api/alpha/decisions. No second vendor, no
   second key, no extra SDK. See openrouter_brain.py.

Run a bot, not this file:
    python bots/polymarket/bots/jev_5min_bot.py
    python bots/polymarket/bots/astra_5min_bot.py
    python bots/polymarket/bots/fable_5min_bot.py

Built by Moon Dev 🌙
================================================================================
"""

import os
import sys
import csv
import threading
import json
import math
import time
import statistics
from datetime import datetime

import requests

from poly_core import (say, out, sticky, unstick, width, wrap, narrow,
                       phase_name, clock, when, play_sound, SOUNDS, client,
                       FILL_SOUND, CANCEL_SOUND, HERE, book, place,
                       cancel_all_on, position_in, balance, market_meta,
                       window_now, get_market, get_resolution, shares_for,
                       MARKET_DURATION,
                       GREEN, RED, YELLOW, CYAN, MAG, BOLD, DIM, OFF)

# ─── 🌙 MOON DEV - THE ONLY KNOBS THAT MATTER ───────────────────────────────
ASSET = "BTC"              # 🪙 the 5-minute market we are calling
USD_SIZE = 5               # 💰 dollars per trade
# 🚦 False = do everything real EXCEPT send the order.
#
# 🚨 AI5_PAPER=1 IN THE ENVIRONMENT FORCES THIS OFF, and it exists because
#    setting this constant in one process does NOT reach the others. The fleet
#    runs each brain as its own process, so a parent that flips this flag and
#    then spawns children has flipped nothing — the children import this module
#    fresh, read True, and trade real money. That happened, and it cost a real
#    $5 order during what was supposed to be a dry run. The environment is the
#    only switch that crosses a process boundary, so it wins over the constant.
LIVE_TRADING = True and os.getenv("AI5_PAPER") != "1"
# 🧠 SECONDS INTO THE WINDOW BEFORE WE ASK. This was 15 and 15 was too early.
#
#    The market settles on the AVERAGE across five minutes. At 15 seconds in,
#    only 5% of that average is locked and the TWAP margin is always small: the
#    first three live rounds came in at $8, $12 and $19 from the strike. Those
#    are all inside the feed noise, so the model sat at 0.50 every time and
#    both reasoning brains correctly refused to trade a coin flip. Three rounds,
#    zero trades, and they were right to pass.
#
#    At the halfway mark HALF the answer is already locked in and cannot be
#    undone, so the margin means something and the probability moves off 0.50.
#
#    The cost is a worse price: by 150 seconds the book has worked it out too,
#    so the side you want is dearer. That trade-off is the experiment. Push it
#    later for more certainty and a worse fill, earlier for the reverse.
DECIDE_AT_SEC = 150
ENTRY_CUTOFF_SEC = 240     # ⏰ no new entry past here. A reasoning model can
                           #    think for a minute; if the answer lands with
                           #    under 60s left that is not a trade, it is a
                           #    lottery ticket with a spread on it.
FILL_WAIT_SEC = 20         # ⏱️ how long to watch for the fill before giving up
BAR_HOURS = 24             # 📈 how much 5-minute history the brain is shown
DAILY_STOP_USD = -30.0     # 🛑 realized loss for the day that stops new entries
MAX_ROUNDS_PER_BRAIN = 40  # 🛑 the walk-away stop. A brain that passes on
                           #    almost everything could run all night chasing
                           #    ten trades, so 40 windows (about 3h20m) is the
                           #    cap. Hitting it is a RESULT, not a crash.
PROVISIONAL_MIN_EDGE_USD = 30.0   # ⚡ how far the TWAP must sit from the strike
                           #    before we will call a window early off Binance.
                           #    Polymarket settles on CHAINLINK, and the two
                           #    feeds disagree by a few dollars, so a $10 margin
                           #    is a guess. $30 is outside the observed basis.
SETTLE_PATIENCE_SEC = 900  # ⏳ how long a finished run waits for its last rounds
                           #    to resolve before giving up on them. Polymarket
                           #    takes 5-8 minutes, so 15 is plenty of room.

# 💸 THE PRICE CEILING, and it is here because Moon Dev's own data put it here.
#    Re-mining 1,533 resolved fills: entries above 0.80 LOST money across 484 of
#    them. This is not a hunch and it is not the model second-guessing the brain,
#    it is a measured cliff. Set to 1.0 to turn it off and watch it bleed.
MAX_ENTRY_PRICE = 0.80

# 📏 THE BASIS, AND IT IS THE BIGGEST SOURCE OF ERROR IN THIS WHOLE FILE.
#
# Polymarket settles on a CHAINLINK price. Everything here is measured on
# BINANCE. Those two feeds do not agree, and on a five minute window the gap
# is large enough to flip the answer.
#
# MEASURED on 14 of Moon Dev's own resolved windows, Binance TWAP against what
# Polymarket actually paid:
#
#     margin from strike     agreed with Polymarket
#     under $22              3 of 7      <- worse than a coin flip
#     $22 to $66             2 of 2
#     over $66               5 of 5      <- never wrong
#
#   Every single miss happened under $60. The worst was a $58.37 margin that
#   settled the other way.
#
# So a TWAP sitting $11 above the strike is NOT an 11 dollar cushion, it is a
# coin flip wearing one. Before this existed the model read that as P(Up)=0.997
# and all three brains bought it at 0.74. It lost. The book had it at 0.675 and
# the book was right.
#
# The number below is the standard deviation of that feed disagreement in
# dollars. It gets added to the market's own uncertainty IN QUADRATURE, which
# is the correct way to combine two independent errors. Set it to 0 to see the
# old overconfident model and watch it pay 0.74 for coin flips.
#
# 🚨 IT IS AN ESTIMATE OFF 14 WINDOWS, NOT A MEASUREMENT. Re-fit it once the
#    consensus log has a few hundred rows — that is exactly what the
#    twap_minus_strike and resolution columns are in there for.
BASIS_USD = 40.0

# ─── 🌙 MOON DEV - PLUMBING (you should not need to touch anything below) ───
BINANCE = "https://api.binance.com/api/v3"
BINANCE_SYMBOL = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT"}
MOONDEV_POSITIONS = "https://api.moondev.com/api/positions.json"
POSITIONS_MAX_AGE_SEC = 1800      # 🐋 a snapshot older than 30 min is not news
DATA_DIR = os.path.join(HERE, "data", "ai_5min")

ROUNDS_HEADER = [
    "round_ts", "slug", "brain", "model", "side", "p_up", "confidence", "why",
    "strike", "spot", "cushion_usd", "secs_left", "p_up_model", "book_p_up",
    "book_resid", "up_ask", "down_ask", "liq_long_usd", "liq_short_usd",
    "traded", "entry_price", "shares", "usd_risked", "resolution", "won", "pnl",
    "latency_ms", "cost_usd", "skip_reason"]

# 🔔 SOUND. Every one of these already exists in Moon Dev's shared sounds folder
#    except the two voice lines, which are made once by make_voice_line.py (the
#    README has the exact commands). play_sound never raises on a missing file,
#    so a bot with no voice lines yet still runs, it is just quieter.
ROUND_SOUND = SOUNDS + "ai_round_ballad_ding.wav"       # 🔔 new window is open
UP_SOUND = SOUNDS + "up_ballad.wav"                     # 🗣️ "up"
DOWN_SOUND = SOUNDS + "down_ballad.wav"                 # 🗣️ "down"
DENIED_SOUND = SOUNDS + "token_denied_fable_1.6x.wav"   # 🗣️ brain sat it out
HUNT_SOUND = SOUNDS + "hunting_entry_fable_1.6x.wav"    # 🗣️ order is going out

NB = " "        # 🌙 glue: a space that wrap() will not break on

# 📋 THE PINNED RECORD LINE, the second row of the sticky bar.
#
# 🚨 DEFINED HERE, AT MODULE LEVEL, ON PURPOSE. It used to spring into
#    existence the first time set_status() ran, which worked only because
#    ai_5min_core.run() happens to call that before it ever paints. Any other
#    caller — the consensus bot, for one — reached pin() first and got a
#    NameError mid-round. A global that only exists if you called the right
#    function first is a trap, so it starts empty and always exists.
_STATUS = ""

# 🔇 A QUIET SWITCH. Set AI5_SILENT=1 in the environment to run a bot with no
#    voice lines or chimes at all, which is what you want when something else
#    is doing the talking or you are recording.
SILENT = os.getenv("AI5_SILENT") == "1"

def chime(path):
    """🌙 Moon Dev - play_sound, unless this process was told to keep quiet."""
    if not SILENT:
        play_sound(path)

# ─── 🌙 MOON DEV - HOW THE FEED READS ───────────────────────────────────────
# You stream this terminal, and the stream window is TINY, about 32 columns at a
# font size that reads on video. Nothing here assumes 80.

def tag(side):
    """🌙 Moon Dev - the one colored arrow used everywhere. Green up, red down."""
    if side == "Up":
        return f"{GREEN}{BOLD}▲{NB}UP{OFF}"
    if side == "Down":
        return f"{RED}{BOLD}▼{NB}DOWN{OFF}"
    return f"{DIM}—{NB}NOTHING{OFF}"

def rule(color=CYAN):
    out(f"{color}{'═' * width()}{OFF}")

# 🧵 THREE BRAINS ANSWER AT ONCE NOW, so three threads can reach this at the
#    same moment. out() moves the cursor around to redraw the pinned status
#    bar, and two threads doing that together leaves the terminal in shreds.
#    One lock, held only for the drawing, costs nothing and keeps the screen
#    readable while all three are thinking.
_PRINT_LOCK = threading.RLock()

def row(text=""):
    """🌙 Moon Dev - a detail line, wrapped, giving up its indent when the
    window cannot afford one. Safe to call from several threads."""
    with _PRINT_LOCK:
        if not text:
            out()
            return
        lead = " " if narrow() else " " * 4
        for line in wrap(text, lead, lead + "  "):
            out(line)

def set_status(record, pending):
    """🌙 Moon Dev - refresh the pinned record line.

    `pending` are the rounds Polymarket has not graded yet. Showing that count
    is the honest part: a score of 2/4 means something different when three
    more results are still in the post, and without this you cannot tell."""
    global _STATUS
    bits = [record.line()]
    if pending:
        waiting = sum(1 for p in pending if p.get("provisional"))
        bits.append(f"{DIM}{len(pending)}{NB}settling{OFF}"
                    + (f" {YELLOW}{waiting}{NB}known{OFF}" if waiting else ""))
    _STATUS = "  ".join(bits)

def pin(brain, ts, phase, secs, extra=""):
    """🌙 Moon Dev - THE STICKY BOTTOM LINE. Everything scrolls past above it,
    this never moves, so a glance at the screen tells you where the round is.

    Two lines now: the clock on top, the running record underneath."""
    if narrow():
        sticky(f"{CYAN}{BOLD}{brain.EMOJI}{when(ts)}{OFF} {phase} "
               f"{BOLD}{clock(secs)}{OFF}" + (f"  {extra}" if extra else ""),
               _STATUS)
        return
    sticky(f"{CYAN}{BOLD}{brain.EMOJI} {brain.NAME} {when(ts)} {ASSET}{OFF} │ "
           f"{phase} {clock(secs)}" + (f" │ {extra}" if extra else ""), _STATUS)

# ─── 🌙 MOON DEV - THE FACTS ────────────────────────────────────────────────
# Real data or no trade. Every fetch below returns None on failure and a None
# anywhere kills the round, logged as a skip. A bot that guesses when the feed
# is down is a bot that teaches you nothing.

def _get(url, **kw):
    """🌙 Moon Dev - one GET. Returns the parsed body or None, never raises."""
    try:
        r = requests.get(url, timeout=kw.pop("timeout", 10), **kw)
        return r.json() if r.status_code == 200 else None
    except (requests.exceptions.RequestException, ValueError):
        return None

def klines(interval, limit, start_ms=None):
    """🌙 Moon Dev - Binance candles. [open_ms, o, h, l, c, v, ...]"""
    params = {"symbol": BINANCE_SYMBOL[ASSET], "interval": interval, "limit": limit}
    if start_ms is not None:
        params["startTime"] = start_ms
    d = _get(f"{BINANCE}/klines", params=params)
    return d if isinstance(d, list) and d else None

def spot_now():
    """🌙 Moon Dev - last traded price."""
    d = _get(f"{BINANCE}/ticker/price", params={"symbol": BINANCE_SYMBOL[ASSET]})
    return float(d["price"]) if d and "price" in d else None

def strike_for(window_ts):
    """🌙 Moon Dev - THE NUMBER POLYMARKET SETTLES AGAINST.

    The 5-minute market resolves Up when the close beats the OPEN of the window.
    That open is the Binance 1-minute bar that starts at the top of the window.
    Polymarket's own crypto-price endpoint is broken, so we read the bar itself
    and we check its timestamp matches — a bar for the wrong minute would put
    every cushion in the dataset off by a whole candle."""
    k = klines("1m", 1, start_ms=window_ts * 1000)
    if not k or int(k[0][0]) // 1000 != window_ts:
        return None
    return float(k[0][1])

def twap_so_far(window_ts):
    """🌙 Moon Dev - the TIME-WEIGHTED AVERAGE PRICE so far in this window, and
    how many seconds of it have run.

    🚨 THIS IS WHAT THE MARKET ACTUALLY SETTLES ON, and getting it wrong is the
       most expensive mistake in this whole file. Polymarket's own resolution
       text says it plainly:

         "resolve to Up if the TIME-WEIGHTED AVERAGE PRICE (TWAP) of Bitcoin,
          generated by Chainlink, of the time range specified in the title is
          GREATER THAN OR EQUAL TO the price at the beginning of that range."

       Not the closing price. The AVERAGE across the whole five minutes. Tested
       on Moon Dev's own resolved rounds, TWAP-vs-open called 6 of 7 correctly
       while close-vs-open managed 4 of 7, which is a coin flip.

    One-second candles, so the average is a real average and not five bars
    pretending to be one. Returns (twap, seconds_elapsed, last_price)."""
    now = min(time.time(), window_ts + MARKET_DURATION)
    elapsed = int(now - window_ts)
    if elapsed < 5:
        return (None, elapsed, None)
    rows = klines("1s", min(1000, elapsed + 5), start_ms=window_ts * 1000)
    if not rows:
        return (None, elapsed, None)
    px = [float(b[4]) for b in rows
          if window_ts * 1000 <= int(b[0]) < (window_ts + MARKET_DURATION) * 1000]
    if not px:
        return (None, elapsed, None)
    return (sum(px) / len(px), len(px), px[-1])

def near_liq():
    """🌙 Moon Dev - BTC positions sitting closest to liquidation, from the Moon
    Dev API. Top 50 per side across all coins, min $75k, so we filter to ours.

    Long liq prices sit BELOW spot, short liq prices sit ABOVE. Whichever pool
    is bigger is the bigger stack of forced market orders waiting to fire.

    Returns None when the feed is down OR when the snapshot is stale — the
    refresh is irregular and a 40-minute-old picture of who is about to blow up
    is not a picture of now."""
    d = _get(MOONDEV_POSITIONS, headers={"X-API-Key": os.getenv("MOONDEV_API_KEY", "")})
    if not isinstance(d, dict) or "longs" not in d:
        return None
    try:
        age = time.time() - datetime.fromisoformat(d["updated_at"]).timestamp()
    except (KeyError, ValueError, TypeError):
        return None
    if age > POSITIONS_MAX_AGE_SEC:
        return None
    keep = lambda rows: [r for r in rows if r.get("coin") == ASSET]
    return {"age_sec": round(age), "longs": keep(d.get("longs") or []),
            "shorts": keep(d.get("shorts") or [])}

def norm_cdf(x):
    """🌙 Moon Dev - Phi. The odds a normal draw lands under x."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def implied_p_up(up_bid, up_ask, down_bid, down_ask):
    """🌙 Moon Dev - what the BOOK thinks P(Up) is, using both sides of it.

    Up and Down are the same dollar split two ways, so a Down bid of 0.99 is
    somebody offering to sell Up at 0.01. Late in a window one side of one token
    goes empty all the time, and reading only the Up token there gives you None
    on a book that is actually quoting perfectly well through Down.

    So: build the best Up bid and the best Up ask out of BOTH tokens, then take
    the middle of whatever survives. None only when the book is genuinely empty."""
    bids = [p for p in (up_bid, (1 - down_ask) if down_ask else None) if p]
    asks = [p for p in (up_ask, (1 - down_bid) if down_bid else None) if p]
    best_bid = max(bids) if bids else None
    best_ask = min(asks) if asks else None
    if best_bid and best_ask:
        return (best_bid + best_ask) / 2
    return best_bid or best_ask

def liq_side(rows, spot):
    """🌙 Moon Dev - one side of the liquidation book, already added up.

    Every sum here is done in PYTHON. The brain is asked which pool matters,
    never asked to add the pools."""
    total = sum(float(r.get("value") or 0) for r in rows)
    near = [r for r in rows if float(r.get("distance_pct") or 99) <= 1.0]
    dists = [float(r.get("distance_pct") or 99) for r in rows]
    return {
        "positions": len(rows),
        "total_value_usd": round(total),
        "value_within_1pct_usd": round(sum(float(r.get("value") or 0) for r in near)),
        "positions_within_1pct": len(near),
        "closest_distance_pct": round(min(dists), 3) if dists else None,
        "biggest_position_usd": round(max((float(r.get("value") or 0) for r in rows),
                                          default=0)),
    }

def gather(market):
    """🌙 Moon Dev - THE FACT PACK. Every number the brain gets, computed here.

    Returns the pack, or None when any feed is down. There is no half pack and
    there is no filled-in gap: a missing feed is a skipped round, on purpose."""
    ts = market["ts"]
    strike = strike_for(ts)
    spot = spot_now()
    bars = klines("5m", int(BAR_HOURS * 12))
    liq = near_liq()
    if strike is None or spot is None or bars is None:
        return None

    closes = [float(b[4]) for b in bars]
    highs = [float(b[2]) for b in bars]
    lows = [float(b[3]) for b in bars]
    rets = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]

    # 📏 TWO VOLS, not one. The 24-hour number is the regime, the 1-hour number
    #    is right now, and in a 5-minute market they disagree constantly. Handing
    #    the brain both and letting it judge beats us picking one in advance.
    sig_24h = statistics.pstdev(rets) if len(rets) > 2 else 0.0
    sig_1h = statistics.pstdev(rets[-12:]) if len(rets) > 13 else sig_24h
    per_sec = lambda s: s / math.sqrt(MARKET_DURATION)   # 5-min bar -> 1 second

    left = max(1.0, ts + MARKET_DURATION - time.time())
    done = MARKET_DURATION - left               # seconds of the window already run
    cushion = spot - strike                     # spot vs strike, NOT the settle rule
    twap, ticks, last = twap_so_far(ts)
    if twap is None:                            # too early in the window to average
        twap, ticks = spot, 0

    # 🧮 FAIR VALUE FOR UP, AND IT IS A TWAP BARRIER, NOT A TERMINAL ONE.
    #
    #    The market settles on the AVERAGE price across the window, not the
    #    closing price, so pricing it like a terminal bet is simply the wrong
    #    model. Two things change, and they pull in opposite directions:
    #
    #    1. THE PART ALREADY RUN IS LOCKED IN. Whatever the average has been so
    #       far is a fact now, not a random variable. With `done` seconds gone,
    #       that fraction of the answer is already settled.
    #    2. AN AVERAGE WANDERS LESS THAN AN ENDPOINT. The integral of a random
    #       walk over the remaining time has variance sigma^2 * (left^3)/3,
    #       so as a share of the window the standard deviation carries a
    #       1/sqrt(3) against the terminal case. The average is STICKIER than
    #       the close, which is exactly why a market that looks like a coin
    #       flip on spot can be well decided on TWAP.
    #
    #    expected final TWAP = (done * twap_so_far + left * spot) / T
    #    sd of final TWAP    = sigma * spot * sqrt(left^3 / 3) / T
    def fair(sig):
        if sig <= 0:
            return 0.5
        mean = (done * twap + left * spot) / MARKET_DURATION
        market_sd = per_sec(sig) * spot * math.sqrt(left ** 3 / 3.0) / MARKET_DURATION
        # 📏 TWO INDEPENDENT UNCERTAINTIES, COMBINED IN QUADRATURE. One is where
        #    the price goes from here. The other is that we are reading a
        #    different price feed than the one that pays out. Late in a window
        #    the first goes to nearly zero and the SECOND IS ALL THAT IS LEFT,
        #    which is exactly when the old model was most sure and most wrong.
        sd = math.sqrt(market_sd ** 2 + BASIS_USD ** 2)
        # 🌙 ties resolve UP ("greater than or equal to"), so the strike itself
        #    is a win. At a zero cushion that is worth exactly nothing in a
        #    continuous model, but the rule is the rule and it is written here
        #    so nobody later assumes it was ">".
        return norm_cdf((mean - strike) / sd) if sd > 0 else (
            1.0 if mean >= strike else 0.0)
    p_up_24h, p_up_1h = fair(sig_24h), fair(sig_1h)
    twap_edge = twap - strike

    up_bid, up_ask = book(market["tokens"]["Up"])
    down_bid, down_ask = book(market["tokens"]["Down"])
    book_p_up = implied_p_up(up_bid, up_ask, down_bid, down_ask)

    pct = lambda a, b: round((a / b - 1) * 100, 3)
    hi, lo = max(highs), min(lows)

    return {
        "ts": ts,
        "market": {
            "slug": market["slug"],
            "asset": ASSET,
            "window_opened": when(ts, secs=True),
            "window_length_sec": MARKET_DURATION,
            "seconds_left_in_window": round(left),
            "resolves": "Up if the price finishes above the strike, Down if not",
        },
        "price": {
            "HOW_THIS_SETTLES": (
                "Up if the TIME-WEIGHTED AVERAGE price across the whole 5 "
                "minutes is GREATER THAN OR EQUAL TO the strike. NOT the "
                "closing price. An average, so early minutes count as much as "
                "late ones and a spike at the end barely moves it."),
            "strike_window_open": round(strike, 2),
            "spot_now": round(spot, 2),
            "twap_so_far": round(twap, 2),
            "twap_minus_strike_usd": round(twap_edge, 2),
            "twap_is_above_strike": twap_edge >= 0,
            "seconds_of_twap_locked_in": round(done),
            "twap_samples": ticks,
            "cushion_usd": round(cushion, 2),
            "cushion_note": ("cushion is spot vs strike. It is NOT the settle "
                             "condition — twap_minus_strike_usd is. Spot can be "
                             "below the strike while the average is above it."),
            "cushion_pct": round(cushion / strike * 100, 4),
            "already_above_strike": cushion > 0,
            "change_last_5m_pct": pct(closes[-1], closes[-2]) if len(closes) > 1 else 0,
            "change_last_15m_pct": pct(closes[-1], closes[-4]) if len(closes) > 3 else 0,
            "change_last_1h_pct": pct(closes[-1], closes[-13]) if len(closes) > 12 else 0,
            "change_last_4h_pct": pct(closes[-1], closes[-49]) if len(closes) > 48 else 0,
            "change_last_24h_pct": pct(closes[-1], closes[0]),
            "high_24h": round(hi, 2),
            "low_24h": round(lo, 2),
            "where_in_24h_range_0_to_1": round((spot - lo) / (hi - lo), 3) if hi > lo else 0.5,
            "green_bars_of_last_12": sum(float(b[4]) > float(b[1]) for b in bars[-12:]),
        },
        "volatility": {
            "stdev_of_5m_moves_24h_pct": round(sig_24h * 100, 4),
            "stdev_of_5m_moves_1h_pct": round(sig_1h * 100, 4),
            "typical_5m_move_usd_24h": round(strike * sig_24h, 2),
            "typical_5m_move_usd_1h": round(strike * sig_1h, 2),
            "vol_right_now_vs_24h": ("higher" if sig_1h > sig_24h * 1.25 else
                                     "lower" if sig_1h < sig_24h * 0.75 else "similar"),
        },
        "fair_value": {
            "p_up_using_24h_vol": round(p_up_24h, 4),
            "p_up_using_1h_vol": round(p_up_1h, 4),
            "what_it_models": (
                "P(final TWAP >= strike), the real settle condition. It blends "
                "the average ALREADY LOCKED IN with a random walk over the "
                "seconds left, AND with the gap between the price feed we read "
                "and the one Polymarket pays on."),
            "feed_basis_usd": BASIS_USD,
            "basis_warning": (
                f"Polymarket settles on CHAINLINK and these numbers are "
                f"BINANCE. That gap is worth roughly ${BASIS_USD:.0f} on a "
                f"5-minute average. IT IS ALREADY PRICED INTO THE P(Up) ABOVE "
                f"— it is the reason that number sits nearer 0.5 than a naive "
                f"reading of the TWAP would give you. So do NOT discount for "
                f"it a second time. The probability above is the honest one "
                f"after the feed risk: compare it to what the side costs and "
                f"decide."),
            "note": ("A random-walk model, nothing more. It does not know about "
                     "trend, news or the order book, and Polymarket settles on "
                     "CHAINLINK while these numbers come from Binance, so a "
                     "margin of a few dollars is inside the noise between the "
                     "two feeds."),
        },
        "book": {
            "up_bid": up_bid, "up_ask": up_ask,
            "down_bid": down_bid, "down_ask": down_ask,
            "market_implied_p_up": round(book_p_up, 4) if book_p_up else None,
            "book_minus_model_p_up": (round(book_p_up - p_up_1h, 4)
                                      if book_p_up else None),
            "note": ("book_minus_model_p_up above zero means the book thinks Up is "
                     "likelier than the model does. Moon Dev's fleet testing found "
                     "this book is EFFICIENT most of the time."),
        },
        "liquidations": ({
            "what_this_is": ("Hyperliquid BTC positions closest to getting force "
                             "closed, min $75k each. Longs blow up BELOW spot and "
                             "sell into it. Shorts blow up ABOVE spot and buy into "
                             "it. The bigger pool is the bigger pile of forced "
                             "orders waiting to fire."),
            "snapshot_age_sec": liq["age_sec"],
            "longs_below_spot": liq_side(liq["longs"], spot),
            "shorts_above_spot": liq_side(liq["shorts"], spot),
        } if liq else {"unavailable": "the feed was down or the snapshot was stale"}),
        # 📈 ALL 288 BARS, as the percent each one moved, oldest first. A percent
        #    is a fact the model can read; four raw OHLC prices is arithmetic we
        #    would be asking it to do. The last entry is the bar just before this
        #    window opened.
        "bars_5m_pct_change_oldest_first": [pct(float(b[4]), float(b[1])) for b in bars],
        "bars_5m_closes_oldest_first": [round(c, 1) for c in closes],
    }

def brief(pack, record):
    """🌙 Moon Dev - the pack as plain English, for the models that read English.

    Jev takes the pack as a dict and never sees this. Astra and Fable see this.
    Same facts either way, so the three bots are judged on judgement, not on who
    got a nicer prompt."""
    p, v, f, b = pack["price"], pack["volatility"], pack["fair_value"], pack["book"]
    m = pack["market"]
    lines = [
        f"MARKET: {m['slug']}",
        "HOW IT SETTLES: UP if the TIME-WEIGHTED AVERAGE price across the whole "
        "5 minutes is GREATER THAN OR EQUAL TO the strike. It is NOT the closing "
        "price. An average, so the early minutes count as much as the late ones "
        "and a spike right at the end barely moves it.",
        f"The window opened at {m['window_opened']} and has "
        f"{m['seconds_left_in_window']} seconds left.",
        "",
        "PRICE",
        f"  strike (the window open)   {p['strike_window_open']:,}",
        f"  TWAP so far                {p['twap_so_far']:,} "
        f"({p['twap_minus_strike_usd']:+,.2f} vs strike, "
        f"{'ABOVE' if p['twap_is_above_strike'] else 'BELOW'}) "
        f"<-- THIS IS WHAT SETTLES THE MARKET",
        f"  {p['seconds_of_twap_locked_in']}s of that average is already locked "
        f"in and cannot change",
        f"  spot right now             {p['spot_now']:,} "
        f"({p['cushion_usd']:+,.2f} vs strike)",
        "  note: spot can sit below the strike while the AVERAGE is above it. "
        "Trade the average.",
        f"  moves      5m {p['change_last_5m_pct']:+.3f}%   "
        f"15m {p['change_last_15m_pct']:+.3f}%   1h {p['change_last_1h_pct']:+.3f}%   "
        f"4h {p['change_last_4h_pct']:+.3f}%   24h {p['change_last_24h_pct']:+.3f}%",
        f"  24h range {p['low_24h']:,} to {p['high_24h']:,}, spot sits "
        f"{p['where_in_24h_range_0_to_1']:.2f} of the way up it",
        f"  {p['green_bars_of_last_12']} of the last 12 five-minute bars closed green",
        "",
        "VOLATILITY (already computed, do not recompute it)",
        f"  a typical 5-minute move is ${v['typical_5m_move_usd_24h']:,} on 24h vol, "
        f"${v['typical_5m_move_usd_1h']:,} on the last hour",
        f"  volatility right now is {v['vol_right_now_vs_24h']} to the 24h average",
        "",
        "FAIR VALUE FROM A RANDOM WALK (already computed)",
        f"  P(final TWAP >= strike) = {f['p_up_using_1h_vol']:.3f} on recent "
        f"vol, {f['p_up_using_24h_vol']:.3f} on 24h vol",
        f"  {f['what_it_models']}",
        f"  ⚠️ {f['basis_warning']}",
        f"  {f['note']}",
        "",
        "THE ORDER BOOK",
        f"  Up   bid {b['up_bid']}  ask {b['up_ask']}",
        f"  Down bid {b['down_bid']}  ask {b['down_ask']}",
        (f"  the book implies P(Up) = {b['market_implied_p_up']}, which is "
         f"{b['book_minus_model_p_up']:+.3f} away from the model"
         if b["market_implied_p_up"] is not None else
         "  the book is empty right now, so it implies nothing"),
        f"  {b['note']}",
        "",
    ]

    liq = pack["liquidations"]
    if "unavailable" in liq:
        lines += ["LIQUIDATION FUEL", "  feed unavailable this round", ""]
    else:
        lo, sh = liq["longs_below_spot"], liq["shorts_above_spot"]
        lines += [
            "LIQUIDATION FUEL ON HYPERLIQUID (everyone else's positions)",
            f"  {liq['what_this_is']}",
            f"  snapshot is {liq['snapshot_age_sec']}s old",
            f"  LONGS below spot   {lo['positions']} positions, "
            f"${lo['total_value_usd']:,} total, ${lo['value_within_1pct_usd']:,} "
            f"within 1%, closest is {lo['closest_distance_pct']}% away, "
            f"biggest is ${lo['biggest_position_usd']:,}",
            f"  SHORTS above spot  {sh['positions']} positions, "
            f"${sh['total_value_usd']:,} total, ${sh['value_within_1pct_usd']:,} "
            f"within 1%, closest is {sh['closest_distance_pct']}% away, "
            f"biggest is ${sh['biggest_position_usd']:,}",
            "",
        ]

    lines += [
        f"YOUR OWN RECORD SO FAR: {record.summary()}",
        "",
        f"THE LAST {BAR_HOURS} HOURS OF 5-MINUTE BARS, oldest first, as the "
        f"percent each bar moved. The last one is the bar right before this "
        f"window opened.",
        "  " + ", ".join(f"{x:+.3f}" for x in pack["bars_5m_pct_change_oldest_first"]),
        "",
        f"Call this window. UP buys the Up side at {b['up_ask']}, DOWN buys the "
        f"Down side at {b['down_ask']}, NOTHING sits it out and costs nothing.",
    ]
    return "\n".join(lines)

CHARS_PER_TOKEN_PROSE = 2.5
CHARS_PER_TOKEN_JSON = 1.15

def tokens_in(text, chars_per_token=CHARS_PER_TOKEN_PROSE):
    return int(len(text) / chars_per_token) + 1

def _trim_to(pack, cap, render, chars_per_token=CHARS_PER_TOKEN_PROSE):
    dropped, text = 0, render()
    size = lambda t: tokens_in(t, chars_per_token)
    while size(text) > cap and len(pack["bars_5m_pct_change_oldest_first"]) > 24:
        for key in ("bars_5m_pct_change_oldest_first", "bars_5m_closes_oldest_first"):
            pack[key] = pack[key][12:]
        dropped += 12
        text = render()
    if dropped:
        say(f"✂️  Trimmed {dropped} old bars ({dropped // 12}h) to fit "
            f"{cap:,} tokens. {len(pack['bars_5m_pct_change_oldest_first'])} "
            f"bars sent.", YELLOW)
    pack["bars_dropped_to_fit_context"] = dropped
    return text

def fit_brief(pack, record, cap):
    text = _trim_to(pack, cap, lambda: brief(pack, record))
    return text, tokens_in(text)

def state_of(pack, record):
    s = {k: v for k, v in pack.items() if k != "ts"}
    s["your_own_record"] = record.summary()
    return s

def fit_state(pack, record, cap):
    render = lambda: json.dumps(state_of(pack, record))
    text = _trim_to(pack, cap, render, CHARS_PER_TOKEN_JSON)
    return state_of(pack, record), tokens_in(text, CHARS_PER_TOKEN_JSON)

class Record:
    def __init__(self, brain):
        self.path = os.path.join(DATA_DIR, f"{brain.KEY}_rounds.csv")
        self.calls = self.passes = self.traded = self.wins = 0
        self.trade_wins = 0
        self.pnl = self.risked = self.need_num = 0.0
        self.recent = []
        self.load()

    def _add(self, side, won, traded, pnl, entry=0.0, risked=0.0):
        if side:
            self.calls += 1
            self.wins += bool(won)
        else:
            self.passes += 1
        if traded:
            self.traded += 1
            self.trade_wins += bool(won)
            self.pnl += pnl
            self.risked += risked
            self.need_num += entry * risked
        self.recent = (self.recent + [(side, won)])[-10:]

    def load(self):
        if not os.path.exists(self.path):
            return
        with open(self.path) as f:
            for r in csv.DictReader(f):
                if not r.get("resolution"):
                    continue
                side = r.get("side") or None
                self._add(side, side == r["resolution"] if side else None,
                          r.get("traded") == "True", float(r.get("pnl") or 0),
                          float(r.get("entry_price") or 0),
                          float(r.get("usd_risked") or 0))

    def grade(self, side, winner, traded, pnl, entry=0.0, risked=0.0):
        self._add(side, (side == winner) if side else None, traded, pnl,
                  entry, risked)

    def breakeven(self):
        if not self.risked or not self.traded:
            return (None, None)
        return (self.need_num / self.risked, self.trade_wins / self.traded)

    def _streak(self):
        return "".join("W" if ok else ("L" if ok is False else ".")
                       for _, ok in self.recent)

    def summary(self):
        if not self.calls and not self.passes:
            return "no graded rounds yet, this is the first one"
        rate = (f"{self.wins / self.calls * 100:.0f}%" if self.calls else "n/a")
        return (f"{self.calls} directional calls, {self.wins} right ({rate}), "
                f"{self.passes} windows sat out, {self.traded} trades for "
                f"${self.pnl:+.2f}, last 10 rounds {self._streak()}")

    def line(self):
        if not self.calls and not self.passes:
            return f"{DIM}no graded rounds yet{OFF}"
        rate = (f"{self.wins / self.calls * 100:.0f}%" if self.calls else "n/a")
        color = GREEN if self.pnl >= 0 else RED
        last = "".join(f"{GREEN}W{OFF}" if ok else
                       (f"{RED}L{OFF}" if ok is False else f"{DIM}.{OFF}")
                       for _, ok in self.recent)
        roi = f" {color}{self.pnl / self.risked:+.0%}{OFF}" if self.risked else ""
        need, actual = self.breakeven()
        gap = ("" if need is None else
               f"  {DIM}need{NB}{need:.0%}{OFF}"
               f"{GREEN if actual >= need else RED}{BOLD}"
               f"{NB}{actual - need:+.0%}{OFF}")
        return (f"📋 {BOLD}{self.wins}/{self.calls}{OFF} right ({rate})  "
                f"{DIM}{self.passes} passed{OFF}  "
                f"{color}{BOLD}${self.pnl:+.2f}{OFF}{roi}{gap}  {last}")

    def trades_logged(self):
        return self.traded

    def today_pnl(self):
        if not os.path.exists(self.path):
            return 0.0
        start = datetime.now().replace(hour=0, minute=0, second=0,
                                       microsecond=0).timestamp()
        total = 0.0
        with open(self.path) as f:
            for r in csv.DictReader(f):
                if r.get("resolution") and float(r.get("round_ts") or 0) >= start:
                    total += float(r.get("pnl") or 0)
        return total

def _open_path(brain):
    return os.path.join(DATA_DIR, f"{brain.KEY}_open.json")

def open_load(brain):
    try:
        with open(_open_path(brain)) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}

def _open_save(brain, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = _open_path(brain) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, _open_path(brain))

def open_add(brain, pending):
    data = open_load(brain)
    pk = pending.get("pack") or {}
    data[pending["slug"]] = {
        "ts": pending["ts"], "slug": pending["slug"], "side": pending["side"],
        "price": pending["price"], "shares": pending["shares"],
        "p_up": pending["p_up"], "confidence": pending["confidence"],
        "why": pending["why"], "detail": pending["detail"],
        "traded": True, "skip_reason": pending["skip_reason"],
        "pack": {k: pk[k] for k in
                 ("market", "price", "fair_value", "book", "liquidations")
                 if k in pk} or None,
    }
    _open_save(brain, data)

def open_drop(brain, slug):
    data = open_load(brain)
    if data.pop(slug, None) is not None:
        _open_save(brain, data)

def append_csv(path, header, row):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerow(row)

def fill_of(order_id):
    try:
        d = client().get_order(str(order_id)) or {}
    except Exception:
        return None
    for key in ("size_matched", "sizeMatched", "matched_size", "filled_size"):
        if key in d:
            shares = float(d.get(key) or 0)
            price = float(d.get("price") or d.get("avgPrice") or 0)
            return (shares, price)
    return None

def enter(token, side, ask, size):
    chime(HUNT_SOUND)
    try:
        r = place(token, "BUY", round(ask, 4), size, post_only=False)
    except Exception as e:
        say(f"❌  Could not place the order: {type(e).__name__}", RED)
        return {"skip_reason": f"order error {type(e).__name__}"}
    if not r.get("orderID"):
        say("❌  The exchange did not take that order.", RED)
        return {"skip_reason": "order rejected"}
    order_id = r.get("orderID")
    say("📤  Order sent. Watching for the fill.", GREEN)
    deadline = time.time() + FILL_WAIT_SEC
    while time.time() < deadline:
        got = fill_of(order_id)
        have, avg = got if got else position_in(token)
        if got and have > 0 and not avg:
            avg = ask
        if have > 0:
            chime(FILL_SOUND)
            say(f"✅  FILLED {have:.2f} {tag(side)} @{NB}{BOLD}{avg:.2f}{OFF}",
                GREEN + BOLD)
            return {"traded": True, "side": side, "price": avg, "shares": have}
        time.sleep(2)
    say(f"⚠️  Nothing filled in {FILL_WAIT_SEC}s. Cancelling so nothing rests "
        f"into the next window.", YELLOW)
    chime(CANCEL_SOUND)
    try:
        cancel_all_on(token)
    except Exception:
        say("❌  Could not confirm the cancel. Check the site.", RED)
    return {"side": side, "price": ask, "shares": size, "skip_reason": "no fill"}

def hold(brain, side, end, traded, ts, pending, record):
    state = (f"{tag(side)} ${USD_SIZE}" if traded
             else f"{DIM}flat,{NB}no{NB}trade{OFF}")
    next_beat, next_settle = 0.0, time.time() + 20
    while time.time() < end:
        if pending and time.time() > next_settle:
            next_settle = time.time() + 15
            pending[:] = [p for p in pending if not settle(brain, p, record)]
            set_status(record, pending)
        if time.time() > next_beat:
            next_beat = time.time() + 30
            row(f"⏱  holding {state}  {clock(end - time.time())} left")
        pin(brain, ts, f"{YELLOW}{phase_name('SETTLES IN', 'SETTLE')}{OFF}",
            end - time.time(), state)
        time.sleep(0.5)

def settle(brain, pending, record):
    winner = get_resolution(pending["slug"])
    if winner is None:
        if (not pending.get("provisional")
                and time.time() > pending["ts"] + MARKET_DURATION + 5):
            tw, _, _ = twap_so_far(pending["ts"])
            strike = (pending["pack"] or {}).get("price", {}).get("strike_window_open")
            if tw and strike:
                edge = tw - strike
                pending["provisional"] = "?" if abs(edge) < PROVISIONAL_MIN_EDGE_USD \
                    else ("Up" if edge >= 0 else "Down")
                if pending["provisional"] == "?":
                    say(f"⚡  {when(pending['ts'])} is TOO CLOSE to call: TWAP is "
                        f"{edge:+.2f} from the strike. Waiting for Polymarket.",
                        YELLOW)
                else:
                    side, p = pending["side"], pending["provisional"]
                    mark = ("" if not side else
                            f"  {GREEN}{BOLD}✅ WON{OFF}" if side == p else
                            f"  {RED}{BOLD}❌ LOST{OFF}")
                    say(f"⚡  {when(pending['ts'])} looks like {tag(p)}{mark}  "
                        f"{DIM}TWAP {edge:+.2f} vs strike — provisional, off "
                        f"Binance, not yet official{OFF}", BOLD)
        return False

    side, traded = pending["side"], pending["traded"]
    price, shares = pending["price"], pending["shares"]
    won = traded and side == winner
    pnl = (shares * (1 - price) if won else -shares * price) if traded else 0.0
    record.grade(side, winner, traded, pnl, price if traded else 0.0,
                 price * shares if traded else 0.0)

    d = pending["detail"]
    pk = pending["pack"]
    p = pk["price"] if pk else {}
    f = pk["fair_value"] if pk else {}
    b = pk["book"] if pk else {}
    liq = pk["liquidations"] if pk else {}
    blank_ = lambda d_, k: d_.get(k, "")
    append_csv(record.path, ROUNDS_HEADER, [
        pending["ts"], pending["slug"], brain.NAME, brain.MODEL, side or "",
        pending["p_up"], pending["confidence"], pending["why"],
        blank_(p, "strike_window_open"), blank_(p, "spot_now"),
        blank_(p, "cushion_usd"),
        pk["market"]["seconds_left_in_window"] if pk else "",
        blank_(f, "p_up_using_1h_vol"), blank_(b, "market_implied_p_up"),
        blank_(b, "book_minus_model_p_up"), blank_(b, "up_ask"),
        blank_(b, "down_ask"),
        liq.get("longs_below_spot", {}).get("total_value_usd", ""),
        liq.get("shorts_above_spot", {}).get("total_value_usd", ""),
        traded, f"{price:.4f}" if price else "", f"{shares:.2f}" if shares else "",
        f"{price * shares:.2f}" if traded else "", winner,
        (side == winner) if side else "", f"{pnl:.2f}" if traded else "",
        d.get("latency_ms", ""), d.get("cost_usd", ""), pending["skip_reason"]])

    open_drop(brain, pending["slug"])

    out()
    rule(GREEN if winner == "Up" else RED)
    called = (f"{brain.NAME} said {tag(side)}" if side
              else f"{brain.NAME} sat it out")
    mark = (f"{GREEN}{BOLD}✅ RIGHT{OFF}" if side == winner else
            f"{RED}{BOLD}❌ WRONG{OFF}") if side else f"{DIM}no call{OFF}"
    say(f"🏁  {when(pending['ts'])} SETTLED {tag(winner)}", BOLD)
    row(f"{called}  {mark}")
    if traded:
        risked = price * shares
        roi = pnl / risked if risked else 0.0
        row(f"{'✅ WON' if won else '❌ LOST'} ${risked:.2f} at risk @{price:.2f}  "
            f"{(GREEN if won else RED)}{BOLD}{pnl:+.2f}{NB}({roi:+.0%}){OFF}")
    row(record.line())
    rule(GREEN if winner == "Up" else RED)
    out()
    return True

def blank(ts, slug, reason):
    return {"ts": ts, "slug": slug, "side": None, "p_up": "", "confidence": "",
            "why": "", "traded": False, "price": 0.0, "shares": 0.0,
            "skip_reason": reason, "detail": {}, "pack": None}

def wait_until(brain, ts, target, phase):
    while time.time() < target:
        pin(brain, ts, phase, target - time.time())
        time.sleep(0.2)

def run_round(brain, market, record, pending_rounds):
    ts = market["ts"]
    end = ts + MARKET_DURATION

    out()
    rule()
    say(f"{brain.EMOJI}  ROUND {when(ts)} {ASSET} UP or DOWN", CYAN + BOLD)
    row(f"{brain.NAME} decides in {clock(max(0, ts + DECIDE_AT_SEC - time.time()))}, "
        f"${USD_SIZE} on its call, held to expiry.")
    row(record.line())
    if narrow():
        out(f"{DIM}🔗 polymarket.com/event/{OFF}")
        out(f"{DIM}   {market['slug']}{OFF}")
    else:
        out(f"{DIM}https://polymarket.com/event/{market['slug']}{OFF}")
    rule()
    chime(ROUND_SOUND)

    wait_until(brain, ts, ts + DECIDE_AT_SEC, f"{CYAN}{phase_name('GATHERING', 'DATA')}{OFF}")

    say("📡  Pulling the bars, the strike and everyone else's positions.", CYAN)
    pack = gather(market)
    if pack is None:
        say("⛔  A feed is down. Real data or no bet, so this round is skipped.",
            YELLOW + BOLD)
        return blank(ts, market["slug"], "feed down")

    p, b = pack["price"], pack["book"]
    tw = p["twap_minus_strike_usd"]
    row(f"🎯 strike {BOLD}{p['strike_window_open']:,}{OFF}  TWAP "
        f"{(GREEN if tw >= 0 else RED)}{BOLD}{tw:+,.2f}{OFF}"
        f"{DIM}({p['seconds_of_twap_locked_in']}s locked){OFF}  spot "
        f"{(GREEN if p['cushion_usd'] > 0 else RED)}{p['cushion_usd']:+,.2f}{OFF}")
    row(f"📖 book  up {b['up_ask']}  down {b['down_ask']}  "
        f"{DIM}model P(Up) {pack['fair_value']['p_up_using_1h_vol']:.2f}{OFF}")
    liq = pack["liquidations"]
    if "unavailable" not in liq:
        row(f"🐋 near-liq  {RED}longs ${liq['longs_below_spot']['total_value_usd']:,}{OFF}"
            f"  {GREEN}shorts ${liq['shorts_above_spot']['total_value_usd']:,}{OFF}"
            f"  {DIM}{liq['snapshot_age_sec']}s old{OFF}")

    say(f"{brain.EMOJI}  {brain.NAME} is deciding.", MAG + BOLD)
    pin(brain, ts, f"{MAG}{phase_name('THINKING', 'THINK')}{OFF}", end - time.time())
    side, p_up, confidence, why, detail = brain.decide(pack, record)

    pending = {"ts": ts, "slug": market["slug"], "side": side, "p_up": p_up,
               "confidence": confidence, "why": why, "traded": False,
               "price": 0.0, "shares": 0.0, "skip_reason": "", "detail": detail,
               "pack": pack}

    out()
    rule(MAG)
    say(f"{brain.EMOJI}  {brain.NAME} SAYS {tag(side)}", BOLD)
    row(why)
    if detail.get("latency_ms"):
        row(f"{DIM}{detail['latency_ms']:.0f}ms"
            + (f"  ${detail['cost_usd']:.6f}" if detail.get("cost_usd") else "")
            + f"  {brain.MODEL}{OFF}")
    rule(MAG)
    chime(UP_SOUND if side == "Up" else
               DOWN_SOUND if side == "Down" else DENIED_SOUND)

    if side is None:
        pending["skip_reason"] = "brain said nothing"
        hold(brain, None, end, False, ts, pending_rounds, record)
        return pending

    if time.time() > ts + ENTRY_CUTOFF_SEC:
        say(f"⛔  That answer took too long, only {clock(end - time.time())} left. "
            f"Logging the call, skipping the trade.", YELLOW)
        pending["skip_reason"] = "answer too late"
        hold(brain, side, end, False, ts, pending_rounds, record)
        return pending

    held = open_load(brain).get(market["slug"])
    if held and held.get("traded"):
        say(f"🛑  ALREADY IN THIS WINDOW from an earlier run: "
            f"{held['shares']:.2f} {tag(held['side'])} @{NB}"
            f"{BOLD}{held['price']:.2f}{OFF}. NOT buying again.", YELLOW + BOLD)
        row(f"{DIM}Adopting that position and holding it to expiry.{OFF}")
        pending.update(traded=True, side=held["side"], price=held["price"],
                       shares=held["shares"], skip_reason="adopted on restart")
        hold(brain, held["side"], end, True, ts, pending_rounds, record)
        return pending

    token = market["tokens"][side]
    _, ask = book(token)
    if ask is None:
        say(f"⛔  Nobody is offering {side}, so there is nothing to buy.", YELLOW)
        pending["skip_reason"] = "no ask"
        hold(brain, side, end, False, ts, pending_rounds, record)
        return pending
    if ask > MAX_ENTRY_PRICE:
        say(f"⛔  {side} is {ask:.2f}, over the {MAX_ENTRY_PRICE:.2f} ceiling. "
            f"Moon Dev's 484 fills above 0.80 all lost. Sitting out.", YELLOW)
        pending["skip_reason"] = f"ask {ask:.2f} over ceiling"
        hold(brain, side, end, False, ts, pending_rounds, record)
        return pending

    today = record.today_pnl()
    if today <= DAILY_STOP_USD:
        say(f"🛑  Daily stop hit: ${today:.2f} today. Logging the call, no trade.",
            RED + BOLD)
        pending["skip_reason"] = "daily stop"
        hold(brain, side, end, False, ts, pending_rounds, record)
        return pending

    size = shares_for(USD_SIZE, ask)
    out()
    say(f"💰  BUY {size:.2f} {tag(side)} @{NB}{BOLD}{ask:.2f}{OFF} "
        f"={NB}{BOLD}${ask * size:.2f}{OFF}", GREEN + BOLD)
    row(f"🎯 pays {BOLD}{(1 - ask) / ask:+.0%}{OFF} if right, "
        f"{RED}-100%{OFF} if wrong  →  needs to be right "
        f"{BOLD}{ask:.0%}{OFF} of the time to break even")
    if LIVE_TRADING:
        pending.update(**enter(token, side, ask, size))
        if pending["traded"]:
            open_add(brain, pending)
    else:
        say("📝  LIVE_TRADING is off, so no order was sent. Everything else "
            "is real.", YELLOW)
        pending.update(side=side, price=ask, shares=size, skip_reason="paper")

    hold(brain, side, end, pending["traded"], ts, pending_rounds, record)
    return pending

def drain(brain, pending, record):
    if not pending:
        return
    deadline = time.time() + SETTLE_PATIENCE_SEC
    say(f"⏳  Waiting on {len(pending)} round(s) to resolve. Polymarket takes a "
        f"few minutes. Not exiting until they are graded.", CYAN + BOLD)
    while pending and time.time() < deadline:
        pending[:] = [p for p in pending if not settle(brain, p, record)]
        set_status(record, pending)
        if not pending:
            break
        left = deadline - time.time()
        sticky(f"{CYAN}⏳ settling {len(pending)} round(s){OFF} │ "
               f"giving up in {clock(left)}")
        time.sleep(15)
    unstick()
    for p in pending:
        say(f"⚠️  {p['slug']} never resolved in time. It is NOT in the CSV, so "
            f"the count is short by one. Re-run the scoreboard later.", YELLOW)

def run(brain, trade_target=0, max_rounds=0):
    rule()
    say(f"{brain.EMOJI}  MOON DEV's {brain.NAME} 5-MINUTE BOT", CYAN + BOLD)
    row(f"{brain.TAGLINE}")
    row(f"Every {MARKET_DURATION // 60} minutes it calls the {ASSET} market: "
        f"{BOLD}UP, DOWN or NOTHING{OFF}.")
    row(f"${USD_SIZE} per trade, decides at {DECIDE_AT_SEC}s, holds to expiry, "
        f"never pays over {MAX_ENTRY_PRICE:.2f}.")
    row(f"{DIM}model {brain.MODEL}  ·  log {brain.KEY}_rounds.csv{OFF}")
    row(f"{DIM}about {brain.COST_PER_DAY} a day in model calls at 288 "
        f"windows{OFF}")
    rule()

    try:
        brain.check()
    except Exception as e:
        say(f"❌  {e}", RED + BOLD)
        return None

    if not LIVE_TRADING:
        say("📝  LIVE_TRADING is OFF. The data and the calls are real, the "
            "orders are not.", YELLOW + BOLD)

    record = Record(brain)
    row(record.line())
    set_status(record, [])

    already = record.trades_logged() + sum(
        1 for r in open_load(brain).values() if r.get("traded"))
    owed = max(0, trade_target - already) if trade_target else 0
    if trade_target:
        if already:
            say(f"🌉  {already} trade(s) already in {brain.NAME}'s log. "
                f"It owes {owed} more to reach {trade_target}.", CYAN + BOLD)
        else:
            say(f"🎯  Taking {trade_target} trades. Windows it sits out do not "
                f"count against that.", CYAN + BOLD)
        if not owed:
            say(f"✅  {brain.NAME} is already at {already} trades. Nothing to "
                f"do.", GREEN + BOLD)
            return {"brain": brain.NAME, "rounds": 0, "trades": 0,
                    "already": already, "hit_cap": False}

    try:
        this_window = get_market(window_now(), ASSET)
        known = set(open_load(brain))
        if this_window and this_window["slug"] not in known:
            for sd, tok in this_window["tokens"].items():
                have, avg = position_in(tok)
                if have > 0:
                    say(f"🚨  YOUR WALLET ALREADY HOLDS {have:.2f} {tag(sd)} "
                        f"@{NB}{BOLD}{avg:.2f}{OFF} in the CURRENT window, and "
                        f"no run of this bot recorded it.", RED + BOLD)
                    row("Left over from an older build or a process that was "
                        "killed. This bot will NOT add to it.")
                    row(f"{DIM}It settles on its own at expiry. From here every "
                        f"fill is recorded, so a restart can never double up "
                        f"again.{OFF}")
                    open_add(brain, {
                        "ts": this_window["ts"], "slug": this_window["slug"],
                        "side": sd, "price": avg, "shares": have, "p_up": "",
                        "confidence": "", "why": "adopted from wallet at startup",
                        "detail": {}, "traded": True,
                        "skip_reason": "adopted from wallet", "pack": None})
    except Exception as e:
        say(f"Could not check the wallet for open positions "
            f"({type(e).__name__}). Continuing.", YELLOW)

    try:
        say(f"💵  Your balance is ${balance():,.2f}.", CYAN)
    except Exception as e:
        say(f"Could not read your balance ({type(e).__name__}). Run "
            f"test_connection.py.", RED)
        return None

    pending = []
    for slug, rec in sorted(open_load(brain).items(),
                            key=lambda kv: kv[1].get("ts", 0)):
        rec.setdefault("detail", {})
        rec.setdefault("pack", None)
        pending.append(rec)
    if pending:
        say(f"🌉  Picking up {len(pending)} position(s) left open by the last "
            f"run. They will be graded, not lost.", CYAN + BOLD)
        for r in pending:
            row(f"{DIM}{when(r['ts'])}{OFF} {tag(r.get('side'))} "
                f"{r.get('shares', 0):.2f} @{r.get('price', 0):.2f}")

    last_ts, next_settle = None, 0.0
    played = trades = 0
    hit_cap = stopped = False
    try:
      while True:
          if pending and time.time() > next_settle:
              next_settle = time.time() + 15
              pending = [p for p in pending if not settle(brain, p, record)]
              set_status(record, pending)

          ts = window_now()
          if ts == last_ts:
              left = f"{trades}/{owed}{NB}trades" if owed else ""
              pin(brain, ts, f"{DIM}{phase_name('NEXT ROUND IN', 'NEXT')}{OFF}",
                  ts + MARKET_DURATION - time.time(), f"{DIM}{left}{OFF}")
              time.sleep(1)
              continue

          market = get_market(ts, ASSET)
          if not market:
              say(f"No {ASSET} market posted for this window yet. Waiting.", YELLOW)
              time.sleep(2)
              continue

          if time.time() > ts + ENTRY_CUTOFF_SEC:
              say("Joined this window too late to call it. Waiting for the next.",
                  YELLOW)
              last_ts = ts
              continue

          last_ts = ts
          for side in ("Up", "Down"):
              try:
                  market_meta(market["tokens"][side])
              except Exception:
                  pass
          result = run_round(brain, market, record, pending)
          pending.append(result)
          set_status(record, pending)
          played += 1
          if result["traded"]:
              trades += 1

          if owed:
              rate = f"{trades}/{played} windows" if played else ""
              say(f"📊  {brain.NAME}: {trades} of {owed} trades taken, "
                  f"{played} rounds played ({rate}).", CYAN + BOLD)
              if trades >= owed:
                  break
              if max_rounds and played >= max_rounds:
                  hit_cap = True
                  say(f"🛑  {brain.NAME} hit the {max_rounds} round cap with only "
                      f"{trades} trades. It is being very selective, and THAT IS "
                      f"THE RESULT — it is not a failure, it is the finding.",
                      YELLOW + BOLD)
                  break
    except KeyboardInterrupt:
        stopped = True
        unstick()
        say(f"⌨️  Ctrl+C. Grading the {len(pending)} round(s) already in "
            f"flight before stopping, so nothing you paid for is lost.",
            YELLOW + BOLD)

    drain(brain, pending, record)
    out()
    rule(MAG)
    say(f"🏁  {brain.NAME} {'STOPPED EARLY' if stopped else 'DONE'}: "
        f"{trades} trades in {played} rounds.", MAG + BOLD)
    if played:
        row(f"traded {trades / played:.0%} of the windows it saw")
    row(record.line())
    row(f"{DIM}log {record.path}{OFF}")
    rule(MAG)
    return {"brain": brain.NAME, "rounds": played, "trades": trades,
            "already": already, "hit_cap": hit_cap, "stopped": stopped}

def start(brain):
    target = 0
    if len(sys.argv) > 1:
        if not sys.argv[1].isdigit():
            say(f"'{sys.argv[1]}' is not a number of trades. Try: "
                f"python {os.path.basename(sys.argv[0])} 10", RED)
            return
        target = int(sys.argv[1])
    try:
        run(brain, target, MAX_ROUNDS_PER_BRAIN if target else 0)
    except KeyboardInterrupt:
        unstick()
        say("Stopped with Ctrl+C. If a position is open it settles on its own. 🌙",
            YELLOW)
    finally:
        unstick()
```
### openrouter_brain.py

3 of 8 — the two ways of talking to a model.

openrouter_brain.py

```python
"""
================================================================================
🌙 MOON DEV's OPENROUTER BRAINS: everything all three bots share
================================================================================
Jev, Astra and Fable ALL run through OpenRouter on the one OPENROUTER_API_KEY.
This file is what they share, so each bot file is short and a fourth model is
about a minute of work.

There are TWO brains in here, because OpenRouter has two different endpoints:

  🗣️ OpenRouterBrain  ->  /api/v1/chat/completions
     Astra and Fable. You send a prompt, you get a paragraph, you fish the
     answer out of it with a regex.

  ⚡ DecisionsBrain   ->  /api/alpha/decisions
     Jev. You send STATE plus TYPED QUESTIONS and you get typed VALUES back:
     a choice with calibrated probabilities, a 0-1 noul, a score. No prose at
     all, so there is nothing to parse and nothing to mis-parse.

🚨 JEV IS NOT ON THE CHAT MODEL LIST, and it is not supposed to be. Asking for
   it at /chat/completions returns, word for word:

     "typesafe/jev-1.13 is a decisions model and cannot be used with the
      chat/completions endpoint. Use the /api/alpha/decisions endpoint instead."

   That is the whole trick. It is on OpenRouter, it just lives somewhere else,
   and `GET /api/v1/models` will never show it to you.

HOW THE CHAT ANSWER COMES BACK
A model writes a paragraph and we have to find the decision inside it. Two
things that costs us, both handled below:

  🕳️ A reasoning model can burn its whole token budget thinking and hand back
     content of null. That is not a yes and it is not a no, it is a NOTHING,
     and it gets logged as one so a bad stretch is visible in the CSV instead
     of looking like a quiet afternoon of no opinions.

  🔤 The last valid keyword wins. A model that says "I considered DOWN but the
     cushion says UP" must not be read as DOWN, and reading the LAST one is the
     only rule that survives that sentence.

Built by Moon Dev 🌙
================================================================================
"""

import os
import re
import time

import requests

import ai_5min_core as core

OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"
DECISIONS = "https://openrouter.ai/api/alpha/decisions"

SYSTEM = """You are calling a 5-minute Bitcoin up-or-down market on Polymarket \
for Moon Dev. Real money follows your answer.

THE SETTLE RULE, AND MOST PEOPLE GET THIS WRONG. The market resolves UP if the \
TIME-WEIGHTED AVERAGE PRICE of BTC across the whole 5-minute window is GREATER \
THAN OR EQUAL TO the strike (the price at the start of the window). It is NOT \
the closing price. It is the AVERAGE. Three things follow from that:
- Minutes already elapsed are locked into the average and cannot be undone.
- A spike in the last thirty seconds barely moves a five-minute average.
- Spot can be below the strike while the average is still above it, and that \
market resolves UP.
Trade the average, not the last price. You buy one side at the ask shown and \
hold it to expiry. There is no exit.

EVERY NUMBER YOU NEED IS ALREADY COMPUTED FOR YOU. The returns, the volatility, \
the fair value and the liquidation totals were all worked out in Python before \
you saw them. Do not recompute anything and do not do arithmetic in your head. \
Your job is the judgement the arithmetic cannot make.

Three things worth knowing before you answer:
- This book is efficient most of the time. Moon Dev has tested fleets of bots \
against it and the honest prior is that any given window is a coin flip paying \
a spread. NOTHING is the correct answer for most windows and it costs nothing.
- When the model says a 4-cent side is worth 15 cents, that is usually the \
model being wrong, not the book. The cheap side rots as the clock runs out.
- These numbers come from Binance; Polymarket settles on Chainlink. That feed \
gap is ALREADY built into the P(Up) you are given, which is why it sits closer \
to 0.5 than the raw TWAP suggests. Do not subtract for it again. Judge the \
probability you are handed against the price you would pay.
- NOTHING is for windows with no edge, not for windows with ordinary \
uncertainty. Every one of these is uncertain. If the probability and the price \
disagree enough to be worth five dollars, that is a call, not a coin flip.
- Buying a side at 0.85 to win 0.15 needs to be right 85% of the time just to \
break even. Price is part of the call, not a detail.

Answer in at most three short sentences of reasoning, then these two lines \
exactly, nothing after them:
DECISION: UP or DOWN or NOTHING
CONFIDENCE: a whole number from 50 to 100, how sure you are of that decision"""

def ask(model, brief, max_tokens, timeout):
    r = requests.post(
        OPENROUTER,
        headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                 "Content-Type": "application/json"},
        json={"model": model,
              "messages": [{"role": "system", "content": SYSTEM},
                           {"role": "user", "content": brief}],
              "max_tokens": max_tokens,
              "usage": {"include": True}},
        timeout=timeout)
    r.raise_for_status()
    d = r.json()
    text = d["choices"][0]["message"].get("content") or ""
    return text, (d.get("usage") or {})

def read_answer(text):
    up = text.upper()
    m = re.search(r"DECISION:\s*\**\s*(UP|DOWN|NOTHING)", up)
    if m:
        word = m.group(1)
    else:
        words = re.findall(r"\b(UP|DOWN|NOTHING)\b", up)
        word = words[-1] if words else "NOTHING"
    c = re.search(r"CONFIDENCE:\s*\**\s*(\d{1,3})", up)
    confidence = min(100, int(c.group(1))) if c else 0
    side = {"UP": "Up", "DOWN": "Down"}.get(word)
    return side, confidence

class OpenRouterBrain:
    NAME = "OPENROUTER"
    KEY = "openrouter"
    EMOJI = "🤖"
    MODEL = ""
    TAGLINE = ""
    COST_PER_DAY = "$10"
    CONTEXT_CAP = 120_000
    MAX_TOKENS = 1500
    TIMEOUT = 120
    MIN_CONFIDENCE = 0

    def check(self):
        if not os.getenv("OPENROUTER_API_KEY"):
            raise RuntimeError("OPENROUTER_API_KEY is not in your .env, so "
                               f"{self.NAME} cannot decide anything.")
        if not os.getenv("MOONDEV_API_KEY"):
            raise RuntimeError("MOONDEV_API_KEY is not in your .env, so the "
                               "near-liquidation feed cannot be read.")

    def decide(self, pack, record):
        brief, toks = core.fit_brief(pack, record, self.CONTEXT_CAP)
        core.row(f"{core.DIM}sending {toks:,} tokens to {self.MODEL}{core.OFF}")

        t0 = time.time()
        try:
            text, usage = ask(self.MODEL, brief, self.MAX_TOKENS, self.TIMEOUT)
        except Exception as e:
            return (None, "", "", f"{self.NAME} call failed: {type(e).__name__}",
                    {"error": type(e).__name__,
                     "latency_ms": (time.time() - t0) * 1000})
        ms = (time.time() - t0) * 1000

        side, confidence = read_answer(text)
        if not text.strip():
            why = "came back empty, which is a NOTHING, not a yes"
        else:
            why = re.sub(r"\s+", " ", re.split(r"DECISION:", text, 1)[0]).strip()
            why = (why[:240] or "no reasoning given") + f"  [{confidence}%]"

        if side and confidence < self.MIN_CONFIDENCE:
            why = (f"only {confidence}% sure, under the {self.MIN_CONFIDENCE}% "
                   f"line — wanted {side}. {why}")
            side = None

        p_up = ("" if side is None else
                round(confidence / 100 if side == "Up" else 1 - confidence / 100, 4))

        return side, p_up, confidence, why, {
            "latency_ms": round(ms, 1),
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
            "cost_usd": round(float(usage.get("cost") or 0), 8),
            "model": self.MODEL,
            "raw": re.sub(r"\s+", " ", text)[:600],
        }

def decide_call(model, state, questions, timeout):
    r = requests.post(
        DECISIONS,
        headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                 "Content-Type": "application/json"},
        json={"model": model, "state": state, "questions": questions},
        timeout=timeout)
    r.raise_for_status()
    return r.json()

class DecisionsBrain:
    NAME = "DECISIONS"
    KEY = "decisions"
    EMOJI = "⚡"
    MODEL = ""
    TAGLINE = ""
    COST_PER_DAY = "$0.06"
    CONTEXT_CAP = 28_000
    TIMEOUT = 15
    QUESTIONS = {}

    def check(self):
        if not os.getenv("OPENROUTER_API_KEY"):
            raise RuntimeError("OPENROUTER_API_KEY is not in your .env, so "
                               f"{self.NAME} cannot decide anything.")
        if not os.getenv("MOONDEV_API_KEY"):
            raise RuntimeError("MOONDEV_API_KEY is not in your .env, so the "
                               "near-liquidation feed cannot be read.")

    def read(self, answers):
        raise NotImplementedError

    def decide(self, pack, record):
        state, toks = core.fit_state(pack, record, self.CONTEXT_CAP)
        core.row(f"{core.DIM}sending ~{toks:,} tokens to {self.MODEL}{core.OFF}")

        t0 = time.time()
        try:
            d = decide_call(self.MODEL, state, self.QUESTIONS, self.TIMEOUT)
        except Exception as e:
            return (None, "", "", f"{self.NAME} call failed: {type(e).__name__}",
                    {"error": type(e).__name__,
                     "latency_ms": (time.time() - t0) * 1000})
        ms = (time.time() - t0) * 1000

        side, p_up, confidence, why, extra = self.read(d.get("answers") or {})
        usage = d.get("usage") or {}
        return side, p_up, confidence, why, {
            **extra,
            "latency_ms": round(ms, 1),
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "cost_usd": round(float(usage.get("cost") or 0), 10),
            "model": d.get("model") or self.MODEL,
            "request_id": d.get("id"),
        }
```
### jev_5min_bot.py

4 of 8 — Jev, six typed questions.

jev_5min_bot.py

```python
"""
================================================================================
⚡ MOON DEV's JEV 5-MINUTE BOT: Jev calls every BTC window, up or down
================================================================================
Polymarket opens a new BTC up-or-down market every five minutes. This bot hands
Jev the facts and Jev says UP, DOWN, or NOTHING. Moon Dev's money follows.

Same round, same facts, same $5, same CSV columns and same screen as
astra_5min_bot.py and fable_5min_bot.py. The brain is the only thing that
differs, which is the whole point.

WHY JEFF IS A DIFFERENT SHAPE FROM THE OTHER TWO
Astra and Fable write a paragraph and we fish the answer out of it with a regex.
Jev never writes prose at all. You hand him STATE plus TYPED QUESTIONS and the
answers come back as VALUES in one forward pass: a choice with calibrated
probabilities, a 0-1 noul, a score. Nothing to parse, so nothing to mis-parse,
and no round is ever lost to a reasoning model burning its whole budget thinking
and handing back null.

MEASURED ON MOON DEV'S OWN PACK, not from a vendor page:
  ⚡ 325-420ms, p50 about 380ms, against 3.8s for Astra and 5.8s for Fable
  💸 $0.00022 a round on the full 5,260-token pack. 288 windows a day is SIX
     CENTS. Astra and Fable are about $10 a day each. Jev is ~150x cheaper.
  🎯 every question is answered IN PARALLEL, so the sixth one is free in time.
     That is why this asks six instead of one.

🚨 HOW TO REACH JEFF, because this cost an hour of confusion:
   Jev IS on OpenRouter, on your normal OPENROUTER_API_KEY, with NO extra
   signup and NO extra SDK. But it is a DECISIONS model, so it lives at
   /api/alpha/decisions, NOT at /chat/completions, and `GET /v1/models` does
   not list it. Ask for it on the chat endpoint and OpenRouter tells you so
   in plain English. See openrouter_brain.py for the wire format.

🚨 JEV IS A CLASSIFIER, NOT AN EDGE. It reads exactly the same pack Astra and
   Fable read. Faster and cheaper is not the same as righter. Moon Dev's own
   fleet testing says this 5-minute book is EFFICIENT, so the honest prior is
   that all three of these bots are coin flips paying a spread. The CSV is the
   point. Let it run, then read it.

SETUP  OPENROUTER_API_KEY and MOONDEV_API_KEY in .env, plus the usual
       Polymarket keys every bot in this folder uses. That is all.

RUN  python bots/polymarket/bots/jev_5min_bot.py

Built by Moon Dev 🌙
================================================================================
"""

from ai_5min_core import start
from openrouter_brain import DecisionsBrain

TRADE_AT = 0.58
TOO_THIN_VETO_AT = 0.70

QUESTIONS = {
    "call": {
        "type": "choice",
        "instructions": (
            "Which way does this 5-minute window settle? UP means the "
            "TIME-WEIGHTED AVERAGE price across the whole window ends at or "
            "above the strike. DOWN means the average ends below it. It is the "
            "AVERAGE, not the closing price, and the seconds already elapsed "
            "are locked into it. NOTHING means sit this window out, which "
            "costs nothing and is the right answer whenever the two sides look "
            "the same."),
        "criteria": {
            "up": "The average looks like it ends at or above the strike, and "
                  "the Up side is not already priced as if everyone knows it.",
            "down": "The average looks like it ends below the strike, and the "
                    "Down side is not already priced for it.",
            "nothing": "A coin flip, or the cheap side is cheap for a good "
                       "reason. Sitting out costs nothing.",
        },
    },
    "too_thin": {
        "type": "noul",
        "instructions": (
            "The information given is too thin to tell this 5-minute window "
            "apart from any other window whose average sits the same distance "
            "from its strike."),
        "criteria": {
            "true": "Nothing here distinguishes it. Any answer would be a guess.",
            "false": "There is something specific in this window to go on.",
        },
    },
    "tape": {
        "type": "choice",
        "instructions": (
            "Given the recent bars, the 24-hour range position and the "
            "volatility numbers, what does this market's behaviour most look "
            "like right now?"),
        "criteria": {
            "trending_up": "A persistent push higher that is still going.",
            "trending_down": "A persistent push lower that is still going.",
            "chopping": "Two-sided noise around a level. No direction.",
            "reversing": "A move rolling over or bouncing off an extreme.",
        },
    },
    "book_read": {
        "type": "choice",
        "instructions": (
            "The barrier model's fair value and the order book disagree by the "
            "amount shown. Who is more likely to be right here?"),
        "criteria": {
            "book_is_right": "The book is pricing something real that a random "
                             "walk model cannot see. Do not fade it.",
            "model_is_right": "The book looks lazy or thin and the model's "
                              "number is the better estimate.",
            "too_close": "They barely disagree. Nothing here either way.",
        },
    },
    "liq_pull": {
        "type": "choice",
        "instructions": (
            "Hyperliquid positions near liquidation are listed. Longs blow up "
            "below spot and sell into it, shorts blow up above spot and buy "
            "into it. Does either pool matter for the next few minutes?"),
        "criteria": {
            "pulls_down": "The long pool below is big and close enough to get "
                          "swept inside this window.",
            "pulls_up": "The short pool above is big and close enough to get "
                        "swept inside this window.",
            "no_pull": "Neither pool is close or big enough to move price in "
                       "the next few minutes, or the feed is missing.",
        },
    },
    "difficulty": {
        "type": "score",
        "instructions": "How hard a call is this window?",
        "criteria": [
            "Obvious. The cushion and the clock all but settle it.",
            "Leaning clearly one way.",
            "A real question with arguments on both sides.",
            "Close to a coin flip.",
            "Pure noise. Nobody could call this.",
        ],
    },
}

DIFFICULTY_TOP = len(QUESTIONS["difficulty"]["criteria"]) - 1

class Jev(DecisionsBrain):
    NAME = "JEV"
    KEY = "jev"
    EMOJI = "⚡"
    MODEL = "typesafe/jev-1.13"
    TAGLINE = ("Jev answers in typed values, not paragraphs, in under half a "
               "second for two hundredths of a cent.")
    COST_PER_DAY = "$0.06"
    QUESTIONS = QUESTIONS

    def read(self, a):
        call = a.get("call") or {}
        probs = call.get("probabilities") or {}
        p_up = float(probs.get("up", 0.0))
        p_down = float(probs.get("down", 0.0))
        confidence = float(call.get("confidence", 0.0))

        thin = float((a.get("too_thin") or {}).get("noul", 0.0))
        tape = (a.get("tape") or {}).get("choice", "?")
        bookread = (a.get("book_read") or {}).get("choice", "?")
        liq = (a.get("liq_pull") or {}).get("choice", "?")
        hard = float((a.get("difficulty") or {}).get("score", 0.0))

        side = ("Up" if p_up >= TRADE_AT else
                "Down" if p_down >= TRADE_AT else None)
        why = (f"p(up) {p_up:.0%}, p(down) {p_down:.0%}, {tape} tape, "
               f"{bookread}, {liq}, difficulty {hard:.1f}/{DIFFICULTY_TOP}")
        if side is None:
            why = f"under the {TRADE_AT:.0%} line — {why}"

        if side and thin >= TOO_THIN_VETO_AT:
            why = (f"vetoed: Jev says the pack is too thin ({thin:.0%}) to "
                   f"tell this window apart — he wanted {side} at "
                   f"{max(p_up, p_down):.0%}")
            side = None

        return side, round(p_up, 4), round(confidence, 4), why, {
            "p_up": round(p_up, 4), "p_down": round(p_down, 4),
            "call_confidence": round(confidence, 4),
            "too_thin": round(thin, 4),
            "tape": tape, "book_read": bookread, "liq_pull": liq,
            "difficulty": round(hard, 3),
        }

if __name__ == "__main__":
    start(Jev())
```
### astra_5min_bot.py

5 of 8 — Astra.

astra_5min_bot.py

```python
"""
================================================================================
🛰️ MOON DEV's ASTRA 5-MINUTE BOT: GPT-6 Astra calls every BTC window
================================================================================
The same bot as jev_5min_bot.py and fable_5min_bot.py, with a different brain.
Same facts, same round, same $5, same CSV columns, same screen. The ONLY thing
that differs is who is asked, which is the whole point: three bots, one question,
and a log that settles it.

Astra reads the pack as English and writes back a few sentences plus a decision.
That costs seconds where Jev costs milliseconds, and it costs about a thousand
times more per call. What it buys, if anything, is a model that can actually
reason about the shape of the tape instead of classifying it. The CSV will say.

SETUP  OPENROUTER_API_KEY and MOONDEV_API_KEY in .env, plus the usual
       Polymarket keys every bot in this folder uses.

RUN  python bots/polymarket/bots/astra_5min_bot.py

Built by Moon Dev 🌙
================================================================================
"""

from ai_5min_core import start
from openrouter_brain import OpenRouterBrain

class Astra(OpenRouterBrain):
    NAME = "ASTRA"
    KEY = "astra"
    EMOJI = "🛰️"
    MODEL = "openai/gpt-6-astra"
    TAGLINE = "GPT-6 Astra reads the tape in English and writes back a call."
    MIN_CONFIDENCE = 0

if __name__ == "__main__":
    start(Astra())
```
### fable_5min_bot.py

6 of 8 — Fable.

fable_5min_bot.py

```python
"""
================================================================================
📖 MOON DEV's FABLE 5-MINUTE BOT: Claude Fable 5.1 calls every BTC window
================================================================================
The third bot in the set. Identical to jev_5min_bot.py and astra_5min_bot.py in
every way except the brain. Same facts, same round, same $5, same CSV columns,
same screen, so the only variable in the experiment is the model.

Fable is the voice in the order chimes you already hear in this folder, which is
a coincidence and not a reason to believe it can call a coin flip. Let it run
and read the log.

SETUP  OPENROUTER_API_KEY and MOONDEV_API_KEY in .env, plus the usual
       Polymarket keys every bot in this folder uses.

RUN  python bots/polymarket/bots/fable_5min_bot.py

Built by Moon Dev 🌙
================================================================================
"""

from ai_5min_core import start
from openrouter_brain import OpenRouterBrain

class Fable(OpenRouterBrain):
    NAME = "FABLE"
    KEY = "fable"
    EMOJI = "📖"
    MODEL = "anthropic/claude-fable-5.1"
    TAGLINE = "Claude Fable 5.1 reads the tape in English and writes back a call."
    MIN_CONFIDENCE = 0

if __name__ == "__main__":
    start(Fable())
```
### poly_core.py

7 of 8 — all the Polymarket wiring. No trading decisions.

poly_core.py

```python
"""
================================================================================
🌙 MOON DEV's POLYMARKET CORE: the wiring every 5-minute bot needs
================================================================================
Account, market lookup, order book, orders, resolution. Nothing in here makes
a trading decision. It exists so a bot file can be about its IDEA instead of
about DepositWallet signatures and Gamma query flags.

Same .env and account as patience_bot.py. Run test_connection.py first.

Built by Moon Dev 🌙
================================================================================
"""

import os
import re
import sys
import json
import math
import time
import queue
import shutil
import logging
import threading
import subprocess
from datetime import datetime

import requests
from web3 import Web3

from py_clob_client_v2.client import ClobClient
from py_clob_client_v2.clob_types import (
    ApiCreds, OrderArgs, OrderType, OrderMarketCancelParams,
    PartialCreateOrderOptions, BalanceAllowanceParams, AssetType,
)
from py_clob_client_v2.constants import POLYGON

import poly_1271

logging.getLogger("py_clob_client_v2").setLevel(logging.CRITICAL)

MARKET_DURATION = 300
MIN_SHARES = 5           # Polymarket minimum order size
SIGNATURE_TYPE = 3       # 3 = DepositWallet. test_connection.py confirms yours.
CLOB_HOST = "https://clob.polymarket.com"
GAMMA = "https://gamma-api.polymarket.com/markets"
DATA_API = "https://data-api.polymarket.com"

ENV_ADDRESS = "pm_crack_hft_adderess"
ENV_PRIVATE_KEY = "pm_crack_hft_privatekey"
ENV_BUILDER_CODE = "pm_crack_hft_builderkey"
ENV_API_KEY = "pm_crack_hft_apiKey"
ENV_SECRET = "pm_crack_hft_secret"
ENV_PASSPHRASE = "pm_crack_hft_passphrase"

GREEN, RED, YELLOW, CYAN, MAG, WHITE, BOLD, DIM, OFF = (
    "\033[32m", "\033[31m", "\033[33m", "\033[36m", "\033[35m",
    "\033[97m", "\033[1m", "\033[2m", "\033[0m")

def load_env(path):
    """🌙 Moon Dev - tiny .env parser, no dotenv dependency."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
AGENTS_ENV = os.getenv("RESTREAM_ENV_PATH") or os.path.join(
    os.path.dirname(PROJECT_ROOT), "moon-dev-ai-agents-for-trading", ".env")
load_env(os.path.join(PROJECT_ROOT, ".env"))
load_env(AGENTS_ENV)

SOUNDS = "/Users/md/Dropbox/dev/github/ai-agent-to-clip-youtube-videos/sounds/"
FILL_SOUND = SOUNDS + "order_filled_ballad_1.6x.wav"
CANCEL_SOUND = SOUNDS + "order_canceled_ballad_1.6x.wav"
ROUND_SOUND = SOUNDS + "new_round_ballad_ding.wav"

_PLAYER = shutil.which("afplay") or shutil.which("aplay") or shutil.which("play")
_SOUND_Q = queue.Queue(maxsize=2)
_SOUND_OK = bool(_PLAYER) and os.path.exists(FILL_SOUND)

def _sound_worker():
    while True:
        path = _SOUND_Q.get()
        try:
            subprocess.run([_PLAYER, path], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=30)
        except Exception:
            pass

if _SOUND_OK:
    threading.Thread(target=_sound_worker, daemon=True).start()

def play_sound(path):
    if not _SOUND_OK or not path:
        return
    try:
        _SOUND_Q.put_nowait(path)
    except queue.Full:
        pass

_STICKY = []
_TTY = sys.stdout.isatty()
_ANSI = re.compile(r"\033\[[0-9;]*m")

def width():
    return max(20, shutil.get_terminal_size((100, 24)).columns - 1)

def narrow():
    return width() < 60

def clock(seconds):
    return f"{max(0, int(seconds)) // 60}:{max(0, int(seconds)) % 60:02d}"

def when(ts=None, secs=False):
    t = datetime.now() if ts is None else datetime.fromtimestamp(ts)
    return t.strftime("%-I:%M:%S %p" if secs else "%-I:%M %p")

def bar(up, down, cells=20):
    if not up + down:
        return f"{DIM}{'░' * cells}{OFF}"
    filled = round(cells * up / (up + down))
    return f"{GREEN}{'█' * filled}{OFF}{RED}{'█' * (cells - filled)}{OFF}"

def phase_name(long, short):
    return short if narrow() else long

def vis(text):
    return _ANSI.sub("", text)

_JOIN = re.compile(r"[\U0001F3FB-\U0001F3FF️]|‍.", re.DOTALL)
_WIDE = re.compile(
    "[\U0001F000-\U0001FAFF⌚⌛⏩-⏳◽◾☔☕"
    "♈-♓♿⚓⚠⚡⚪⚫⚽⚾⛄⛅"
    "⛎⛔⛪⛲⛳⛵⛺⛽✅✊✋✨"
    "❌❎❓-❕❗➕-➗➰➿⬛⬜"
    "⭐⭕]")

def cols(text):
    t = _JOIN.sub("", _ANSI.sub("", text))
    return len(t) + len(_WIDE.findall(t))

def wrap(text, indent="", hang=None):
    hang = indent if hang is None else hang
    lim, lines, cur, lead = width(), [], indent, indent
    for word in text.split(" "):
        if not word:
            continue
        if cur != lead and cols(cur) + 1 + cols(word) > lim:
            lines.append(cur + OFF)
            cur, lead = hang + word, hang
        else:
            cur += word if cur == lead else " " + word
    lines.append(cur + OFF)
    return lines

def clip(text):
    kept, seen, i, lim = [], 0, 0, width()
    while i < len(text) and seen < lim:
        m = _ANSI.match(text, i)
        if m:
            kept.append(m.group())
            i = m.end()
            continue
        kept.append(text[i])
        seen += cols(text[i])
        i += 1
    return "".join(kept) + OFF

def _paint():
    print("\r\033[K" + "\n\r\033[K".join(_STICKY), end="", flush=True)

def _wipe():
    print("\r\033[K", end="")
    for _ in range(len(_STICKY) - 1):
        print("\033[A\r\033[K", end="")

def out(line=""):
    if not _TTY:
        print(line, flush=True)
        return
    _wipe()
    print(line, flush=True)
    if _STICKY:
        _paint()

def sticky(*lines):
    global _STICKY
    new = [clip(t) for t in lines if t]
    if new == _STICKY:
        return
    if _TTY:
        _wipe()
    _STICKY = new
    if _TTY and _STICKY:
        _paint()

def unstick():
    global _STICKY
    if _TTY:
        _wipe()
    _STICKY = []

def say(msg, color=""):
    tail = OFF if color else ""
    stamp = "" if width() < 60 else f"{DIM}[{when(secs=True)}]{OFF} "
    for line in wrap(f"{stamp}{color}{msg}{tail}", "", "  "):
        out(line)

_CLIENT = None
_WALLET = None
_KEY = None

def client():
    global _CLIENT, _WALLET, _KEY
    if _CLIENT is not None:
        return _CLIENT
    _KEY = os.getenv(ENV_PRIVATE_KEY)
    address = os.getenv(ENV_ADDRESS)
    if not _KEY or not address:
        say(f"Missing {ENV_PRIVATE_KEY} or {ENV_ADDRESS} in your .env. "
            f"Run test_connection.py.", RED)
        sys.exit(1)
    _WALLET = Web3.to_checksum_address(address)
    c = ClobClient(host=CLOB_HOST, chain_id=POLYGON, key=_KEY,
                   signature_type=SIGNATURE_TYPE, funder=_WALLET)
    api_key, secret, passphrase = (os.getenv(ENV_API_KEY), os.getenv(ENV_SECRET),
                                   os.getenv(ENV_PASSPHRASE))
    if api_key and secret and passphrase:
        c.set_api_creds(ApiCreds(api_key=api_key, api_secret=secret,
                                 api_passphrase=passphrase))
        try:
            c.get_balance_allowance(BalanceAllowanceParams(
                asset_type=AssetType.COLLATERAL, signature_type=SIGNATURE_TYPE))
        except Exception:
            c.set_api_creds(c.create_or_derive_api_key())
    else:
        c.set_api_creds(c.create_or_derive_api_key())
    _CLIENT = c
    return c

def balance():
    b = client().get_balance_allowance(BalanceAllowanceParams(
        asset_type=AssetType.COLLATERAL, signature_type=SIGNATURE_TYPE))
    return float(b.get("balance", 0) or 0) / 1e6

_META = {}

def market_meta(token_id):
    key = str(token_id)
    if key not in _META:
        c = client()
        _META[key] = (str(c.get_tick_size(key)), bool(c.get_neg_risk(key)))
    return _META[key]

def place(token_id, side, price, shares, post_only):
    c = client()
    tick_size, neg_risk = market_meta(token_id)
    options = PartialCreateOrderOptions(tick_size=tick_size, neg_risk=neg_risk)
    args = OrderArgs(token_id=str(token_id), price=float(price), size=float(shares),
                     side=side, builder_code=os.getenv(ENV_BUILDER_CODE))
    if SIGNATURE_TYPE == 3:
        return poly_1271.create_and_post_order(
            c, args, options, OrderType.GTC, post_only, _KEY, _WALLET, POLYGON) or {}
    return c.create_and_post_order(args, options=options,
                                   order_type=OrderType.GTC, post_only=post_only) or {}

def cancel_all_on(token_id):
    client().cancel_market_orders(OrderMarketCancelParams(asset_id=str(token_id)))

def position_in(token_id):
    try:
        r = requests.get(f"{DATA_API}/positions",
                         params={"user": _WALLET, "limit": 500}, timeout=10)
        if r.status_code != 200:
            return (0.0, 0.0)
        for p in r.json():
            if str(p.get("asset")) == str(token_id):
                return (float(p.get("size", 0) or 0), float(p.get("avgPrice", 0) or 0))
    except requests.exceptions.RequestException:
        pass
    return (0.0, 0.0)

def window_now():
    return (int(time.time()) // MARKET_DURATION) * MARKET_DURATION

def get_market(window_ts, asset="BTC"):
    slug = f"{asset.lower()}-updown-5m-{window_ts}"
    try:
        r = requests.get(GAMMA, params={"slug": slug}, timeout=10)
        if r.status_code != 200 or not r.json():
            return None
        m = r.json()[0]
        outcomes = json.loads(m.get("outcomes", "[]"))
        tokens = json.loads(m.get("clobTokenIds", "[]"))
        if not tokens:
            return None
        return {"slug": slug, "tokens": dict(zip(outcomes, tokens)), "ts": window_ts}
    except (requests.exceptions.RequestException, ValueError, TypeError):
        return None

def get_resolution(slug):
    try:
        r = requests.get(GAMMA, params={"slug": slug, "closed": "true"}, timeout=10)
        if r.status_code != 200 or not r.json():
            return None
        m = r.json()[0]
        if not m.get("closed"):
            return None
        outcomes = json.loads(m.get("outcomes", "[]"))
        prices = [float(p) for p in json.loads(m.get("outcomePrices", "[]"))]
        if len(outcomes) != len(prices) or not prices:
            return None
        return outcomes[prices.index(max(prices))]
    except (requests.exceptions.RequestException, ValueError, TypeError):
        return None

def book(token_id):
    try:
        r = requests.get(f"{CLOB_HOST}/book", params={"token_id": token_id}, timeout=8)
        if r.status_code != 200:
            return (None, None)
        d = r.json()
        bids = [float(b["price"]) for b in d.get("bids", [])]
        asks = [float(a["price"]) for a in d.get("asks", [])]
        return (max(bids) if bids else None, min(asks) if asks else None)
    except (requests.exceptions.RequestException, ValueError):
        return (None, None)

def shares_for(usd, price):
    return max(float(MIN_SHARES), math.floor((usd / price) * 100) / 100)
```
### poly_1271.py

8 of 8 — the signing fix for DepositWallets.

poly_1271.py

```python
"""
================================================================================
🌙 MOON DEV's POLY_1271 SIGNER — makes Polymarket DepositWallets tradeable
================================================================================
WHY THIS FILE EXISTS
--------------------
Polymarket's newer accounts are `DepositWallet` smart contracts. They sign via
EIP-1271, which the CLOB calls signature_type 3 (POLY_1271). `py_clob_client_v2`
1.0.0 cannot place those orders: it hardcodes the order's `signer` field to your
EOA address, but the exchange needs `maker` AND `signer` to both be the wallet,
with an ERC-7739 wrapped signature the wallet's `isValidSignature` accepts.

You hit this as:
    400 {'error': 'the order signer address has to be the address of the API KEY'}

Open and unfixed upstream: Polymarket/py-clob-client-v2 issues #64 and #70,
which claim deposit-wallet users are "completely blocked from programmatic
order placement." They are not. This is the missing ~60 lines.

WHAT IT DOES
------------
Builds the order with the SDK as usual (correct amounts, rounding, salt), then
rewrites `signer` to the wallet and replaces the signature with an ERC-7739
"TypedDataSign" wrapper that the DepositWallet validates on-chain.

The wrapper, per Solady's ERC1271 (which DepositWallet inherits):

    digest = keccak(0x1901 || APP_DOMAIN_SEPARATOR || hashStruct(TypedDataSign))
    sig    = r||s||v || APP_DOMAIN_SEPARATOR || contents
             || contentsType || uint16(len(contentsType))

where `contents` is the struct hash of the thing being signed (the Order), and
the TypedDataSign struct carries the wallet's own EIP-712 domain. Verified
against the live contract: `isValidSignature` returns 0x1626ba7e.

L1 auth (creating API creds) still binds to the EOA — that is what Polymarket's
docs specify, and it is correct. Only the ORDER needs the wallet as signer.

Built by Moon Dev 🌙
================================================================================
"""

from eth_abi import encode as abi_encode
from eth_account import Account
from eth_utils import keccak

from py_clob_client_v2.config import get_contract_config

WALLET_DOMAIN_NAME = "DepositWallet"
WALLET_DOMAIN_VERSION = "1"
WALLET_DOMAIN_SALT = b"\x00" * 32

ORDER_TYPE = (
    b"Order(uint256 salt,address maker,address signer,uint256 tokenId,"
    b"uint256 makerAmount,uint256 takerAmount,uint8 side,uint8 signatureType,"
    b"uint256 timestamp,bytes32 metadata,bytes32 builder)"
)
EXCHANGE_DOMAIN_NAME = "Polymarket CTF Exchange"
EXCHANGE_DOMAIN_VERSION = "2"

ERC1271_MAGIC = "1626ba7e"

def domain_separator(name, version, chain_id, verifying_contract=None):
    """🌙 Moon Dev - EIP-712 domain separator. Omit verifying_contract if the
    domain has no such field (Polymarket's ClobAuth domain does not)."""
    if verifying_contract is None:
        type_hash = keccak(b"EIP712Domain(string name,string version,uint256 chainId)")
        return keccak(abi_encode(
            ["bytes32", "bytes32", "bytes32", "uint256"],
            [type_hash, keccak(name.encode()), keccak(version.encode()), chain_id]))
    type_hash = keccak(
        b"EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)")
    return keccak(abi_encode(
        ["bytes32", "bytes32", "bytes32", "uint256", "address"],
        [type_hash, keccak(name.encode()), keccak(version.encode()),
         chain_id, verifying_contract]))

def erc7739_sign(private_key, wallet, chain_id, app_domain_sep, contents_hash, contents_type):
    """🌙 Moon Dev - the ERC-7739 nested-EIP-712 signature a DepositWallet accepts.

    `contents_type` must start with the struct name (implicit mode), e.g.
    b"Order(uint256 salt,...)". Returns raw bytes, not hex."""
    contents_name = contents_type.split(b"(")[0]
    type_hash = keccak(
        b"TypedDataSign(" + contents_name +
        b" contents,string name,string version,uint256 chainId,"
        b"address verifyingContract,bytes32 salt)" + contents_type)
    struct_hash = keccak(abi_encode(
        ["bytes32", "bytes32", "bytes32", "bytes32", "uint256", "address", "bytes32"],
        [type_hash, contents_hash, keccak(WALLET_DOMAIN_NAME.encode()),
         keccak(WALLET_DOMAIN_VERSION.encode()), chain_id, wallet, WALLET_DOMAIN_SALT]))
    digest = keccak(b"\x19\x01" + app_domain_sep + struct_hash)
    signature = Account._sign_hash(digest, private_key).signature
    return (bytes(signature) + app_domain_sep + contents_hash + contents_type +
            len(contents_type).to_bytes(2, "big"))

def order_struct_hash(order):
    """🌙 Moon Dev - EIP-712 struct hash of a signed V2 order object."""
    return keccak(abi_encode(
        ["bytes32", "uint256", "address", "address", "uint256", "uint256", "uint256",
         "uint8", "uint8", "uint256", "bytes32", "bytes32"],
        [keccak(ORDER_TYPE), int(order.salt), order.maker, order.signer, int(order.tokenId),
         int(order.makerAmount), int(order.takerAmount), int(order.side),
         int(order.signatureType), int(order.timestamp),
         bytes.fromhex(order.metadata[2:]), bytes.fromhex(order.builder[2:])]))

def resign_as_wallet(order, private_key, wallet, chain_id, neg_risk):
    """🌙 Moon Dev - rewrite an SDK-built order into a valid POLY_1271 order.

    The SDK sets signer to your EOA; EIP-1271 needs the WALLET to be the signer,
    with a signature its isValidSignature accepts. Mutates and returns the order."""
    contracts = get_contract_config(chain_id)
    exchange = contracts.neg_risk_exchange_v2 if neg_risk else contracts.exchange_v2
    order.signer = wallet
    app_domain_sep = domain_separator(
        EXCHANGE_DOMAIN_NAME, EXCHANGE_DOMAIN_VERSION, chain_id, exchange)
    signature = erc7739_sign(private_key, wallet, chain_id, app_domain_sep,
                             order_struct_hash(order), ORDER_TYPE)
    order.signature = "0x" + signature.hex()
    return order

def create_and_post_order(client, order_args, options, order_type, post_only,
                          private_key, wallet, chain_id):
    """🌙 Moon Dev - drop-in replacement for client.create_and_post_order() on a
    DepositWallet. Build with the SDK, re-sign as the wallet, then post."""
    order = client.create_order(order_args, options=options)
    resign_as_wallet(order, private_key, wallet, chain_id, options.neg_risk)
    return client.post_order(order, order_type=order_type, post_only=post_only)

def verify_wallet_accepts_key(w3, wallet, private_key, chain_id):
    """🌙 Moon Dev - read-only proof that this key can sign for this wallet.

    Wraps a throwaway struct and asks the contract. Returns True if it answers
    with the ERC-1271 magic value. Costs nothing, changes nothing."""
    probe_type = b"Probe(bytes32 nonce)"
    contents = keccak(abi_encode(["bytes32", "bytes32"],
                                 [keccak(probe_type), keccak(b"moondev")]))
    app_sep = domain_separator("MoonDevProbe", "1", chain_id)
    app_hash = keccak(b"\x19\x01" + app_sep + contents)
    signature = erc7739_sign(private_key, wallet, chain_id, app_sep, contents, probe_type)
    contract = w3.eth.contract(address=wallet, abi=[
        {"inputs": [{"name": "h", "type": "bytes32"}, {"name": "s", "type": "bytes"}],
         "name": "isValidSignature", "outputs": [{"type": "bytes4"}],
         "stateMutability": "view", "type": "function"}])
    try:
        return contract.functions.isValidSignature(app_hash, signature).call().hex().startswith(ERC1271_MAGIC)
    except Exception:
        return False
```
## Go Build Your Own Edge

Please do not just run this bot and expect it to pay your rent. Thirty trades over two days is a rounding error, not an edge, and this 5-minute market has humbled a lot of clever people. What is actually worth taking from this build is the *shape* of it: **do all the arithmetic in Python so the model only makes judgment calls, show every model identical facts so the comparison means something, run one trade instead of three, grade the losers with shadow books so you learn from windows you never traded, price those shadows at the real ask so you cannot lie to yourself, and write it all to one wide CSV you can sort in a spreadsheet.**

That pattern transfers to every model comparison you will ever run, on any market. The specific question of whether Jev, Astra, or Fable can call the next five minutes of Bitcoin is just this week's excuse to build the apparatus.

So fork it and change something. Add a fourth model to VOTERS and watch every scorecard adapt on its own. Set NEED_AGREE = 3 and see whether unanimity is worth the trades it costs you. Move DECIDE_AT_SEC to 200 and trade more certainty for a worse price. Re-fit BASIS_USD once you have a few hundred rows instead of fourteen. Then come tell the Moon Dev community what the numbers actually said, especially if they said the whole thing is noise. That is a result too, and it is the most valuable one you can get cheaply.

Built by Moon Dev 🌙

## Want to build trading bots with Moon Dev?

Join the community, get the full code from every video, and learn algorithmic trading, quantitative finance, and how to actually automate your trading.

[Explore the Roadmap](https://moondev.com/roadmap)

## Related Moon Dev Builds

[

### Polymarket 5-Minute Bot

The original take on the same 5-minute BTC window, without the AI vote.

[

### Liq Magnet Bot

Uses the same near-liquidation feed, but as the whole signal rather than one input.

[

### Strike-Cross Sniper

A pure mechanical read of the same market, with no model in the loop at all.

[

### Full Code-From-Videos Roadmap

Every open-source trading bot walkthrough in one place.

Built by Moon Dev 🌙
