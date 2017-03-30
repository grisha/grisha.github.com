---
layout: post
title: "Load testing Tgres"
date: 2016-11-08 14:41
comments: true
categories:
---

Edit: There is an [update](/blog/2017/02/23/can-tgres-outperform-graphite/) to this story.

So I finally got around to some load testing of [Tgres](https://github.com/tgres/tgres). Load testing is
mysterious, it never goes the way you think it would, and what you
learn is completely unexpcted.

Given that I presently don't have any spare big iron at my disposal
and my "servers" are my macbook and an old thinkpad, all I really was
after is making sure that Tgres is "good enough" whatever that
means. And I think it is.

I was hoping to gather some concrete numbers and may be even make a
chart or two, but in the end it all turned out to be so tedious and
time consuming, running the tests with various setting for hours on,
that I just gave up for now - after all, "premature optimization is
the root of all evil".

I also wanted to see how it stacks up against Graphite
carbon-cache.py. As in, is it on par, or much better or much worse. My
expectation was that Graphite could outperform it, because what it
does is so much simpler (and I was right). First thing I tried to do
is overwhelm Graphite. I never succeeded in that - I probably could
have tried harder, but I quickly learned that I don't know what
symptoms I'm looking for. I wronte a Go program that blasted UDP data
points at 10K/sec across 10K different series, and taking it to over
20K/sec saturated my network before Graphite showed any signs of
deterioration. There was also no reliable way for me to audit the data
points - may be some of them got lost, but at 600K+ per minute, I
don't know of any practical way of doing it. Not without a lot of
work, at least.

With Tgres things were much easier. The weakest link is, not
surpisingly, PostgreSQL. What I learned was that there are two kinds of
deterioration when it comes to PostgreSQL though. The first one is
outright, and that one manifests in database requests getting
progressively slower until Tgres gets stuck with all its channels
full.

You can make PostgreSQL very significantly faster with a few simple
tricks. For example the following settings can make it much faster:

```
synchronous_commit = off
commit_delay = 100000
```

This post isn't about PostgreSQL, and so I'm not going to get into the
details of what this does, there is plenty of documentation and blog
posts on the subject. If you plan on hosting a busy Tgres set up, you
should probably have the above settings.

The second way PostgreSQL deteriorates is not immediately apparent - it
is the infamous table bloat. Getting autovacuum to keep up with the ts
table (which stores all the time series) is tricky, and once you've
ran out of options to tweak, this is probably it - the maximum load
the database can handle, even if it may seem relatively calm.

Autovacuum has a lot of knobs, but ultimately they all exist to take
advantage of the variability of load in a database, i.e. you can let
it get behind during the day and catch up at night when the database
is not as busy. It doesn't really work with time series, which are not
variable by nature - if you're receiving 5 thousand data points per
second at noon, you can expect the same rate at 4am. I think the
setting that worked best for me were:

```
autovacuum_max_workers = 10
autovacuum_naptime = 1s
autovacuum_vacuum_threshold = 2000
autovacuum_vacuum_scale_factor = 0.0
autovacuum_vacuum_cost_delay = 0 # disable cost based

```

To the best of my undestanding the above setting disables cost-based
autovacuum (meaning it doesn't pause periodically to yield resources
to the normal db tasks), makes autovacuum kick in after 2K updates
(which happens in no time), and sleeps 1s in between runs, which means
it's running pretty much continuosly.

I was able to sustain a load of ~6K datapoints per second across 6K
series - anything higher caused my "database server" (which is a 2010
i7 Thinkpad) autovacuum to get behind.

I also did some testing of how TOAST affects performance. There is no
setting for turning TOAST on or off, but it can easily be done in
Tgres by changing the number of data points per row. The default is
768 which is about 75% of a page. If you for example double it, then
each row becomes larger than a page and TOAST kicks in. TOAST is
compressed, which is an advantage, but it is a separate table, which
is a disadvantage. In the end it seemed like the database detirorated
quicker with TOAST, but it was rather inconclusive.

In the end the key factor, or the weakest link, was the rate of
queries per second. I now added a special rate limiting setting
feature to Tgres (max-flushes-per-second) which trumps all other
settings and will keep your database happy at the expense of Tgres
possibly caching a little more points in memory than expected.

I will probably get back to some more load testing in a while, but for
now this is it.
