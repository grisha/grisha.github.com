---
layout: post
title: "Tgres Status - July 4th 2017"
date: 2017-07-04 08:28
comments: true
categories:
---

It's been a while since I've written on
[Tgres](https://github.com/tgres/tgres),
here's a little update, Independence Day edition.

### Current Status ###

The current status is that Tgres is looking more and more like a
finished product. It still needs time and especially user testing (the
ball is in your court, dear reader), because only time reveals the
weirdest of bugs and validates stability. I would not ditch your
current stack just yet, but at this point you'd be remiss not
having given Tgres a spin.

Recently I had an opportunity to test Tgres as a mirror replica of a
sizable Graphite/Statsd/Grafana set up receiving approximately 10K
data points per second across more than 200K series, and the results
were inspiring. Tgres handled the incoming data without breaking a
sweat on "hardware" (ec2 instances, rather) that was a fraction of the
Graphite machines while still outperforming it in most respects.

I'd say the biggest problem (and not really a Tgres one) is that
mirroring Graphite functionality _exactly_ is next to impossible. Or,
rather, it is possible, but it would imply purposely introducing
inaccuracies and complexities. Because of this Tgres can never be a
"drop in" replacement for Graphite. Tgres can provide results that are
close but not identical, and dashboards and how the data is interpreted
would require some rethinking.

## What's new? ##

### Data Point Versioning ###

In a round-robin database slot values are overwritten as time moves
forward and the archive comes full-circle. Whenever a value is not
overwritten for whatever reason, a stale value from an obsolete
iteration erroneously becomes the value for the current iteration.

One solution is to be diligent and always make sure that values are
overwritten. This solution can be excessively I/O intensive for sparse
series. If a series is sparse, then more I/O resources are spent
blanking out non-data (by setting the value to NaN or whatever) than
storing actual data points.

A much more efficient approach is to store a version number along with
the datapoint. Every time the archive comes full-circle, version is
incremented. With versions there is no need to nullify slots, they
become obsoleted by virtue of the data point version not matching the
current version.

Under the hood Tgres does this by keeping a separate array in the `ts`
table which contains a smallint (2 bytes) for every data point. The `tv`
view is aware of it and considers versions without exposing any
details, in other words everything works as before, only Tgres is a
lot more efficient and executes a lot less SQL statements.

### Zero Heartbeat Series ###

Tgres always strives to connect the data points. If two data points
arrive more than a step apart, the slots in between are
[filled in](https://github.com/tgres/tgres/blob/d5a622a33511c1a8c43538c8de915fac52b02291/rrd/ds.go#L220-L229)
to provide continuity. A special parameter called
[Heartbeat](https://github.com/tgres/tgres/blob/d5a622a33511c1a8c43538c8de915fac52b02291/rrd/ds.go#L81-L105)
controls the maximum time between data points. A gap greater than the Heartbeat is
considered unknown or NaN.

This was a deliberate design decision from the beginning, and it is not changing.
Some tools choose to store data points as is,
deferring any normalization to the query time. Graphite is kind of in
the middle: it doesn't store the data points as is, yet it does not
attempt to do any normalization either, which ultimately leads to
inaccuracies which I describe in another
[post](/blog/2015/05/04/recording-time-series/).

The concept of Heartbeat should be familiar to those experienced with
RRDTool, but it is unknown to Graphite users which has no such
parameter. This "disconnected" behavior is often taken advantage of to
track things that aren't continuous but are event occurrences which can
still benefit from being observed as a time series. Tracking
application deploys, where each deploy is a data value of 1 is one
such example.

Tgres now supports this behavior when the the Heartbeat is set to
0. Incoming data points are simply stored in the best matching slot
and no attempt is made to fill in the gap in between with data.

### Tgres Listens to DELETE Events ###

This means that to delete a DS all you need to do is run `DELETE FROM
ds WHERE ...` and you're done. All the corresponding table rows will
be deleted by Postgres because of the foreign key constraints, and the
DS will be cleared from the Tgres cache at the same time.

This is possible thanks to the Postgres excellent
[LISTEN/NOTIFY](https://www.postgresql.org/docs/current/static/sql-notify.html)
capability.

### In-Memory Series for Faster Querying ###

A subset of series can be kept entirely in memory. The recent testing
has shown that people take query performance very seriously, and
dashboards with refresh rates of 5s or even 1s are not unheard
of. When you have to go to the database to answer every query, and if
the dashboard touches a hundred series, this does not work too well.

To address this, Tgres now keeps an in-memory cache of queried
series. The cache is an [LRU](https://godoc.org/github.com/hashicorp/golang-lru)
and its size is configurable. On restart Tgres saves cache keys and loads the series
back to keep the cache "warm".

Requests for some cached queries can now be served in literally
[microseconds](https://en.wikipedia.org/wiki/Microsecond), which
makes for some pretty amazing user experience.

### DS and RRA State is an Array ###

One problem with the Tgres table layout was that DS and RRA tables
contained frequently updated columns such as lastupdate, value and
duration The initial strategy was that these could be updated
periodically in a lzay fashion, but it became apparent that it was not
practical for any substantial number of series.

To address this all frequently mutable attributes are now stored in
arrays, same way as data points and therefore can be updated 200 (or
whatever segment width is configured) at a time.

To simplify querying DSs and RRAs two new views (`dsv` and `rrav`)
were created which abstract away the array value lookup.

### Whisper Data Migration ###

The [whisper_import](https://github.com/tgres/tgres/tree/master/cmd/whisper_import)
tool has been pretty much rewritten and has better instructions. It's been
tested extensively, though admittedly on one particular set up, your mileage may vary.

### Graphite DSL ###

Lots and lots of fixes and additions to the Graphite DSL
implementation. Tgres still does not support *all* of the functions,
but that was never the plan to begin with.

## Future ##

Here's some ideas I might tackle in the near future. If you are
interested in contributing, do not be shy, pull requests, issues and
any questions or comments are welcome. (Probably best to keep
development discussion in [Github](https://github.com/tgres/tgres/issues)).

* ####Get rid of the config file####

Tgres doesn't really need a config file - the few options that are
required for running should be command line args, the rest, such as
new series specs should be in the database.

* #### A user interface ####

Not terribly high on the priority list, since the main UI is `psql`
for low level stuff and Grafana for visualization, but something to
list series and tweak config options might come in handy.

* #### Track Usage ####

It would be interesting to know how many bytes exactly a series
occupies, how often it is updated and queried, and what is the
resource cost for maintaining it.

* #### Better code organization ####

For example vcache could be a separate package.

* #### Rethink the DSL ####

There should be a DSL version 2, which is not based on the Graphite
unwieldiness. It should be very simple and versatile and not have
hundreds of functions.

* #### Authentication and encryption ####

No concrete ideas here, but it would be nice to have a plan.

* #### Clustering needs to be re-considered ####

The current clustering strategy is flawed. It might work with the
current plan, but some serious brainstorming needs to happen
here. Perhaps it should just be removed in favor of delegating
horizontal scaling to the database layer.
