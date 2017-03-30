---
layout: post
title: "Storing Time Series in PostgreSQL - Optimize for Write"
date: 2017-01-21 09:33
comments: true
published: true
categories:
---

Continuing on the
[previous](/blog/2016/12/16/storing-time-series-in-postgresql-part-ii/)
write up on how time series data can be stored in Postgres
efficiently, here is another approach, this time providing for extreme
write performance.

The "horizontal" data structure in the last article requires an SQL
statement for every data point update. If you cache data points long
enough, you might be able to collect a bunch for a series and write
them out at once for a slight performance advantage. But there is no
way to update multiple series with a single statement, it's always
at least one update per series. With a large number of series, this
can become a performance bottleneck. Can we do better?

One observation we can make about incoming time series data is that
commonly the data points are roughly from the same time period, the
current time, give or take. If we're storing data at regularly-spaced
intervals, then it is extremely likely that many if not all of the
most current data points from various time series are going to belong
to the exact same time slot. Considering this observation, what if we
organized data points in rows of arrays, only now we would have a row
per timestamp while the position within the array would determine the
series?

Lets create the tables:

{% codeblock lang:sql %}
CREATE TABLE rra_bundle (
  id SERIAL NOT NULL PRIMARY KEY,
  step_ms INT NOT NULL,
  steps_per_row INT NOT NULL,
  size INT NOT NULL,
  latest TIMESTAMPTZ DEFAULT NULL);

CREATE TABLE rra (
  id SERIAL NOT NULL PRIMARY KEY,
  ds_id INT NOT NULL,
  rra_bundle_id INT NOT NULL,
  pos INT NOT NULL);

CREATE TABLE ts (
  rra_bundle_id INT NOT NULL,
  i INT NOT NULL,
  dp DOUBLE PRECISION[] NOT NULL DEFAULT '{}');
{% endcodeblock %}

Notice how the step and size now become properties of the bundle
rather than the rra which now refers to a bundle. In the `ts` table,
`i` is the index in the round-robin archive (which in the previous
"horizontal" layout would be the array index).

The data we used before was a bunch of temperatures, lets add two more
series, one where temperature is 1 degree higher, and one where it's 1
degree lower. (Not that it really matters).

{% codeblock lang:sql %}
INSERT INTO rra_bundle VALUES (1, 60000, 1440, 28, '2008-04-02 00:00:00-00');

INSERT INTO rra VALUES (1, 1, 1, 1);
INSERT INTO rra VALUES (2, 2, 1, 2);
INSERT INTO rra VALUES (3, 3, 1, 3);

INSERT INTO ts VALUES (1, 0, '{64,65,63}');
INSERT INTO ts VALUES (1, 1, '{67,68,66}');
INSERT INTO ts VALUES (1, 2, '{70,71,69}');
INSERT INTO ts VALUES (1, 3, '{71,72,70}');
INSERT INTO ts VALUES (1, 4, '{72,73,71}');
INSERT INTO ts VALUES (1, 5, '{69,70,68}');
INSERT INTO ts VALUES (1, 6, '{67,68,66}');
INSERT INTO ts VALUES (1, 7, '{65,66,64}');
INSERT INTO ts VALUES (1, 8, '{60,61,59}');
INSERT INTO ts VALUES (1, 9, '{58,59,57}');
INSERT INTO ts VALUES (1, 10, '{59,60,58}');
INSERT INTO ts VALUES (1, 11, '{62,63,61}');
INSERT INTO ts VALUES (1, 12, '{68,69,67}');
INSERT INTO ts VALUES (1, 13, '{70,71,69}');
INSERT INTO ts VALUES (1, 14, '{71,72,70}');
INSERT INTO ts VALUES (1, 15, '{72,73,71}');
INSERT INTO ts VALUES (1, 16, '{77,78,76}');
INSERT INTO ts VALUES (1, 17, '{70,71,69}');
INSERT INTO ts VALUES (1, 18, '{71,72,70}');
INSERT INTO ts VALUES (1, 19, '{73,74,72}');
INSERT INTO ts VALUES (1, 20, '{75,76,74}');
INSERT INTO ts VALUES (1, 21, '{79,80,78}');
INSERT INTO ts VALUES (1, 22, '{82,83,81}');
INSERT INTO ts VALUES (1, 23, '{90,91,89}');
INSERT INTO ts VALUES (1, 24, '{69,70,68}');
INSERT INTO ts VALUES (1, 25, '{75,76,74}');
INSERT INTO ts VALUES (1, 26, '{80,81,79}');
INSERT INTO ts VALUES (1, 27, '{81,82,80}');
{% endcodeblock %}

Notice that every INSERT adds data for all three of our series in a
single database operation!

Finally, let us create the view. (How it works is described in detail in the
[previous article](/blog/2016/12/16/storing-time-series-in-postgresql-part-ii/))

{% codeblock lang:sql %}
CREATE VIEW tv AS
  SELECT rra.id as rra_id,
     rra_bundle.latest - INTERVAL '1 MILLISECOND' * rra_bundle.step_ms * rra_bundle.steps_per_row *
       MOD(rra_bundle.size + MOD(EXTRACT(EPOCH FROM rra_bundle.latest)::BIGINT*1000/(rra_bundle.step_ms * rra_bundle.steps_per_row),
       rra_bundle.size) - i, rra_bundle.size) AS t,
     dp[pos] AS r
  FROM rra AS rra
  JOIN rra_bundle AS rra_bundle ON rra_bundle.id = rra.rra_bundle_id
  JOIN ts AS ts ON ts.rra_bundle_id = rra_bundle.id;
{% endcodeblock %}

And now let's verify that it works:

{% codeblock lang:sql %}
=> select * from tv where rra_id = 1 order by t;
 rra_id |           t            | r
 --------+------------------------+----
       1 | 2008-03-06 00:00:00-00 | 64
       1 | 2008-03-07 00:00:00-00 | 67
       1 | 2008-03-08 00:00:00-00 | 70
 ...
 {% endcodeblock %}

This approach makes writes blazingly fast though it does have its
drawbacks. For example there is no way to read a single series - even
though the view selects a single array element, under the hood
Postgres reads the whole row. Given that time series is more write
intensive and rarely read, this may not be a bad compromise.
