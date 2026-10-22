# YouTube transcript — "how do prop firm bots actually work" (Moon Dev stream)

Source: user-provided NoteGPT auto-transcript · Filed 2026-10-14 in `Prop Firm Bots/`
Companion build: `prop_firm_lab/passed_test.py` (our rule-replay checker, inspired
by his `passed_test.py`). Trust-model context: `../VENUE-TRUST-MODEL.md`.

## Key claims & numbers (verbatim from the transcript)

**The machine:**
- Pay a fee → get a SIMULATION account: $50→$10k, $125→$25k, **$245→$50k**,
  ~$1,000→$100k. Orders never reach the real market.
- Pass = **+9% profit target, NO time limit**. Then balance RESETS to $50k and
  you enter the funded sim with an **80/20 split** (his phrasing flips once —
  "the firm keeps 80%" — but "your upside is 80% of whatever you make, no
  ceiling" matches the industry standard: trader keeps 80%).
- Two instant-death floors: **daily loss ~3%** and **max drawdown 3%** (static —
  "if you go up at the start, the floor doesn't move").
- "You have to double-win": pass the test, THEN start earning the split.

**The reframe:**
- It's an **option, not leverage**: premium = fee, max loss = fee, upside = 80%
  of uncapped profits, ~204x effective ($245 controlling $50k).
- "The fee is the max loss… it equalizes things a little bit" (birthplace
  fairness point).
- "Leverage multiplies your worst day, not your edge." >10x leverage by hand
  = "cooked".

**The economics (his numbers from the firm's own site):**
- Only **15% of paid evaluations ever pass**; of passers, **78% never withdraw
  a dollar**. "The losers' fees are the winners' payouts… a little Ponzi-ish,
  but apparently legal."
- ~$3.6M evaluation fees collected by the firm he looked at.
- Everything simulated → the firm SEES every signal; could trade against/with
  them. Trust risk: will they keep paying? Reputation is the only moat.
- His firm **allows bots**; he asked them about it, no reply; "I kind of think
  they don't want us trading here for very long." (Regime risk — see
  VENUE-TRUST-MODEL.md.)
- Firm name garbled in transcript (sounds like "Proper").

**His bot work:**
- Built `passed_test.py`: replays any strategy backtest through the firm's
  rules → counts passes/deaths/stalls. Rulebook constants must be edited per
  firm.
- Backtest pass rates: 95%, 97%, 95%, 83% (one 1,374% return / 83% survival vs
  1,051% return / 95% funded). **"The one that returns more money gets funded
  less because it has higher drawdown"** — prop rules invert the normal
  ranking: optimize pass-rate, not return. A 40%-return/6%-DD system "would
  get absolutely cooked on every single prop firm".
- Many of his live systems draw down 4% → instant death at these floors.
- Hand traders: "cooked anyways — you'll get emotional one day… that's what
  they bank on." Retry math: just buy another sim; 83% per attempt stacks.
- RBI honored: "backtests don't necessarily line up with the future"; he
  doubts all three deployed bots pass; will deploy and see.

**The teased "built-in edge" (withheld in this video):**
- He confirms: no clock, floor doesn't trail up, fee = max loss, multiple
  cheap attempts allowed, firm allows bots.

## Our inference of the built-in edge (OUR deduction — not his stated answer)

The rules **punish variance, not slowness**. With no time limit + static
floors + capped fee, a low-variance positive-drift grind sized so its worst
round is ~1% of the account reaches +9% with near-certainty given enough
weeks, while the rushing/tilting majority dies and funds the pool. Add
multiple $50–245 attempts across uncorrelated strategies and the option
portfolio skews positive. This is exactly what `prop_firm_lab/passed_test.py`
now measures (auto-scale mode): size to fit the floors, then ask if the shape
climbs to +9% before a floor hits.

## Annotations for our stack

1. **New venue class = same doctrine.** House writes quirky rules, profits
   from the fee pool, tolerance for bots can vanish overnight. Treat exactly
   like the Polymarket regime-risk posture: measure, cap downside, assume the
   window closes.
2. **Pass-rate > return** at this venue — a different objective function than
   our maker work. If our streams ever clear the ≥200-round gates, this checker
   ranks them for prop-suitability separately from raw PnL.
3. **High-variance shapes are structurally disqualified.** S1's deep-longshot
   payoff (worst round ≈ −107% of deployed capital) forces prop-safe sizing to
   a rounding error (auto-scale 0.0001). Maker-style low-variance streams are
   the natural prop citizens — consistent with "be a maker" everywhere else.
4. **Marketing-pattern note:** the edge is gated behind subscribe/Zoom ("I'll
   present it some other time"). Content is still solid; the teaser is
   deliberate funnel design — same lens as the More Perfect Union analysis.
5. First scores (both STALL = insufficient data) live in
   `prop_firm_lab/results/`. Re-run at the 200-round gate.

---
## Verbatim transcript
00:00:01 - 00:01:19
On October 1st, 2026, after a full year of trying to understand these prop firms, I finally sat down and mapped out every single rule line by line. Most traders who pay for the $245 examination for a $50,000 account, they never read these terms. Most people don't even know how prop firms work, including myself. They think they're buying a pass for real money, but it's actually not real money. And remember, the cap the capital that you do make eventually, the firm keeps 80% of it. And honestly, I thought it was just the

00:00:41 - 00:02:00
same thing where right away you get this account that you can live trade. But what I found out changes everything. So, I I dove deep into the rule book and I finally understand it. So, I want to go ahead and explain it to you, and it explains why a lot of this is just hard to comprehend. So, you pay a fee here to pass a test. So, for example, if you spend the $245 in order to get a $50,000 account, you're actually getting a $50,000 simulation, and you have to pretty much trade until you have a winning of 9%

00:01:20 - 00:02:20
before you get the real account. So, when you pay, you get a simulation account. You're trading it for real on the simulation account, but you don't get to keep those earnings until you pass the 9%. So, you have to win first, right? And there's two floors, and if you touch either one of them, you're absolutely cooked. It's over. You lost your $245 you put in, or if you spot a smaller account, you lost that as well. Now, the two floors are the daily loss floor and the max drawdown floor.

00:01:50 - 00:02:51
Usually, there's a daily loss around 3%, and for this account that I first purchased was also 3% for max drawdown. So, daily loss and max drawdown. If you touch either of those, the account's over. So, if you put $50 in to buy a $10,000 account or $245 in to buy a $50,000 account, if you touch either of those, you lost that money. It's over. Now, the good thing is is if you go up at the start, well, the floor doesn't move. So, you're going to go ahead and you won't you'll have a little more

00:02:19 - 00:03:26
room, I guess, in order to trade without breaking the rules. But, I'm pretty sure you still have the daily drawdown even if you do pass the evaluation. Now, the coolest part to me, at least for the prop firm that I'm using, is that there's no limit. So, I'll tell you about this later, but I felt I I found a built-in edge with prop firms. Especially this one, they allow bots. I don't know if they're going to allow bots forever. I did reach out to the team. I haven't heard anything back. I

00:02:54 - 00:03:56
kind of think they don't want us trading here for very long. So, there is a built-in edge. Maybe you can ask your AI about it. I found it. I'll present it some other time. If you're subscribed, I'll make sure to make a short concise video explaining the built-in edge I did find. And honestly, you know, yes, other than me trying to show people what they they have been asking for about how to build bots for prop firms, other than that, the only reason I'm really going after this is because I did find a

00:03:25 - 00:04:21
built-in edge to these prop firms. There's no clock. There's no limit to how long it takes to get to your profit target. Remember, you have to hit like a 9% profit target to even pass the simulation. And remember, it's all a simulator, so your orders never actually reach the real market. And at first, I was like, "Oh, this sounds like a scam." And you know, it's got its own little sketchiness to it, of course. I mean, it is a simulator. They don't pass your stuff to the real market. But at the end

00:03:53 - 00:04:56
of the day, you know, the money's all green and they do split 80/20 with you if you do pass the initial simulation. Then you're kind of trading on this simulated account and you're still splitting the same amount, which is 80/20. But I just have to make sure you know, this is all simulated and they could be taking your signals and trading against them or with them. We don't know what they're doing with our trades. They pretty much have a venue that you're able to trade on.

00:04:24 - 00:05:16
It's a simulated venue, but if you do pass the test, then hey, you do still get a split the 80/20, but they know for a fact that most people are not going to pass the test. And this is the thing, the losers' fees are the winners' payouts. A little Ponzi-ish, for sure. I think this is very gray at the moment and you have to be worried about are they actually going to pay me out? So you have to find somebody with a good reputation. I think that's why there's so many of these popping up because some

00:04:50 - 00:05:46
of them are sketch. That's why so many people talk about this is because when you find a good one that actually pays out, people promote it. You can see if they got $3.6 million of evaluation fees in, I think that's actually how much they've brought in. Well, a lot will be paid out to traders on that 80/20 split. But remember, most people don't pass the the simulation part and even get to the part of the split because you have to pay the money, you have to hit the target and then you start live trading. And

00:05:18 - 00:06:17
there's a huge quotes under live trading because it's still simulated, but you do get the payouts off that 80/20 there. So somebody was asking me, why why do people do this? Why like what's the difference between using leverage and this? Well, if you only have $50 to your name, if you use 10x leverage, you can trade $500 size. But if you have $50 to your name and use a prop firm, you can go here and buy a $10,000 account. Does that make sense? To me, that was very hard to conceptualize because if you're sitting

00:05:47 - 00:06:41
there with 10 racks, 50 racks, 100 racks, 10 mil, like you'll never look at a prop firm. There's no reason to. I've had so many students come and ask me, "Hey, can you build bots for prop firms?" And I just brush them off. But we're in a different situation. If you only have 200 bucks, you can't trade $10,000 size. But with prop firms you can. But remember this, most people fail in trading and also most people fail and they don't never even pass a prop firm. So, the good thing is if you're using

00:06:14 - 00:07:10
prop firms, then if you fail on that $50 account or that $245 account, you're only losing $245 or $50. I think it's the 50 one buys the 10,000 then 245 245 buys the 50,000. So, it's capped downside and increased leverage. To answer Helmec's question directly. That's what I found out at least. Now, this is the interesting thing and I think it's a little disheartening because you run it up you say you start with a 50,000 account, you run up to 54,000, you don't get that 4,500. You're

00:06:42 - 00:07:42
not up 4,500. You literally just passed the test. And now you get your own $50,000 account and that's where you'll start doing the 80/20 split. So, it's it's a little tricky because you have to like you have to win, you have to pass the test at 9% or whatever and then you can go ahead and start doing a profit split. So, it's like you have to double win, which is tricky. And you can see it starts back at 50,000. So, if you're using that $50,000 account, you pass the test at 54,500

00:07:12 - 00:08:21
and then you open up the actual profit split test the profit split account 80/20 at 50,000 again. And now you get to earn 80,000 on chain then it all resets. Then you can see this is the math behind it. You do a 80/20 split and instead of looking at this at like buying leverage, you're buying an option, right? The premium is $245. I'm sorry, I keep flipping behind the the $245 account and the $50 account. Essentially, the $50 account buys you up to 10,000 size. The $245 account is up to $50,000 size. So, you're buying an

00:07:46 - 00:08:45
option. The downside is capped at $245. The upside is 80% of whatever you make with no ceiling. So, you can see if you only have a few hundred bucks, this is a very like I know wonder people ask me about this so much. It's you know, options are addicting. Being able to get extra leverage is addicting. Being able to take your $245 of capital and turn it into $50,000. Okay, yes. Starting to make sense. But remember, you have to pass the test first. So, you have to have a a good week or two of trading to

00:08:16 - 00:09:13
get to that 9% and then you have the opportunity to start making money. And I think that's like the kind of tricky part and a lot of people don't realize. You're not just saying, "Hey, I'm going to buy a $50,000 account and start live trading with it." No, you're buying the simulation. And if you pass that simulation, then you go into another simulation where now you get a profit split. So, the money is real at the end if you get there. And this is that. $245 controls the whole 50,000 and it's the

00:08:44 - 00:09:34
245 is also the whole downside. So, somebody was asking about why not just use leverage because you can't get 204x leverage anywhere. And if you could get 204x leverage anywhere, you'd lose it. You'd lose all of your money immediately. Cuz if you're using more than like 10x leverage, you're cooked. Now, if you have a built-in edge and a bot can handle that, sure. Use as much leverage as you can handle. But as a hand trader, you know, HyperLiquid gives you 10x leverage for free.

00:09:10 - 00:10:06
But it's not really free, is it? They know you're going to get cooked off it. So, this just essentially gives you more leverage and a capped downside. And then if you want more size, it's just a higher fee. So, you can see you can buy a $25,000 account for $125. But remember, you have to pass the test first and then you get that split on the 25,000. Or you could spend $245 and get a $50,000 account. Or I think you could spend $1,000 and get a $100,000 account. You see how it goes? So,

00:09:37 - 00:10:33
it's kind of cool that the fee is the max loss. I like that part. I also like that this does equalize things a little bit, right? Because if I'm competing against you, but I grew up in uh Europe or America or somewhere that like and you're over there in Africa, you got $42 to your name, dude. Like that's not fair. It's not fair. We literally were just born in different places. And I know there's a lot of people act acting out here in this world acting like, "Oh, I'm better than you." Because I grew up

00:10:06 - 00:11:02
here. Bro, it was a It's a random draw where you grew up. It's a random draw where you were born. So, this equalizes it a little bit. But, remember, it's it's hard. It's hard. You have to pass the simulation first. And leverage kills you. You know that. Leverage multiplies your worst day, not your edge. The three set The 3% daily limit is very hard. I was looking at my systems. I have systems that will pass these. But, a lot of my systems draw down 4% and I would have lost immediately. So,

00:10:34 - 00:11:15
you really have to look if you're an automated trader or even if you're a hand trader. Look at your back test. See what your max drawdown is. If you're a hand trader, you're probably cooked anyways because you'll get emotional one day and you'll double down, triple down, and lose it all anyways. And that's what they bank on. Remember, your profits are coming from other people's evaluation fees, which is very Ponzi-like, but apparently it's legal. But, it's also

00:10:54 - 00:11:57
good because if you have your worst day ever and it's like 20% and you're running you're running this by hand, well, on a prop firm, your worst loss can be whatever you put in, the option you put in, $50, $245. They cut you off immediately. You can see these are some of my strategies I have I've built live here on Zoom. Um this one has a 95% pass rate. This one has a 97% pass rate. This is a 95% pass rate. But, is this live? No, these are back tests. So, as I always preach, research, back test, and then incubate.

00:11:26 - 00:12:31
Because back tests don't necessarily line up with the future. So, if I go go and deploy all three of these, Are they all going to pass? I doubt it. I will go ahead and deploy them though. You can see this one here has a 3.36 drawdown. The pass rate is 83% but it will eventually get cooked. Now, I think this is interesting because you can technically just buy another simulation, buy another simulation, buy another simulation. And so, if you have a 83% pass rate, that's not bad. So, even my worst will probably pass a lot

00:11:59 - 00:12:48
of them. I don't know. This is going to be a journey. Like I said, let me know below. Type in prop firms or something if you want me to go deeper down this rabbit hole because it is a rabbit hole and I do see a built-in edge. I'll explain that some other day if you want me to hear tell you about it but just let me know. I thought this was interesting. These are all based off of real bots that back tests I've built. The one that returns more money actually gets funded less because it has a higher

00:12:23 - 00:13:24
drawdown. So, that's something you have to think about and that's a different way of approaching the markets. You have to go ahead and okay, I see this has a 40% return but the drawdown is 6%. I would get absolutely cooked on every single prop firm. You can see this A4S4 strategy here has a 1,374% return but it only survives 83% of the time. While this other strategy has a 1,051% return but it gets funded 95% of the time. So, I kind of like this. This is kind of exciting because this is like a

00:12:54 - 00:13:58
new it's almost a new venue for trading. You know, we had Solana, we've got Robinhood chain, we've got Polymarket, of course we've got Hyperliquid, stocks, futures. This is almost like a new venue just because they put these quirks in here and like my one of my better systems performs worse than a second. So, I think that's pretty interesting. And here's the honest truth truth, most people do not passed. They never pass the actual evaluation so they put the 50 bucks, 200 bucks down

00:13:26 - 00:14:37
to to take the evaluation. Remember, you have to hit the 9% profit target based off of prop firms actual stats. I have the real stats from their website. Only 15% of paid evaluations ever pass. I mean, that makes sense. 95% of day traders lose, right? So, that actually might be good. And then 78% of people who do pass never withdraw a dollar. So, now you're seeing the Ponzinomics here and how they can actually pay people out because if if 15% of people never get past the step one where they spend the

00:14:01 - 00:15:08
250 or whatever for the account, they just lose that money. And then 78% of people who do pass that part never pull money out, well, they've got so much money from evaluation fees that if you are part of this small sub sector that first passes and then also earns the payout, they're going to have plenty of cash to pay you. But, it is also a little bit of a trust thing, right? You have to trust the company that they're going to keep paying you out. So, again, I still think this is a little sketch,

00:14:35 - 00:15:31
but apparently it's legal and there are a ton of prop firms out there. I think it's a little gray on their side, but us as traders, we're just trading on the venues that we have access to. Again, none of this is financial advice. I'm not a financial advisor. Prop firms have been here for so long now, multiple years, and I've been hearing about them. I know everybody's using them. I just personally haven't until recently I started building out these bots. So, I'm going to fly through this code here

00:15:03 - 00:15:57
because this code will go ahead and show you if you actually pass the test. So, I as you saw earlier, I had a lot of my bots that showed like 98% pass or 92% pass. How did I do that? Well, I built this past test.py. It's one file. It will show you if any strategy actually would pass the test in the past. Now, remember, just because it worked in the past isn't guaranteed it's going to work in the future, but if it worked in the past, it's much more likely work in the future than something

00:15:30 - 00:16:17
that didn't work in the past. So, this past test.py, I'm going to go through fast through it, and you will have all of the code. You'll have to stop and rewind, do whatever you need to do. So, this is the thesis here. These are the caveats here. This is the rule book here. So, you might have to change these if you're going to use a different prop firm. I'm using Proper. You can see this is the run the evaluation code. This is the walk of through the code to see if, you know, you win, lose, etc.

00:15:54 - 00:16:54
This is the actual like past test product part. This is the raw count the passes, deaths, and stalls. This is the cost here. There are costs. They I think they add a fee, which is fair, cuz you don't want to be using a prop firm with no fees and then switch on over to Hybrid Liquid and get cooked by that. I think there is a fee. Here's the rank here. Time, risk, frequency, one table. Here is the table. Here is the actual printout, so you can read through it. And this is how you actually run it. So,

00:16:23 - 00:16:39
every single day I do host a live Zoom, and I'll get you up to speed with me. If you want to learn more about prop firms, let me know below.