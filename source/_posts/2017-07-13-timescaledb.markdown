---
layout: post
title: "TimescaleDB"
date: 2017-07-13 07:56
comments: true
published: false
categories:
---

There is a new kid on the time series block:
[TimescaleDB](https://github.com/timescale/timescaledb). (From here on
sometimes referred to as *Timescale*, for brevity). TimescaleDB is a
descendant of the company formerly known as iobeam, a hosted data
analysis service for connected hardware. TimescaleDB is an
open-sourced and evolved version of the underlying data storage
technology.

What I find interesting about Timescale is that it is a Postgres-based
thing. In fact upon some digging I discovered that its very early
code (e.g. [here](https://github.com/timescale/timescaledb/tree/c3d55d339e37de75fa2eab27d6537dca05cc6c48))
consisted entirely in PL/pgSQL.

There isn't a lot of documentation on how it works, though there is a
[paper](https://www.timescale.com/papers/timescaledb.pdf), but it
lacks on the implementation details. The paper
talks about the TimescaleDB *hypertable*, which to the best of my
understanding is another name for the [OLAP cube](https://en.wikipedia.org/wiki/OLAP_cube), aka hypercube.

I am not really an expert on OLAP cubes, but they are not a new
concept, e.g. "pivot tables" is a feature of MS Excel since version 5
released in 1993. My understanding is that under the hood it is a tree
structure where a parent is an element of some dimension of the cube
and children are then other dimensions related to the parent. This way
to find the intersection of "year 1993", "month of June", "sales",
"phase of the moon" and "chickens" is a straight forward tree
traversal operation with the number of steps approximately equal to
the number of dimensions. If the entire structure is in RAM, this can
be extremely fast.

In any event, the initial PL/pgSQL TimescaleDB implementation didn't
have any hypercubes, those were added later.

##How does it work?##

From staring at the code for a few hours, it looks like the general
idea is that once you convert your table to a hypertable it becomes a
partitioned table with insert triggers.  On INSERT, rows are added to
an in-memory hypercube while at the same time a second copy is written
to a
[partition](https://www.postgresql.org/docs/current/static/ddl-partitioning.html).
This partition is known as a *chunk*. The schema of the chunk is
identical to the original table, the chunk is a
[child](https://www.postgresql.org/docs/current/static/ddl-inherit.html)
of the table.  You cannot see the chunks because they are tucked away
in a separate namespace. To the user it just acts like any other
table.

The data is divided
across partitions by the *chunk_time_interval* parameter, as well as
(optionally) another dimension (partitioning column) which you can specify as an argument to the
[create_hypertable](http://docs.timescale.com/api/api-timescaledb#create_hypertable) function.
(As far as I can tell, only one such dimension is supported).

I am still not very clear on what is done to make inserts faster or even
if they are indeed faster than any other PG insert. I think that the
[trick](/blog/2017/01/21/storing-time-seris-in-postgresql-optimize-for-write/)
we're using in Tgres where a bunch of data points across multiple series
is sent as an array of a single row is a performance optimization that would
be hard to beat when it comes to writes.

As far as querying, if the chunk you need to answer the query is in
memory, then naturally it is extremely fast. If the chunk is not in
memory, then it will be loaded first, which too, is actually pretty
fast. I am not very clear on what happens when the query spans chunks
that are on disk and there isn't enough memory to load them all, it
seems to me that in this case a Timescale table wouldn't perform much
faster than any other Postgres one.

##Conclusion##

I like it. I think the approach is a good one, especially because to
the extent possible, Timescale blends into Postgres and all the PG
tools are at your disposal. Timescale does not attempt to reinvent
storage, which is my biggest issue with most every "time series
database" out there. It leaves storage to the experts, if you trust
Postgres, you can trust TimescaleDB. It seems to me that it is not going to be
a solution to all problems, but in my limited testing it does provide
a very substantial (10x) speed up with not a lot of effort - all you
need to do is to call create_hypertable() after creating your table.

I still need to do some research on what is happening with the
inserts. I think that it would be interesting to experiment with Tgres
and see if it could run on top of Timescale, though that would be a
lot of work. There may also be some interesting stuff done whereby
incoming data is stored in the Tgres format, but then is somehow by
way of a trigger copied into a Timescale table and perhaps that could
make queries even faster.
