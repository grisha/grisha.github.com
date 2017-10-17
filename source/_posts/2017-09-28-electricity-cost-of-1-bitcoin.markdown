---
layout: post
title: "Electricity cost of 1 Bitcoin (Sep 2017)"
date: 2017-09-28 16:38
comments: true
published: true
categories:
---

How much does it cost in electricity to mine a Bitcoin?

As of Sep 28, 2017, according to blockchain.info the hashrate is:
9,214,860,125 GH/s.

These days it seems that the best miner available for sale is the
AntMiner S9. It is actually over a year old, and there are faster and
more energy efficient ASICs now, e.g. BitFury, but it is very hard to
get any information on those, so we will just use the S9 information.

The S9 is capable of 12,930 GH/s. The collective Bitcoin hash rate is
equivalent to 712,672 S9 miners running in parallel.

An S9 uses 1375W, which means that in 1 hour it consumes 1.375 kW/h.

In USA, a kWh costs $0.12 on average. (It can be
as low as 0.04, according to this [EIA chart](https://www.eia.gov/electricity/monthly/epm_table_grapher.php?t=epmt_5_6_a).)

At 12c per kWh a running S9 costs $0.165 per hour.

712,672 running S9's would cost $117,591.02 per hour.

Bitcoin blocks are solved at 6 per hour on average. Thus, each block
costs $19,598.50 to solve.

The current mining reward is 12.5 BTC, which gives us the answer:

At \\$0.12 kW/h a Bitcoin costs \\$1,567.88 to mine.

At \\$0.04 kW/h a Bitcoin costs \\$522.62 to mine.

This, of course, does not include hardware and other costs.

It's quite likely that the largest mining operations pay even less
than $0.04 for electricity and the hardware they use is many times
more efficient.

While grosly inaccurate, this shows that mining is quite profitable,
and that Bitcoin price would have to fall a lot for mining to stop
being profitable.

### Looking at the Trend ###

Current difficulty is 1103400932964, The difficulty before that was
922724699725.

Difficulty adjusts every 2,016 blocks, which is about two weeks.

The Difficulty number is a coefficient of the "difficulty 1 target",
i.e. where the hash has to begin with 4 zero bytes (32 zero bits). It
means is that it is N times harder than "1 target".

We can see that at the last adjustment it went up by 180,676,233,239,
or 16%, which is quite a bit in just two weeks. The last adjustment
before that was from 888171856257, or 4%.

Assuming that the only miner in the world was the S9, the difficulty
adjustment can only be explained by more S9's coming online. The
number of S9's online is directly proportional to the hashrate, which
is directly proportional to the difficulty. Thus there is a direct
relationship between energy cost and the difficulty.

When the difficulty was 922724699725 (Sep 6 through 16), the hash rate
was at about 8,000,000 TH/s, or equivalent of 618,716 S9's. At that
difficulty and the 12c kW/h price, a BTC cost $1,361 to mine.

Now let's look back at the world before the S9, which uses the Bitmain
BM1387 16nm ASIC. Before the S9, there was S7, based on BitMain BM1385
28nm ASIC. The S7 power consumption is roughly same as S9, or let's
assume it is for simplicity, but it is only capable of 4,000 GH/s.

Back at the end of 2015 when S7 was announced, the hashrate was at
around 700,000,000 GH/s, or equivalent to 175,000 S7's. That cost
\\$28,875 per hour, or \\$4,812.5 per block. The block reward was 25
Bitcoins then, so a Bitcoin would cost only \\$192 to mine. (With a 12.5
reward it would have been \\$385).

This is all very confusing, but we can see that faster hardware and
more of it drives the cost of mining up and the rlationship between
the difficulty and the cost of mining a Bitcoin is linear. Faster
hardware enables higher hash rate at improved energy efficiency, and
the difficulty adjusts to keep the rate of blocks and supply of new
BTC at 10 minutes.

The cost factor behind Bitcoin is energy, and spending more energy on
mining makes a Bitcoin more expensive and less profitable. However, a
more energy-expensive Bitcoin is a more sound/secure Bitcoin from the
cryptographic perspective, which means it is likely to go up in USD
price, and thus should still be profitable for the miners. This is a
very interesting factor here, because if the BTC/USD price wasn't
going up, the miners would be bitter enemies and would do everything
possible to prevent more miners from coming online. The rise of the
BTC/USD price is what justifies as positive more miners coming
online. So far we have not seen any news reports of mining facilities
being sabotaged, which probably means miners are not enemies.

I will need to think on this some more as there are a lot of moving
parts. But if I can make a cursory conclusion here, it is that
(industrial) mining is and will remain very profitable for some time.
