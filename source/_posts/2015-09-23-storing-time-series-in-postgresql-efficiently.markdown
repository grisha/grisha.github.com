---
layout: post
title: "Storing Time Series in PostgreSQL efficiently"
date: 2015-09-23 22:01
comments: true
categories:
---

With the latest advances in PostgreSQL (and other db's), a relational
database begins to look like a very viable TS storage platform. In
this write up I attempt to show how to store TS in PostgreSQL.

A TS is a series of [timestamp, measurement] pairs, where measurement
is typically a floating point number. These pairs (aka "data points")
usually arrive at a high and steady rate. As time goes on, detailed
data usually becomes less interesting and is often consolidated into
larger time intervals until ultimately it is expired.

## The obvious approach ##

The "naive" approach is a three-column table, like so:

```sql
 CREATE TABLE ts (id INT, time TIMESTAMPTZ, value REAL);
```

(Let's gloss over some details such as an index on the time column and
choice of data type for time and value as it's not relevant to this
discussion.)

One problem with this is the inefficiency of appending data. An insert
requires a look up of the new id, locking and (usually) blocks until
the data is synced to disk. Given the TS's "firehose" nature, the
database can quite quickly get overwhelmed.

This approach also does not address consolidation and eventual
expiration of older data points.

## Round-robin database ##

A better alternative is something called a _round-robin database_.  An
RRD is a circular structure with a separately stored pointer denoting
the last element and its timestamp.

A everyday life example of an RRD is a week. Imagine a structure of 7
slots, one for each day of the week. If you know today's date and day
of the week, you can easily infer the date for each slot. For example
if today is Tuesday, April 1, 2008, then the Monday slot refers to
March 31st, Sunday to March 30th and (most notably) Wednesday to March
26.

Here's what a 7-day RRD of average temperature might look as of
Tuesday, April 1:

```
Week day: Sun  Mon  Tue  Wed  Thu  Fri  Sat
Date:     3/30 3/31 4/1  3/26 3/27 3/28 3/29
Temp F:   79   82   90   69   75   80   81
                    ^
                    last entry
```

Come Wednesday, April 2nd, our RRD now loooks like this:

```
Week day: Sun  Mon  Tue  Wed  Thu  Fri  Sat
Date:     3/30 3/31 4/1  4/2  3/27 3/28 3/29
Temp F:   79   82   90   92   75   80   81
                         ^
                         last entry
```

Note how little has changed, and that the update required no
allocation of space: all we did to record 92F on Wednesday is
overwrite one value. Even more remarkably, the previous value
automatically "expired" when we overwrote it, thus solving the
eventual expiration problem without any additional operations.

RRD's are also very space-efficient. In the above example we specified
the date of every slot for clarity. In an actual implementation only
the date of the last slot needs to be stored, thus the RRD can be kept
as a sequence of 7 numbers plus the position of the last entry and
it's timestamp. In Python syntax it'd look like this:

```python
[[79,82,90,92,75,80,81], 2, 1207022400]
```

## Round-robin in PostgreSQL ##

Here is a naive approach to having a round-robin table. Carrying on
with our 7 day RRD example, it might look like this:

```
week_day | temp_f
---------+--------
     1   |   79
     2   |   82
     3   |   90
     4   |   69
     5   |   75
     6   |   80
     7   |   81
```

Somewhere separately we'd also need to record that the last entry is
week_day 3 (Tuesday) and it's 2008-04-01. Come April 2, we could
record the temperature using:

```sql
UPDATE series SET temp_f = 92 WHERE week_day = 4;
```

This might be okay for a 7-slot RRD, but a more typical TS might have
a slot per minute going back 90 days, which would require 129600
rows. For recording data points one at a time it might be fast enough,
but to copy the whole RRD would require 129600 UPDATE statements which
is not very efficient.

This is where using PostgrSQL _arrays_ become very useful.

## Using PostgreSQL arrays ##

An array would allow us to store the whole series in a single
row. Sticking with the 7-day RRD example, our table would be created
as follows:

```sql
CREATE TABLE ts (dp DOUBLE PRECISION[] NOT NULL DEFAULT '{}',
                 last_date DATE,
                 pos INT);
```

(Nevemind that there is no id column for now)

We could populate the whole RRD in a single statement:

```sql
INSERT INTO ts VALUES('{79,82,90,69,75,80,81}', '2008-08-01', 3);
```

...or record 92F for Wednesday as so:

```sql
UPDATE ts SET dp[4] = 92, last_date = '2008-04-02', pos = 4;
```

(In PostgreSQL arrays are 1-based, not 0-based like in most
programming languages)

## But it could be even more efficient ##

Under the hood, PostgreSQL data is stored in pages of 8K. It would
make sense to keep chunks in which our RRD is written to disk in line
with page size, or at least smaller than one page. (PostgreSQL provides
configuration parameters for how much of a page is used, etc, but this
is way beyond the scope of this article).

Having the series split into chunks also paves the way for some kind
of a caching layer, we could have a server which waits for one row
worth of data points to accumulate, then flushes then all at once.

For simplicity, let's take the above example and expand the RRD to 4
weeks, while keeping 1 week per row. In our table definition we need
provide a way for keeping the order of every row of the TS with a
column named n, and while we're at it, we might as well introduce a
notion of an id, so as to be able to store multiple TS in the same
table.

Let's start with two tables, one called rrd where we would store the
last position and date, and another called ts which would store the
actual data.

```sql
CREATE TABLE rrd (
  id SERIAL NOT NULL PRIMARY KEY,
  last_date DATE,
  last_pos INT);

CREATE TABLE ts (
  rrd_id INT NOT NULL,
  n INT NOT NULL,
  dp DOUBLE PRECISION[] NOT NULL DEFAULT '{}');
```

We could then populate the TS with fictitious data like so:

```sql
INSERT INTO rrd (id, last_date, last_pos) VALUES (1, '2008-04-01', 24);

INSERT INTO ts VALUES (1, 1, '{64,67,70,71,72,69,67}');
INSERT INTO ts VALUES (1, 2, '{65,60,58,59,62,68,70}');
INSERT INTO ts VALUES (1, 3, '{71,72,77,70,71,73,75}');
INSERT INTO ts VALUES (1, 4, '{79,82,90,69,75,80,81}');
```

To update the data for April 2, we would:

```sql
UPDATE ts SET dp[4] = 92 WHERE rrd_id = 1 AND n = 4;
UPDATE rrd SET last_date = '2008-04-02', last_pos = 25 WHERE id = 1;
```

The last_pos of 25 is n * 7 + 1 (since arrays are 1-based).

This article omits a lot of detail such as having resolution finer
than one day, but it does describe the general idea. For an actual
implementation of this you might want to check out a project I've been
working on: [tgres](https://github.com/tgres/tgres)
