---
layout: post
title: "Keeping ETL in BigQuery&nbsp;with&nbsp;bq_etl."
date: 2020-05-08 12:22
comments: true
published: true
categories:
---

When doing computing that requires data to be local to the machine,
e.g. model training on a GPU, data may be downloaded from tables in
BigQuery or similar SQL-centric environments such as Hadoop/Hive. (The
[project](https://github.com/grisha/bq_etl) I describe here is
BigQuery-specific for now, but the concept applies and can be extended
to any such tool).

There is always the question of when does one bring data out of
BigQuery and how much more data transformation is acceptible
afterwards. I believe that the correct answer is a rather strong
"none": all possible data transformation should be done *before* the
data leave BigQuery.

Reality is oft otherwise. Once information is downloaded to local
storage, it is much easier to load up a Pandas dataframe for a quick
tweak.  Even though the proper fix would be to correct the SQL and run
it again, it is just too convenient to adjust data locally. Once a
dataset has been corrected locally, possibly multiple times as part of
development iteration, it becomes critically important to somehow keep
track of which files result from which code version. You can hopefully
see how this is gradually becoming a data nightmare.

Data monkey patching is difficult to track because the place in code
where it happens usually is not in any way tied to the SQL statement
for which it is correcting. The SQL defining the original data may be
in a different code base or in none at all.

Here is my simple solution. It starts with a few requirements:

>  * Each SQL statement should be in its own .sql file.

This makes it possible to view and edit this code as what it is - SQL,
not a string in Python code.

>  * The name and the content of the .sql file should dictate the name
>    of the output table.

The simplest way to do this is with a short hash of the contents
appended to the table name. Once that is true, the .sql file becomes a
complete description of the output table. If the SQL file is altered,
it would result in a different table.

>  * There should be no need to use external tools to keep track of
>    the state.

You do not need MLFlow or Redis to know that the SQL has been
executed - the mere table's existence in BigQuery is evidence of it.

>  * The location of  any GCS extracts from this table should uniquely match the table name.

If the blob(s) exist, it means that the extract has been performed.

>  * The local filename should still depend on the original .sql file.

Which makes it easy to check whether the data has been downloaded to
local storage.

Note that given the above scheme, if the name or the content of the
.sql file changes, so does the table name, the GCS extract name and
the local file name.

Given the above few constraints, we can now answer the questions of
"Should this SQL be executed or has it already been done?", "Should
this table be extracted to GCS?" and "Should this GCS data be
downloaded?" and optionally forego these steps if they are already
done.

>  * The order of execution of .sql files should be inferred from the
>    SQL itself.

Last but no the least, if we have multiple SQL statements to be
executed, what dictates the order of execution? It turns out that SQL
statements do not need to be executed in any particular order *unless*
the output of one is input to another. As I have [written about before](/blog/2016/11/14/table-names-from-sql/),
this is best inferred
from the SQL itself and does not need to be explicitely
specified.

Last week I put together a simplistic little package that does all of
the above. See it on Github at [https://github.com/grisha/bq_etl](https://github.com/grisha/bq_etl).

It was written to serve my specific needs and for this reason it is
very bare-bones, but that's not to say I'm not open to comments,
issues and pull requests to make it better!
