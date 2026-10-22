<!-- source: https://moondev.com/roadmap (section #faq) -->
<!-- captured: 2026-10-07 · all 35 Q&A extracted verbatim from the page's JS bundle -->

# 🙋🏽‍♂️ Frequently Asked Questions — Moon Dev Roadmap

> Section of https://moondev.com/roadmap · "got questions?"

---

## 1. What is the best coding language to learn for algo trading?

Python because it's the most widely used language, it isn't too hard to learn and there are so many amazing tutorials and python packages to help you with your journey. Once you learn python, learning a second language, if needed is not going to be that hard. I use 100% python in my systems.

---

## 2. Where to learn coding for algo trading?

I teach how to code in my algo trade camp but you can also learn python on YouTube.

**→ [algo trade camp here](https://algotradecamp.com/?utm_source=roadmap)**

---

## 3. Do you prefer trading crypto vs forex or stocks or futures? Why?

I personally like crypto as I am a fan of decentralization but imo, markets are markets and algo trading can be done with futures, stocks, crypto, prediction markets & any other market that gives you API access.

---

## 4. What is 777?

Peace and love. I believe you can have anything in this world if you lead with love, so while I share absolutely every line of code on YouTube, I get a lot of negative energy thrown at me. It's the only downside of sharing. Sending a 777 is an easy way to send some good vibes to not only me, but everyone reading the comments. Lead with love and kindness and you can have anything in this world. Imo.

---

## 5. Do you run your bots on your computer? How do you run them 24/7?

When getting started I used to run them on my computer but now for scaling, I use a VPS provided by Cherry Servers. There are a ton of VPS providers out there, pick your favorite. That said, I am a big believer in staying away from live trading until you have a bunch of proven backtests. I cover this in the RBI system.

---

## 6. What's the bootcamp's refund policy?

We want to make sure that every customer is extremely happy with their decision to join the bootcamp so we offer a 30 day, no questions asked refund policy. Simply email us and we will refund your money immediately through Stripe, our payment processor. We want to ensure your experience is amazing and if for any reason you don't 100% enjoy the bootcamp, we stand behind our 30 day, 100% guarantee. You can contact us and we will refund you in less than 2-24 hours. Email: moon@algotradecamp.com

---

## 7. Why don't you believe in trading by hand?

While I know there is a small percentage of traders who are profitable from hand trading, it wasn't for me. Emotions would always get in the way at least one day a month and when trading size, that one day can screw up a whole month's work. I believe in working things that can compound. Sitting in front of the charts, guessing price direction doesn't compound. Coding backtests and researching new edges, does. This is why I believe if you are going to trade, you should do it algorithmically or not do it at all.

---

## 8. Do you need a computer science degree for this?

No you don't need a computer science degree to learn how to code. YouTube is the best place on earth, you can learn anything. I didn't go to college for coding, I learned to code after 30 years old from focusing for 4 hours per day, watching YouTube python tutorials. You got this.

---

## 9. How do I start the algo trading journey? If I get the bootcamp for a month, will it be enough?

You can start by consuming this free resource and roadmap, along with my YouTube. If you want me to hold your hand in short, concise videos, you can join the bootcamp. One month will be enough to consume the whole bootcamp. Dependent on your experience, one month may be enough. Regardless, join and see. You can always cancel after a month.

---

## 10. Can you talk about the profitability of algo trading?

Not really, as I don't know your strategy and approach to the market. In algo trading, no one will ever share their edge. If you see someone online trying to sell you a bot that is "plug and play" it's a scam. It's just math, if everyone was running the same strategy, the profits would go to 0. I can teach you how to automate your trading, where to look for strategies and how to backtest them, but I can't speak on profitability since I don't know your strategy.

---

## 11. What's your opinion on machine learning in trading?

Everyone wants to predict price with machine learning but after a bunch of tests, I don't think that is the way. Instead I think it comes down to predicting other things like market regime or when to run a certain strategy. I definitely think there is room for ML in trading, just approached differently, cause if everyone is predicting price, the price won't be the price anymore.

---

## 12. What strategy do you suggest starting with?

I'm not a financial advisor, so I can't suggest anything. The one suggestion I do have, is stop trading by hand, because you will slowly lose all of your money. I understand some traders are profitable by hand, but most will have at least 1 day out of each month they are on 'tilt' and will eventually lose all their money. I can't suggest any strategies as this is not financial advice but I can suggest stepping away from hand trading, even if you don't want to automate it.

---

## 13. What are the sounds going off on your stream?

On my stream I have sounds connected to different market conditions. I am exploring the thought of connecting sounds to market actions. For example: when the market is slightly up in the last 60 mins, you may hear birds chirping. If it is down bad, it may sound like we are in the middle of the ocean getting pummeled by waves. If someone gets liquidated you may hear a dong, or a chopper coming through to pick up their body. Listen closely and you will be able to know what's going on in the markets just by the sounds.

---

## 14. Why can't I just buy a bot from you or someone else?

I'm very skeptical of buying bots on the internet. I think it's just math that if someone is selling a bot with a specific strategy, that strategy will eventually go to 0. I don't suggest you or anyone else ever buy a bot. If you want to automate your trading, it has to be with your strategy - that's why I prefer teaching how to automate, opposed to selling bots.

---

## 15. Can you share your PnL?

No, I don't share PnL as I share all of my code on YouTube. I don't want someone to think they can just copy my code and make a million dollars overnight. This is the hardest game in the world and I don't want to attract get rich quickers. This is a long, hard game & most won't make it. You must build your own edge. If everyone runs the same algos, they mathematically will go to 0.

---

## 16. What do I need to download to start coding in python?

Visual Studio Code or Cursor. Cursor is new to me, but it is a copy of Visual Studio Code with AI inside it.

---

## 17. Do you do market orders or limit orders?

I try to use limit orders as much as possible, but some strategies require market orders. I use market orders more often on the close than the open of a trade as most of my bots can wait to enter, but sometimes need to get out in a hurry.

---

## 18. What brokers / exchanges do you use for algo trading?

In the bootcamp I show how to use CCXT which connects to essentially all exchanges.

**→ [full list here](https://github.com/ccxt/ccxt/wiki/Exchange-Markets)**

---

## 19. How do you backtest algos?

I show this process a lot in the bootcamp, but I have landed on using backtesting.py as my favorite backtester. It's a quick way to see if strategies work in the past and be able to see data like ROI, Sharpe, drawdown among many others.

---

## 20. Do you always backtest with commission fee and slippage?

Yes, all backtests include a line of code to allocate a fee, usually 2-3 times higher than the actual exchange fee to account for slippage.

---

## 21. Do you use Mac or PC to algo trade?

I use a MacBook to build everything. It doesn't matter though, you can use Mac or PC.

---

## 22. Do I need an upgraded PC to do algo trading?

No. Virtually any computer, you can code on. Code is light. If you need more power or want to run your algos 24/7 without keeping that computer on, you can simply set up a VPS. Which I show you how to do in the bootcamp, it's super easy. AI can walk you through it too.

---

## 23. Do you have a community?

Yes, we have a free Discord community and a members only one as well for bootcamp members.

**→ [free discord community here](https://discord.gg/gQv5sqZkkn)**

---

## 24. Where do you get data from?

Any of the crypto exchanges, they all give free data. For crypto you can use cryptodatadownload.com, and you can use Yahoo Finance or the yfinance python library for stocks. I also walk you through a couple different ways in the bootcamp.

---

## 25. How can I modify my subscription and get invoices?

You can change, cancel or manage your bootcamp subscription anytime. You can also download invoices there.

**→ [manage subscription here](https://billing.stripe.com/p/login/bIY4h63H89bKdQ4000)**

---

## 26. How can I get in touch with you (Moon Dev)?

The best way is to catch me on a live stream. If it's about business you can send me a short email at moon@algotradecamp.com - I can't get back to everyone, so please pitch short and concisely.

---

## 27. Can you build a bot for me?

Probably not, I code live every day on YouTube so I can show my code to as many people as possible to help them. If you have a project that you'd like to hire me to do & are ok with some of it being shown on YouTube, feel free to email me at moon@algotradecamp.com. I would much rather teach you how to fish, opposed to just giving you a meal. That's why I teach how to automate your trading in the bootcamp.

---

## 28. Can I have a discount?

I've spent nearly 4 years testing & figuring out things. I believe code is the great equalizer so there already is a steep discount. I believe I could sell this bootcamp for 10x the price, minimum. If you really can't afford it, I would suggest checking out the #clips channel in Discord so you can get the bootcamp for free, while learning.

---

## 29. How often is the bootcamp updated?

The bootcamp is updated every time I find something new that helps me. The idea is to constantly share new things I figure out inside of the bootcamp members area. I stream on YouTube every day and work on the hardest problems and then at the end of the week I update the bootcamp. There are usually 2-4 updates per month.

---

## 30. Is the bootcamp for advanced coders only?

No way! I built this bootcamp because I believe code is the great equalizer. I teach you exactly how to code in python, and then teach you how to algo trade. Check out the testimonials, there are students who have never coded before and others who have coded for 10+ years. The bootcamp will save everyone interested in algo trading an unbelievable amount of time.

---

## 31. Can I learn only from your YouTube channel?

Yes, absolutely. I believe code is the great equalizer so every day I create "over the shoulder" type coding videos. I have over 969 hours of coding videos free on my YouTube so you can watch them all and essentially know what I know. That was the whole point of the YouTube channel. Many people kept asking for a course with short and concise videos and all my code, so I launched the algo trade camp but I still want to build the YouTube into the best public good about algo trading.

---

## 32. Why do you teach algo trading?

Because I believe code is the great equalizer. If you learn how to code, you know a language that 99% of the population doesn't. And that language controls the current world, and the future AI world. That language is python, which is a coding language. I spent 10+ years in tech, scared to learn to code. It seemed too hard. After a few failed attempts, I just gave it up until I was faced with an urgent problem - I had success in tech that gave me a nice portfolio to trade, but that trading quickly led me to the realization: me, a human, shouldn't be dealing with these daily emotions and a robot should be trading for me. 4 hours per day and a few months later, I had learned. I also quickly discovered no one shares algo trading info as they don't want to leak their edge. Since it took me 10+ years and a huge problem to get me to learn to code, and seeing the power I now have, being able to build anything I can dream of - I had to fire up a mic and show this to others. I believe in abundance. If you learn to code, you have a skill to build anything and to literally build your future. I wish I would have learned to code earlier.

---

## 33. How did you get started with coding?

I spent multiple years hiring developers to build apps & SaaS for me, thinking I could never code myself. Once I wanted to automate my trading, I knew I had to learn how to code to iterate to success. No one has a profitable bot off the bat, and I knew it would be too costly to iterate to success with a developer. So I started learning how to code in python, 4 hours per day, using free YouTube videos and documentation. The algo trading industry is super secretive though, so there wasn't much info on how to build trading bots so once I understood how, I just started to show literally everything I do on YouTube. I believe code is the great equalizer, and it took me til 30 years old to start the journey of learning to code but now I believe I can build anything in this world. That's why I believe code is the great equalizer, cause if you know how to code, you can build anything for the rest of your life.

---

## 34. Can I have the bootcamp for free?

We have many lengthy videos on our YouTube channel that need concise clips of the key points. To earn free access to the bootcamp, check out the #clips channel in our Discord. There, you can learn how to study our YouTube videos and extract the most valuable segments.

---

## 35. Can I pay for the bootcamp in crypto?

Yes, if you are looking to sign up for the lifetime package. Unfortunately, there is no way to collect subscriptions in crypto so we do lifetime only. You can email moon@algotradecamp.com for the address to send crypto to set up your bootcamp account.

---
