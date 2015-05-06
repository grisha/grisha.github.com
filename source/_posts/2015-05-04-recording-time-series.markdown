---
layout: post
title: "Time Series Accuracy - Graphite vs RRDTool"
date: 2015-05-04 17:40
comments: true
categories:
---

Back in my ISP days, we used data stored in RRDs to bill our
customers. I wouldn't try this with Graphite. In this write up I try
to explain why it is so by comparing the method of recording time series
used by
[Graphite](http://graphite.readthedocs.org/en/latest/overview.html),
with the one used by [RRDTool](https://oss.oetiker.ch/rrdtool/).

Graphite uses
[Whisper](http://graphite.wikidot.com/whisper) to store data, which in
the FAQ is portrayed as a [better alternative](http://graphite.wikidot.com/whisper#toc1) to RRDTool, but
this is potentially misleading, because the flexibility afforded by the
design of Whisper comes at the price of inaccuracy.

A time series is most often described as a sequence of `(time, value)`
tuples [1]. The most naive method of recording a time series is to
store timestamps as is. Since the data points might arrive at
arbitrary and inexact intervals, to correlate the series with a
particular point in time might be tricky. If data points are arriving
somewhere in between one minute bounaries (as they always naturally
would), to answer the question of what happened during a particular
minute would require specifying a range, which is not as clean as
being able to specify a precise value. To join two series on a range
is even more problematic.

One way to improve upon this is to divide time into equal intervals
and assign data points to the intervals. We could then use the
beginning of the interval instead of the actual data point timestamp,
thereby giving us more uniformity. For example, if our interval size
is 10 seconds (I may sometimes refer to it as the _step_), we could
divide the entire timeline starting from the
[beginning of the epoch](http://en.wikipedia.org/wiki/Unix_time)
and until the end of
universe into 10 second slots. Since the first slot begins at 0, any
10-second-step time series will have slots starting at the exact same
times. Now correlation across series or other time values becomes much
easier.

Calculating the slot is trivially easy: `time - time % step` (`%` being
the [modulo operator](https://docs.python.org/3.4/reference/expressions.html#index-51)).
There is, however, a subtle complexity lurking when it comes to
storing the datapoint with the adjusted (or _aligned_) timestamp.
Graphite simply changes the timestamp of the data point to the
aligned one. If multiple data points arrive in the same
step, then the last one "wins".

On the surface there is little wrong with Graphite's approach. In fact,
under right circumstances, there is absolutely nothing wrong with
it. Consider the following example:

```
Graphite, 10 second step.

Actual Time   Aligned Time
1430701282    1430701280     50  <-- This data point is lost
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
of them? In this scenario having the last value override all previous
ones doesn't exactly seem correct.

Enter RRDTool which uses a different method. RRDTool keeps track of
the last timestamp and calculates a weight for every incoming
data point based on time since last update or beginning of the step and
the step length. Here is what the same sequence of points looks like
in RRDTool. The lines marked with a `*` are not actual data points,
but are the last value for the preceding step, it's used for
computing the value for the remainder of the step after a new one has
begun.

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

Note, by the way, that the Whisper FAQ says that "RRD will store your
updates in a temporary workspace area and after the minute has passed,
aggregate them and store them in the archive", which to me sounds like
there is some sort of a temporary storage area holding all the unsaved
updates. In fact, to be able to compute the weighted average, RRD only
needs to store the time of the last update and the current sum, i.e.
exactly just two variables, regardless of the number of updates in a
single step. This is evident from the above figure.

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
trinkets from our website (per second). Here is a horizontal ascii-art
rendition of our timeline, 0 is 1430701270.

```
0         10        20        30    time (seconds)
+.........+.........+.........+.....
|           |     |    |       |
0           50    10   30      30   data points
```

At 12 seconds we recorded selling 50 trinkets per second. Assuming we
started selling at the beginning of our timeline, i.e. 12 seconds
earlier, we can state that during the first step we sold exactly 500
trinkets. Then 2 seconds into the second step we sold another 100
(we're still selling at 50/s). Then for the next 6 seconds we were
selling at 10/s, thus another 60 trinkets, and for the last 2 seconds
of the slot we sold another 60 at 30/s. In the third step we were
selling steadily at 30/s, thus exactly 300 were sold.

Comparing RRDTool and Graphite side-by-side, the stories are quite different:

```
Trinkets per second and sold:
   Time Slot     Graphite Trinkets     RRDTool Trinkets
1. 1430701270      N/A      N/A          50      500
2. 1430701280       10      100          22      220 (100+60+60)
3. 1430701290       30      300          30      300
4. 1430701300       30      N/A          N/A     N/A
                          -----                -----
   TOTAL SOLD:              400                 1020

```

Two important observations here:

1. The totals are vastly different.
1. The rate recorded by RRDTool for the second slot (22/s), yields
   _exactly_ the number of trinkets sold during that period: 220.

Last, but hardly the least, consider what happens when we consolidate
data points into larger intervals by averaging the values. Let's say
20 seconds, twice our step. If we consolidate the second and the third
steps, we would get:

```
Graphite:  average(10,30) = 20  => 400 trinkets in 20 seconds
RRDTool:   average(22,30) = 26  => 520 trinkets in 20 seconds
```

Since the Graphite numbers were off to begin with, we have no reason
to trust the 400 trinkets number. But using the RRDTool data, the new
number happens to still be 100% accurate even after the data points
have been consolidated. This is a very useful property of _rates_ in
time series. It also explains why RRDTool does not permit updating
data prior to the last update: RRD is _always accurate_.

As an exercise, try seeing it for yourself: pretent the value of 10 in
the second step never arrived, which should make the final value of
the second slot 34. If the 10 arrived some time later, averaging it in
will not give you the correct 22.

Whisper allows past updates, but is quasi-accurate to begin with - I'm
not sure I understand which is better - _inaccurate_ data with a data
point missing, or the _whole inaccurate_ data. RRD could accomplish
the same thing by adding some `--inaccurate` flag, though it would
seem like more of a bug than a feature to me.

If you're interested in learning more about this, I recommend reading
the documentation for
[rrdtool create](http://oss.oetiker.ch/rrdtool/doc/rrdcreate.en.html), in
particular the "It's always a Rate" section, as well as
[this post](http://www.vandenbogaerdt.nl/rrdtool/process.php)
by Alex van den Bogaerdt.

P.S. After this post was written, someone suggested that instead of
storing a rate, we coud store a _count delta_. In other words, instead
of recording that we're selling 10 trinkets per second for the past 6
seconds, we would store the total count of trinkets sold, i.e. 60. At
first this seems like the solution to being able to update historical
data accurately: if later we found out that we sold another 75
trinkets in the second time slot, we could just add it to the total
and all would be well and most importantly _accurate_.

Here is the problem with this approach: note that in the previous
sentence I had to specify that the additional trinkets were sold _in
the second time slot_, a small, but crucial detail. If time series
data point is a timestamp and a value, then there isn't even a way to
relay this information in a single data point - we'd need two
timestamps. On the other hand if every data point arrived with two
timestamps, i.e. as a duration, then which to store, rate or count,
becomes a moot point, we can infer one from the other.

So perhaps another way of explaining the historical update problem is
that it *is* possible, but the datapoint must specify a _time
interval_. This is something that neither RRDTool or Graphite authors
have considered (or any other tool I know of, for that matter).

[1] Perhaps the biggest misconception about time series is that it is
a series of data points. What time series represent is _continuous_
rather than _descrete_, i.e. it's the line that connects the points
that matters, not the specific points themselves, they are just
samples at semi-random intervals that help define the line.
