---
layout: post
title: "Recording Time Series"
date: 2015-05-04 17:40
comments: true
categories:
---

Different tools record Time Series in different ways, this write up
focuses on different methods and the implications.

A time series is simply a sequence of `(time, value)` tuples. The most
naive method of recording a time series is to store timestamps as
is.

Since the data points might arrive at arbitrary intervals, to
correlate the series with a particular point in time might be tricky.
One way to improve upon this is to divide time into intervals of a
particular size and assign datapoints to the intervals.

For example, if our interval size is 10 seconds (I may sometimes refer
to it as the _step_), we could divide the entire timeline starting
from the [beginning of the epoch](http://en.wikipedia.org/wiki/Unix_time) and until the end of
universe into 10 second slots. Since the first slot begins at 0, any
10-second-step time series will have slots starting at the exact
same time. Now correlation across series or other time values becomes
much easier.

Calculating the slot is trivially easy: `time % step` (`%` being
[modulo operator](https://docs.python.org/3.4/reference/expressions.html#index-51)).
But there is a complex subtelty lurking when it comes to assigning data points to slot.

[Graphite](http://graphite.readthedocs.org/en/latest/overview.html),
for example, just changes the timestamp of the datapoint to the
beginning of the slot.  If multiple data points arrive in the same
step, then the last one "wins".

On the surface there is little wrong with this approach. In fact,
under right circumstances, there is absolutely nothing wrong with
it. Consider the following example:

```
Graphite, 10 second step.

Actual Time   Adjuste Time
1430701282    1430701280     50  <-- This datapoint is lost
1430701288    1430701280     10
1430701293    1430701290     30
1430701301    1430701300     30
```

Let's pretend those values are some system metric like the number of
files open. The consequnce of the 50 being dropped is that we will
never know it existed, but towards the end of the 10 second interval
it went down to 10, which is still a true fact. If we really wanted to
know about the variations within a 10 second interval, we should have
chosen a smaller step, e.g. 1 second. By deciding that the step is
going to be 10 seconds, we thus declared that _variations within a
smaller period are of no interest_ to us, and from this perspective,
Graphite _is correct_.

But what if those numbers are the price of a stock. There may be
hundreds of thousand of trades within a 10 second interval, yet we do
not want to (or cannot, for technical reasons) record every single one
of them. In this scenario having the last value override all previous
ones doesn't exactly seem correct.

Enter [RRDTool](https://oss.oetiker.ch/rrdtool/) which uses a
different method. RRDTool keeps track of the last timestamp and
calculates a weight for every incoming datapoint based on time since
last update or beginning of the step and the step length. Here is what
the same sequence of points looks like in RRDTool. The lines marked
with a `*` are not actual data points, but are the last value for the
preceeding step, it's used for computing the value for the remainder
of the step after a new one has begun.

```
RRDTool, 10 second step.

  Time          Value       Time since  Weight  Adjusted   Recorded
                            last                value      value
  1430701270    0           N/A
* 1430701280    50         10s          1       50* 1= 50
                                                           50
  1430701282    50          2s          .2      50*.2= 10
  1430701288    10          6s          .6      10*.6= 6
* 1430701290    30          2s          .2      30*.2= 6
                                                           10+6+6= 22
  1430701293    30          3s          .3      30*.3= 9
* 1430701300    30          7s          .7      30*.7= 21
                                                           9+21=   30
  1430701301    30   # this data point is incomplete
```

So to compare the results of the two tools:

```
Time Slot     Graphite    RRDTool
1430701270       N/A        50
1430701280       10         22
1430701290       30         30
1430701300       N/A        N/A

```

Before you say "so what, I don't really understand the difference",
let's pretend that those numbers were actually the rate of sale of
trinkets from our website (per second).

At 1430701282 we recorded selling 50 trinkets per second. Assuming we
started selling at the beginning of our timeline, i.e. 12 seconds
earlier, we can state that during the first step we sold exactly 500
trinkets. Then 2 seconds into the second step we sold another 100
(we're still selling at 50/s). Then for the next 6 seconds we were
selling at 10/s, thus another 60 trinkets, and for the last 2 seconds
of the slot we sold another 60 at 30/s. In the third step we were
selling steadily at 30/s, thus exactly 300 were sold. But according to
Graphite, the story is different:

```
Trinkets per second:
   Time Slot     Graphite Trinkets     RRDTool Trinkets
1. 1430701270      N/A      N/A          50      500
2. 1430701280       10      100          22      220 (100+60+60)
3. 1430701290       30      300          30      300
4. 1430701300       30      N/A          N/A     N/A
                          -----                -----
   TOTAL:                   400                 1020

```

Two important observations here:

1. The totals are vastly different.
1. The rate recorded by RRDTool for the second slot (22/s), yields
   exactly the number of trinkets sold during that period: 220.

Last, but hardly the least, consider what happens when we consolidate
data points into larger intervals by averaging the values. Let's say
20 seconds, twice our step. If we consolidate the second and the third
steps, we would get:

```
Graphite:  average(10,30) = 20  => 400 trinkets in 20 seconds
RRDTool:   average(22,30) = 26  => 520 trinkets in 20 seconds
```

Since the Graphite numbers were off to begin with, we have no reason
to trust the 400 trinkets number. But using the RRDTool, the new
number happens to still be 100% accurate even after the data points
have been consolidated. This is a very useful property of rates in
time series..

If you're interested in learning more about this, I recommend reading
the documentation for [rrdtool
create](http://oss.oetiker.ch/rrdtool/doc/rrdcreate.en.html), in
particular the "It's always a Rate" section, as well as [this post](http://www.vandenbogaerdt.nl/rrdtool/process.php)
by Alex van den Bogaerdt.
