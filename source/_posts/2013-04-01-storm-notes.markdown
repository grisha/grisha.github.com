---
layout: post
title: "Storm Notes"
date: 2013-04-01 17:05
comments: true
categories: 
---

Some random thoughts on having tinkered with
[Storm](http://storm-project.net/) over the past few weeks.

It took me some time to understand what Storm is, and I am still not
clear I have found a perfect use for it. (This is not
a criticism of Storm, the point is that the concepts it introduces are
new, somewhat diffuclt and will need some time so sync in). The best way to get the basic
understanding of Storm concepts is to watch Nathan Marz's [excellent presentation](https://www.youtube.com/watch?v=bdps8tE0gYo). 

In simple terms, Storm is a tool that lets you run code in parallel
across a cluster of servers. It differs from Map/Reduce in that the
actual algorithm is entirely up to you, and in essence all that Storm
provides is the framework that supervises all the moving pieces of your
application (known as a *topology*) and provides a uniform way of
creating, testing locally, sumbitting to a cluster, logging,
monitoring, as well as primitives for sending data between components
such as grouping data by using hashing, etc.

Storm is mainly meant for stream processing. A stream could be
anything, some of the most obvious examples may be your web logs,
tables containing user actions such as clicks, transactions,
purchases, trades, etc. If the data is coming in at a rate where it's
challenging to process it on one server, Storm provides a way to scale
it across a cluster of servers and can handle ridiculous amounts of
incoming data. The result is a real-time view of summary data that is
always up to date.

Storm is written in Java and Clojure, which makes the JVM the common
denominator, so any JVM language should work as "native". Storm also provides a
primitive for using pipes to a process which means that you can write
a component in anything - from a Bash script to C, all it needs to do
is read stdin and write stdout.

For those who would prefer to try it out using a higher-level
language, there is an excellent project called
[Redstorm](https://github.com/colinsurprenant/redstorm) which lets you
write your topology in JRuby. While a Redstorm topology may not be as
fast as something written in pure Java, the reduced development
time is well worth any trade offs, and you always have the option of
perfecting it later by porting your code to something JVM-native when
your understanding of how it ought to work is solidified in your mind.

If you're going to go the Redstorm route, a couple of gotchas that I
came across were:

- Storm 0.8.2 and JRuby 1.7.2 disagree on the version of Yaml parsing
  jar (snakeyaml). Don't know what the solution is if you absolutely must parse
  Yaml other than downgrading to JRuby 1.6.8, otherwise you can just
  use something other than Yaml: JSON or just plain eval().

- If you're going to use ActiveRecord (which does work fine), watch
  out for how to properly use it in a multi-threaded environment. You
  might need to wrap some code in synchronize (see [Concurrency in JRuby](https://github.com/jruby/jruby/wiki/Concurrency-in-jruby).
  You will also need make sure your ActiveRecord connections are not
  shared by concurrent threads by using
  [connection_pool.with_connection](http://api.rubyonrails.org/classes/ActiveRecord/ConnectionAdapters/ConnectionPool.html#method-i-with_connection)

