---
layout: post
title: "Why is there no Formal Definition of Time Series?"
date: 2016-12-23 09:13
comments: true
categories:
---

If you're reading this, chances are you may have searched for
definition of "Time Series". And, like me, you were probably
disappointed by what you've found.

The most popular "definition" I come across amongst our fellow
programmer folk is that it's "data points with timestamps". Or something
like that. And you can make charts from it. And that's about it, alas.

The word _time_ suggests that is has something to do with time. At
first it seems reasonable, I bite. The word _series_ is a little more
peculiar. A mathematician would argue that a series is a [_sum_ of a sequence](https://en.wikipedia.org/wiki/Series_(mathematics)).
Most people though think "series" and "sequence" are the
same thing, and that's fine. But it's a clue that _time series_ is
not a scientific term, because it would have been called
_time sequence_ most likely.

Lets get back to the time aspect of it. Why do data points need
timestamps? Or do they? Isn't it the time _interval_ between points
that is most essential, rather than the absolute time? And if the data
points are spaced equally (which conforms to the most common definiton
of time series), then what purpose would _any_ time-related
information attached to a data point serve?

To understand this better, picture a time chart. Of anything -
temperature, price of bitcoin over a week, whatever. Now think - does
the absolute time of every point provide any useful information to
you? Does the essential meaning of the chart change depending on
whether it shows the price of bitcoin in the year 2016 or 2098 or
10923?

Doesn't it seem like "time" in "time series" is a bit of a red
herring?

Here is another example. Let's say I decide to travel from
San-Francisco to New York taking measurements of elevation above the
sea level at every mile. I then plot that sequence on a chart where
x-axis is distance traveled and y-axis is elevation. You would agree
that this chart is not a "time series" by any stretch, right? But then
if I renamed x-axis to "time traveled" (let's assume I moved at
constant speed), the chart wouldn't change at all, but now it's okay
to call it "time series"?

So it's no surprise that there is no formal definition of "time
series".  In the end a "time series" is just a _sequence_. There are
no timestamps required and there is nothing at all special regarding a
dimension being time as opposed to any other unit, which is why there
is no mathematical definition of "time series". Time series is a
colloquial term etymological origins of which are not known to me, but
it's not a thing from a scientific perspective, I'm afraid.

Next time you hear "time series" just substitute it with "sequence" and
see how much sense that makes. For example a "time series database" is
a "sequence database", i.e. database optimized for sequences. Aren't
all relational databases optimized for sequences?

Something to think about over the holidays...

Edit: Someone brought up the subject of [_unevenly-spaced time series_](https://en.wikipedia.org/wiki/Unevenly_spaced_time_series).
All series are evenly spaced given proper resolution. An
unevenly-spaced time series with timestamps accurate to 1 millisecond
is a sparse evenly-spaced series with a 1 millisecond resolution.
