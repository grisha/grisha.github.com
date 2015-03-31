---
layout: post
title: "On Time Series"
date: 2015-03-28 15:40
comments: true
categories:
---

## Is it a even thing?

Time Series is on its way to becoming a buzzword in the Big Data
circles. This has to do with the looming Internet of Things which
shall cause the Great Reversal of Internet whereby upstream flow of
data produced by said Things is expected to exceed the downstream
flow. Much of this data is expected to be of the Time Series kind.

This, of course, is a money-making opportunity of the Big Data
proportions all over again, and I imagine we're going to see a lot of
Time Series support of various shapes and forms appearing in all
manners of (mostly commercial) software.

But is there really such a thing as the problem specifically inherent
to Time Series data which warrants a specialized solution? I've been
pondering this for some time now, and I am still undecided. This
here is my attempt at arguing that TS is *not* a special problem and
that it can be done by using a database like PostgreSQL.

## Influx of data and write speeds

One frequently cited issue with time series data is that it arrives in
large volumes at a steady pace which renders buffered writes
useless. The number of incoming data streams can also be large
typically causing a disk seek per stream and further complicating the
write situation. TS data also has a property where often more data is
written than read because it's possible for a data point to be
collected and examined only once, if ever. In short, TS is very
write-heavy.

But is this unique? For example logs have almost identical
properties. The real question here is whether our tried and true
databases such as PostgreSQL are ill-equipped to deal with large
volumes of incoming data requiring an alternative solution.

When considering incoming data I am tempted to imagine every US
household sending it, which, of course, would require massive
infrastructure. But this (unrealistic) scenario is not a TS data
problem, it's one of scale, the same one from which the Hadoops and
Cassandras of this world were born. What is really happening here is
that TS happens to be yet another thing that requires the difficult to
deal with "big data" infrastructure and reiterates the need for an
easy-to-setup horizontally scalable database.

The only thing that is certain here is that we can expect more "Big
Data" stuff as we inch closer to the Internet of Things being a
reality. Perhaps this need will finally result in PostgreSQL natively
supporting clustering.

## The backfill problem

This is the problem of having to import vast amounts of historical
data. For example OpenTSDB goes to great lengths to optimize
back-filling by structuring it in specific ways and storing compressed
blobs of data.

But just like the write problem, it's not unique to TS. It
is another problem that is becoming more and more pertinent as our
backlogs of data going back to when we stopped using paper keep
growing and growing.

## Downsampling

Aside from a few corner cases, most often TS data is used to generate
charts. This is an artifact of the human brain being spectacularly
good at interpreting a visual representation of a relationship between
streams of numbers while completely incapable of making any sense of
it when presented in tabular form. When plotting, no matter how much
data is being examined, the end result is limited to however many
pixels are available on the display. I should also point out that
aggregation is useful even when using raw data, most any use of time
series data is in an aggregated form.

The process of consolidating datapoints into a smaller number (e.g.
the pixel width of the chart), sometimes called _downsampling_, involves
aggregation around a particular time interval or simply picking every
Nth datapoint.

As an aside, selecting every Nth row of a table is an interesting SQL
challenge, in PostgreSQL it looks like this (for every 100th row):

```
 SELECT time, data FROM
   (SELECT *, row_number() OVER (ORDER BY time) as n FROM data_points) dp
      WHERE dp.n % 100 = 0 ORDER BY time
```

Aggregation over a time interval similar to how InfluxDB does it with
the `GROUP BY time(1d)` syntax can be easily achieved via the
`date_trunc('day', time)`.

Another aspect of downsampling is that since TS data is immutable,
there is no need to repeatedly recompute the consolidated version. It
makes more sense to downsample immediately upon the receipt of the
data and to store it permanently in this form. RRDTool's Round-Robin
database is based entirely on this notion. InfluxDB's continuous
queries is another way persistent downsampling is addressed.

Again, there is nothing TS-specific here. Storing data in summary form
is quite common in the data analytics world and a "continuous query"
is easily implemented via a trigger.

## Derivatives

Sometimes the data from various devices exists in the form of a
counter, which requires the database to derive a rate by comparing
with a previous data point. An example of this is number of bytes sent
over a network interface. Only the rate of change of this value is
relevant, not the number itself. The rate of change is the difference
with the previous value divided over the time interval passed.

Referring to a previous row is also a bit tricky but perfectly doable
in SQL. It can accomplished by using windowing functions such as
`lag()`.

```
SELECT time,
  (bytes - lag(bytes, 1) OVER w) / extract(epoch from (time - lag(time, 1) OVER w))::numeric
    AS bytes_per_sec
  FROM data_points
  WINDOW w AS (ORDER BY time)
  ORDER BY time
```

## Expiration

It is useful to downsample data to a less granular form as it ages,
aggregating over an ever larger period of time and possibly purging
records eventually. For example we might want to store minutely data
for a week, hourly for 3 months, daily for 3 years and drop all data
beyond 3 years.

Databases do not do this "natively" like Cassandra or Redis, but it
shouldn't be too hard to accomplish via some sort of a periodic cron
job or possibly even just triggers.

## Heartbeat and Interval Filling

It is possible for a time series stream to stop, and this can be
interpreted in different ways: we can attempt to fill in missing data,
or treat it as unknown. More likely we'd want to start treating it as
unknown after some period of silence. RRDTool addresses this by
introducing the notion of a _heartbeat_ and the number of missed beats
before data is treated as unknown.

Regardless of whether the value is unknown, it is useful to be able to
fill in a gap (missing rows) in data. In PostgreSQL this can be
accomplished by a join with a result set from the `generate_series()`
function.

## Data Seclusion

With many specialized Time Series tools the TS data ends up being
secluded in a separate system not easily accessible from the rest of
the business data. You cannot join your customer records with data in
RRDTool or Graphite or InfluxDB, etc.

## Conclusion

If there is a problem with using PosgreSQL or some other database for
Time Series data, it is mainly that of having to use advanced SQL
syntax and possibly requiring some cookie cutter method for managing
Time Series, especially when it is a large number and high volume.

There is also complexity in horizontally scaling a relational database
because it involves setting up replication, sharding, methods for
recovery from failure and balancing the data. But these are not
TS-specific problem, they are typical general scaling problems.

Having written this up, I'm inclined to think that perhaps there is
no need for a specialized "Time Series Database", instead it can be
accomplished by an application which uses a database for storage and
abstracts the users from the complexities of SQL and potentially even
scaling, while still allowing for direct access to the data via the
rich set of tools that a database like PostgreSQL provides.

