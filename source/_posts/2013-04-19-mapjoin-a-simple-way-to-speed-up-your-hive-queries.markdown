---
layout: post
title: "MapJoin: a simple way to speed up your Hive queries"
date: 2013-04-19 11:15
comments: true
categories: 
---

Mapjoin is a little-known feature of Hive. It allows a table to be
loaded into memory so that a (very fast) join could be performed
entirely within a mapper without having to use a Map/Reduce step. If
your queries frequently rely on small table joins (e.g. cities or
countries, etc.)  you might see a very substantial speed-up from using
mapjoins.

There are two ways to enable it. First is by using a hint, which looks
like `/*+ MAPJOIN(aliasname), MAPJOIN(anothertable) */`. This C-style comment
should be placed immediately following the `SELECT`. It directs Hive
to load `aliasname` (which is a table or alias of the query) into
memory.

```sql
SELECT /*+ MAPJOIN(c) */ * FROM orders o JOIN cities c ON (o.city_id = c.id);
```

Another (better, in my opinion) way to turn on mapjoins is to let Hive
do it automatically. Simply set `hive.auto.convert.join` to true in
your config, and Hive will automatically use mapjoins for any tables
smaller than `hive.mapjoin.smalltable.filesize` (default is 25MB).

Mapjoins have a limitation in that the same table or alias cannot be
used to join on different columns in the same query. (This makes sense
because presumably Hive uses a HashMap keyed on the column(s) used in
the join, and such a HashMap would be of no use for a join on
different keys).

The workaround is very simple - do not use the same aliases in your
query.

I also found that when the Hive documentation states that such queries
are "[not supported](https://cwiki.apache.org/Hive/languagemanual-joins.html#LanguageManualJoins-Mapjoinrestrictions)"
 they mean that the query will fail in unexpected
ways, sometimes with a Java traceback.
