---
layout: post
title: "Storing Time Series in PostgreSQL (Continued)"
date: 2016-12-16 19:35
comments: true
categories:
---

Edit: there is now a [part iii](/blog/2017/01/21/storing-time-seris-in-postgresql-optimize-for-write) in this series of articles.

I have [previously written](/blog/2015/09/23/storing-time-series-in-postgresql-efficiently/) how
time series can be stored in PostgreSQL efficiently using [arrays](https://www.postgresql.org/docs/current/static/arrays.html).

As a continuation of that article, I shall attempt to describe in detail the inner workings of an
[SQL view](https://en.wikipedia.org/wiki/View_(SQL)) that [Tgres](https://github.com/tgres/tgres) uses to
make an array of numbers appear as a regular table
([link to code](https://github.com/tgres/tgres/blob/bc718e3999650b7aab934517179ea47632530d28/serde/postgres.go#L235-L242)).

In short, I will explain how incomprehensible data like this:

{% codeblock lang:sql %}
=> select * from ts;
 rra_id | n |           dp
--------+---+------------------------
      1 | 0 | {64,67,70,71,72,69,67}
      1 | 1 | {65,60,58,59,62,68,70}
      1 | 2 | {71,72,77,70,71,73,75}
      1 | 3 | {79,82,90,69,75,80,81}
{% endcodeblock %}

... can be transformed in an SQL view to appear as so:

{% codeblock lang:sql %}
=> select * from tv order by t;
 rra_id |           t            | r
--------+------------------------+----
      1 | 2008-03-06 00:00:00+00 | 64
      1 | 2008-03-07 00:00:00+00 | 67
      1 | 2008-03-08 00:00:00+00 | 70
      1 | 2008-03-09 00:00:00+00 | 71
...
{% endcodeblock %}

This write up will make a lot more sense if you read the
[previous post](/blog/2015/09/23/storing-time-series-in-postgresql-efficiently/) first.
To recap, Tgres stores series in an array broken up over multiple
table rows each containing an array representing a segment of the
series. The series array is a round-robin structure, which means
that it occupies a fixed amount of space and we do not need to worry
about expiring data points: the round-robin nature of the array
takes care of it by overwriting old data with new on assignment.

An additional benefit of such a fixed interval round-robin structure
is that we do not need to store timestamps for every data point. If we
know the timestamp of the latest entry along with the series step and size,
we can extrapolate the timestamp of any point in the series.

Tgres creates an SQL view which takes care of this extrapolation and
makes this data easy to query. Tgres actually uses this view as its
only source of time series information when reading from the database
thus delegating all the processing to the database server, where it is
close to the data and most efficient.

If you would like to follow along on the Postgres command line, feel
free to create and populate the tables with the following SQL, which
is nearly identical to the schema used by Tgres:

{% codeblock lang:sql %}
CREATE TABLE rra (
  id SERIAL NOT NULL PRIMARY KEY,
  step_s INT NOT NULL,
  steps_per_row INT NOT NULL,
  size INT NOT NULL,
  width INT NOT NULL,
  latest TIMESTAMPTZ DEFAULT NULL);

CREATE TABLE ts (
  rra_id INT NOT NULL,
  n INT NOT NULL,
  dp DOUBLE PRECISION[] NOT NULL DEFAULT '{}');

INSERT INTO rra VALUES (1, 60, 1440, 28, 7, '2008-04-02 00:00:00-00');

INSERT INTO ts VALUES (1, 0, '{64,67,70,71,72,69,67}');
INSERT INTO ts VALUES (1, 1, '{65,60,58,59,62,68,70}');
INSERT INTO ts VALUES (1, 2, '{71,72,77,70,71,73,75}');
INSERT INTO ts VALUES (1, 3, '{79,82,90,69,75,80,81}');
{% endcodeblock %}

And finally create the view:

{% codeblock lang:sql %}
CREATE VIEW tv AS
  SELECT rra.id rra_id,
         latest - INTERVAL '1 SECOND' * rra.step_s * rra.steps_per_row *
           MOD(rra.size + MOD(EXTRACT(EPOCH FROM rra.latest)::BIGINT/(rra.step_s * rra.steps_per_row), size) + 1
           - (generate_subscripts(dp,1) + n * width), rra.size) AS t,
         UNNEST(dp) AS r
    FROM rra
   INNER JOIN ts ts ON ts.rra_id = rra.id;
{% endcodeblock %}

Now give it a whirl with a `SELECT * FROM tv ORDER BY t`. Impressive? So how does it work?

First let's go over the columns of the rra table.

* `step_s`: the minimal unit of time expressed in seconds (60 or 1 minute in the above data).
* `steps_per_row`: the number of the `step_s` intervals in one slot of our time series.
   In our example it is 1440, which is the number of minutes in a day, thus making our time series
   resolution _one day_.
* `size`: number of slots in the series. Ours is 28, i.e. four weeks.
* `width`: size of a segment which will be stored in a single row, which in our case
   is 7 (one week).
* `latest`: the timestamp of the last data point in the series.

Next, let's look at the `UNNEST` keyword in the SQL of the view. `UNNEST` takes an array and turns it into row, e.g.:

{% codeblock lang:sql %}
=> SELECT UNNEST(dp) AS r FROM ts;
 r
----
 64
 67
...
{% endcodeblock %}

`UNNEST` works in conjunction with the `generate_subscripts`
PostgreSQL function which generates index values:

{% codeblock lang:sql %}
=> SELECT generate_subscripts(dp,1) AS i, UNNEST(dp) AS r FROM ts;
 i | r
---+----
 1 | 64
 2 | 67
...
{% endcodeblock %}

Let us now zoom in on the very long expression in the view, here it is again:

{% codeblock lang:sql %}
latest - INTERVAL '1 SECOND' * rra.step_s * rra.steps_per_row *
  MOD(rra.size + MOD(EXTRACT(EPOCH FROM rra.latest)::BIGINT/(rra.step_s * rra.steps_per_row), size) + 1
  - (generate_subscripts(dp,1) + n * width), rra.size) AS t
{% endcodeblock %}

A perhaps not immediately apparent trick to how all this works is that all
our series are aligned
on the [beginning of the epoch](https://en.wikipedia.org/wiki/Unix_time).
This means that at UNIX time 0, any series' slot index is 0. From then on it
increments sequentially until the series size is reached, at which point
it wraps-around to 0 (thus "round-robin"). Armed with this information we
can calculate the index for any point in time.

The formula for calculating the index `i` for a given time `t` is:
{% codeblock lang:python %}
i = t/step % size.
{% endcodeblock %}

We need time to be expressed as a UNIX time which is done
with `EXTRACT(EPOCH FROM rra.latest)::BIGINT`. Now you should recognize
the above formula in the more verbose expression
{% codeblock lang:sql %}
MOD(EXTRACT(EPOCH FROM rra.latest)::BIGINT/(rra.step_s * rra.steps_per_row), size)
{% endcodeblock %}
where `rra.step_s * rra.steps_per_row` is the size of our series in seconds.

Next, we need to compute the _distance_ between the current slot and the
last slot (for which we know the timestamp). I.e. if the last slot is `i` and the slot we need the
timestamp for is `j`, the distance between them is `i-j`, but with a
caveat: it is possible for `j` to be greater than `i` if the series
wraps around, in which case the distance is the sum of the distance from
`j` to the end of the series and the distance from the beginning to
`i`. If you ponder over it with a pencil and paper long enough, you
will arrive at the following formula for distance between two slots
`i` and `j` in a wrap-around array:

{% codeblock lang:python %}
distance = (size + i - j) % size
{% endcodeblock %}

Another thing to consider is that we're splitting our series across
multiple rows, thus the actual index of any point is the subscript
into the current segment plus the index of the segment itself (the `n`
column) multiplied by the `wdith` of the segment: `generate_subscripts(dp,1) + n * width`.

Which pieced together in SQL now looks like this:

{% codeblock lang:sql %}
MOD(rra.size + MOD(EXTRACT(EPOCH FROM rra.latest)::BIGINT/(rra.step_s * rra.steps_per_row), size) + 1
  - (generate_subscripts(dp,1) + n * width), rra.size)
{% endcodeblock %}

Astute readers should notice an unexplained `+ 1`. This is because
PostgreSQL arrays are 1-based.

Now we need to convert the distance expressed in array slots into
a time interval, which we do by multiplying it by
`INTERVAL '1 SECOND' * rra.step_s * rra.steps_per_row`.

And finally, we need to subtract the above time interval from the
latest stamp which yields (ta-da!) the timestamp of the current slot:

{% codeblock lang:sql %}
latest - INTERVAL '1 SECOND' * rra.step_s * rra.steps_per_row *
  MOD(rra.size + MOD(EXTRACT(EPOCH FROM rra.latest)::BIGINT/(rra.step_s * rra.steps_per_row), size) + 1
  - (generate_subscripts(dp,1) + n * width), rra.size) AS t
{% endcodeblock %}

That's it! And even though this may look complicated, from the
computational view point it is very efficient, and PostgreSQL can
handle it easily.

As an exercise, try setting `latest` to various timestamps and observe
how it affects the output of the view and see if you can explain how
and why it happens.
