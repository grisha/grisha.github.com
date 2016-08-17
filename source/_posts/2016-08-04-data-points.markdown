---
layout: post
title: "How Data Points Add Up"
date: 2016-08-04 10:35
comments: true
categories:
---

This silly SVG animation (I only learned how to make an SVG animation
this morning) demonstrates what happens when multiple Tgres data
points arrive within the same step (i.e. smallest time interval for
this series).

<object data="/images/data_point.svg" type="image/svg+xml">
  You browser does not support SVG objects?
</object>

### Explanation

Let's say we have a series with a step of 100 seconds. We receive the
following data points, all within the 100 second interval of a
single step:

| Time  | Value |
|-------|-------|
|  25s  | 1.0   |
|  75s  | 3.0   |
| 100s  | 2.0   |
|-------|-------|
| Final:| 2.25  |

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
(recorded as NaN)?

| Time  | Value |
|-------|-------|
|  25s  | NaN   |
|  75s  | 3.0   |
| 100s  | 2.0   |
|-------|-------|
| Final:| 2.667 |

<p/>
Then the total for this data point is 2.666666666. Or 2.67.

But wait a second... 0.50 &times; 3 + 0.25 &times; 2 = 2.0 ? Where did
2.67 come from?

The reason for this is that NaN ought not be influencing the
value. The above calculation would only be correct if we assumed that NaN is
synonymous with zero, but that would be a false assumption, as NaN
means "we do not know".

Therefore, we must "pretend" that the data point is smaller, i.e. 75s
long, or 3/4 the original size. Thus to get the final value we must
divide the result 2.0 by 3/4, yielding 2.67.

<object data="/images/data_point_unk.svg" type="image/svg+xml">
  You browser does not support SVG objects?
</object>
