---
layout: post
title: "Maestro the BigQuery Orchestrator"
date: 2019-06-05 15:59
comments: true
categories:
published: труе
---

This blog post is mostly for the Google BigQuery nerds out there.  I
am delighted to announce that a little project we've been hacking on
for the past two years has been made open source under the Apache 2.0
license: [https://github.com/voxmedia/maestro](https://github.com/voxmedia/maestro).

Maestro is a trusty tool that imports data from our databases every
night and runs a bunch of BigQuery SQL to generate summaries,
analysis, recommendations, etc. If anything goes wrong, it lets us
know by posting to Slack. It also keeps track of resource utilization
so we can easily tell what each data transformation is costing
us. Maestro keeps track of who created which table so that when
there is a problem, we know whom to ask about it. All SQL changes are
pushed to Github, so that if anything is broken, it is trivial to
figure out what may have caused it by looking at the commit history.

Before Maestro we had a bunch of scripts and cron jobs, and we also
experimented with the multitude of data pipeline tools out there. The
problem was that adding a new SQL statement always required some form
of programming. The second problem was the interdependency management,
i.e. how does one script know that the other thing it relies on is
finished so it can start. Both problems are typically addressed in
ways that are error prone and inefficient. Not to mention that each
job  would be done differently, with varying levels of error
management and notifications. Maestro solved all that.

We still use scripts and cronjobs, and things like Airflow, and
probably will be using them forever. But when it comes to periodically
running some SQL to generate a summary table or importing another
table from a database, Maestro is clearly the first choice.

Maestro is a web app, though it didn't start out this way. The first
version was just a daemon which stored its configuration in
Postgres. To change anything we would simply INSERT/UPDATE on the
`psql` command line. Later we added a crude React UI. The UI leaves a
lot to be desired, but given that the user base is mostly data
engineers and data scientists, no one is complaining.

Maestro requires no programming. The dependency graph is inferred by
examining the SQL, which is how it should be. Everything is in one
place, all errors and notifications are always consistent.

In addition to having a UI, Maestro also has a
[Python client library](https://github.com/voxmedia/maestro/tree/master/pythonlib)
making it very easy to integrate with your favorite data science packages.
Maestro can also export tables as CSV to Google Cloud Storage and
notify your other apps via HTTP when it is done. It can also export
tables to Google Sheets for the humans.

Maestro is written in Go. It is trivial to deploy - it is a single
binary which only requires access to a database to store its
configuration and state. The binary can be compiled with all web
assets baked into itself and deployed in a `FROM scratch`
Docker container only megabytes in size. Being a Go program also makes
it quite performant when it comes to transferring data between
databases and BigQuery.

[Maestro source code](https://github.com/voxmedia/maestro) is in
Github and there is quite a bit of documentation in
[Maestro godoc](https://godoc.org/github.com/voxmedia/maestro), including the
[getting started](https://godoc.org/github.com/voxmedia/maestro#hdr-Getting_Started)
instructions.

The structure of the source code and the UI implementation follows the
guidelines I set out in a series of [previous posts](https://grisha.org/blog/2017/04/27/simplistic-go-web-app/)
on building Golang web apps.

Please check it out and let us know via Github issues if you have any
questions, comments, feature suggestions, etc.
