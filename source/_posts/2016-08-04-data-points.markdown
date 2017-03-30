---
layout: post
title: "How Data Points Build Up"
date: 2016-08-04 10:35
comments: true
categories:
---

This silly SVG animation (animation not my strong suit) demonstrates
what happens when multiple Tgres data points arrive within the same
step (i.e. smallest time interval for this series, also known as PDP,
primary data point).

<object data="/images/data_point.svg" type="image/svg+xml">
  You browser does not support SVG objects?
</object>

### Explanation

Let's say we have a series with a step of 100 seconds. We receive the
following data points, all within the 100 second interval of a
single step:

| Time  | Value | Recorded |
|-------|-------|----------|
|  25s  | 2.0   | 0.5      |
|  75s  | 3.0   | 2.0      |
| 100s  | 1.0   | 2.25     |
|-------|-------|----------|
|       | Final:| 2.25     |

<p/> Tgres will store 2.25 as the final value for this step. So how
does 1, 2 and 3 add up to _2.25_?

One way to think about it is that the incomplete step is an empty
swimming pool as wide as 1 step, into which we dump blocks of
water. The first data point dumps a 2.0 &times; 0.25 block of water, which
fills the pool to 0.5. The second data point dumps a 3.0 &times; 0.50 block,
which raises the water another 1.5 to 2.0. The last data point dumps a
1.0 &times; 0.25 block which raises it to the final value of 2.25.  Compare
this with Graphite which would simply discard the first two data
points and we are left with 1.0 as the final value.

Why is it done this way? Because this is how rates add up. If this was
speed of a car in meters per second (more like a bycicle, I guess),
its weighted average speed for the duration of this step of 2.25
meters per second would mean that in the 100s it would have traveled
exactly 225 meters.

### NaNs or "Unknowns"

What if instead of the first data point, the first 25s were "unknown"
(recorded as NaN)? This would happen, for example, if the series
heartbeat (maximum duration without any data) was exceeded. Even
though the data point has a value of 2.0, it gets recorded as NaN.

| Time  | Value | Recorded |
|-------|-------|----------|
|  25s  | 2.0   | NaN      |
|  75s  | 3.0   | 2.0      |
| 100s  | 1.0   | 2.33     |
|-------|-------|----------|
|       | Final:| 2.33     |

<p/>
But wait a second... 0.50 &times; 3 + 0.25 &times; 1 = 1.75 ? Where did
the value of 2.33 come from?

The reason for this is that NaN ought not be influencing the
value. The above calculation would only be correct if we assumed that NaN is
synonymous with zero, but that would be a false assumption, as NaN
means "we do not know".

Therefore, we must only consider the known part of the data point,
which is 75s. We can think of it that the data point (the "swimming
pool") just got smaller.  Thus the correct calculation for the 3.0
point would be 3.0 &times; 50 &divide; 75 = 2.0 and for the 1.0 point
2.0 + 1.0 &times; 25 &divide; 75 = 2.33.

Here it is in SVG:

<object data="/images/data_point_unk.svg" type="image/svg+xml">
  You browser does not support SVG objects?
</object>

Also note how the value of the data point which was recorded as NaN
(2.0 in our example) is essentially irrelevant. This is because any
calculation with a NaN always results in a NaN. The only thing we know
about this data point is that it was not NaN and that it marked the
end of period recorded as NaN. The next data point after this (3.0 in
our example) is not affected by the NaN, however, this is because it
in effect starts its own data point afresh, not considering anything
in the past.
