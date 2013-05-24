---
layout: post
title: "Checking out Cloudera Impala"
date: 2013-05-23 12:43
comments: true
categories: 
---

I've decided to check out
[Impala](http://blog.cloudera.com/blog/2012/10/cloudera-impala-real-time-queries-in-apache-hadoop-for-real/)
last week and here's some notes on how that went.

## First thoughts

I was very impressed with how easy it was to install, even considering
our unusual set up (see below). In my simple ad-hoc tests Impala
performed orders of magnitude faster than Hive. So far it seems solid
down to the little details, like the shell prompt with a fully
functional libreadline and column headers nicely formatted.

## Installing

The first problem I encountered was that we use Cloudera
[tarballs](http://www.cloudera.com/content/cloudera-content/cloudera-docs/CDHTarballs/3.25.2013/CDH4-Downloadable-Tarballs/CDH4-Downloadable-Tarballs.html)
in our set up, but Impala is only available as a package (RPM in our
case). I tried compiling it from
[source](https://github.com/cloudera/impala), but it's not a trivial
compile - it requires [LLVM](http://llvm.org/) (which is way cool,
BTW) and has a bunch of dependencies, it didn't work out-of-the-box
for me so I've decided to take an alternative route (I will definitely get it compiled some weekend soon). 

Retreiving contents of an RPM is trivial (because it's really a cpio
archive), and then I'd just have to "make it work".

```
$ curl -O http://archive.cloudera.com/impala/redhat/6/x86_64/impala/1.0/RPMS/x86_64/impala-server-1.0-1.p0.819.el6.x86_64.rpm
$ mkdir impala
$ cd impala
$ rpm2cpio ../impala-server-1.0-1.p0.819.el6.x86_64.rpm | cpio -idmv
```

I noticed that `usr/bin/impalad` is a shell script, and it appears to
rely on a few environment vars for configuration, so I created a shell
script that sets them which looks approximately like this:

```sh
export JAVA_HOME=/usr/java/default
export IMPALA_LOG_DIR= # your log dir
export IMPALA_STATE_STORE_PORT=24000
export IMPALA_STATE_STORE_HOST= # probably namenode host or whatever
export IMPALA_BACKEND_PORT=22000

export IMPALA_HOME= # full path to usr/lib/impala from the RPM, e.g. /home/grisha/impala/usr/lib/impala
export IMPALA_CONF_DIR= # config dir, e.g. /home/grisha/impala/etc/impala"
export IMPALA_BIN=${IMPALA_HOME}/sbin-retail
export LIBHDFS_OPTS=-Djava.library.path=${IMPALA_HOME}/lib
export MYSQL_CONNECTOR_JAR= # full path a mysql-connect jar

export HIVE_HOME= # your hive home - note: every impala nodes needs it, just config, not the whole Hive install
export HIVE_CONF_DIR= # this seems redundant, my guess HIVE_HOME is enough, but whatever
export HADOOP_CONF_DIR= # path the hadoop config, the dir that has hdfs-site.xml, etc.

export IMPALA_STATE_STORE_ARGS=" -log_dir=${IMPALA_LOG_DIR} -state_store_port=${IMPALA_STATE_STORE_PORT}"
export IMPALA_SERVER_ARGS=" \                                                                                                                                                                                  -log_dir=${IMPALA_LOG_DIR} \                                                                                                                                                                              -state_store_port=${IMPALA_STATE_STORE_PORT} \                                                                                                                                                            -use_statestore \                                                                                                                                                                                         -state_store_host=${IMPALA_STATE_STORE_HOST} \                                                                                                                                                            -be_port=${IMPALA_BACKEND_PORT}"
```

With the above environment vars set, starting Impala should amount to
the following (you probably want to run those in separate windows, also note that
the state store needs to be started first):

```
$ ./usr/bin/statestored ${IMPALA_STATE_STORE_ARGS} # do this on IMPALA_STATE_STORE_HOST only
$ ./usr/bin/impalad ${IMPALA_SERVER_ARGS} # do this on every node
```

The only problem that I encountered was that Impala needed
short-circuit access enabled, so I had to add the following to the hdfs-site.xml:

```xml
     <property>
       <name>dfs.client.read.shortcircuit</name>
       <value>true</value>
     </property>
     <property>
       <name>dfs.domain.socket.path</name>
    <!-- adjust this to your set up: -->
       <value>/var/run/dfs_domain_socket_PORT.sock</value>
     </property>
     <property>
       <name>dfs.client.file-block-storage-locations.timeout</name>
       <value>3000</value>
     </property>
     <property>
    <!-- adjust this too: -->
       <name>dfs.block.local-path-access.user</name>
       <value><!-- user name --></value>
     </property>
```

Once the above works, we need `impala-shell` to test it. Again, I pulled it out of the RPM:

```
$ curl -O http://archive.cloudera.com/impala/redhat/6/x86_64/impala/1.0/RPMS/x86_64/impala-shell-1.0-1.p0.819.el6.x86_64.rpm
$ mkdir shell ; cd shell
$ rpm2cpio ../impala-shell-1.0-1.p0.819.el6.x86_64.rpm | cpio -idmv
```

I was then able to start the shell and connect. You can connect to any Impala node (read the docs):

```
$ ./usr/bin/impala-shell
[localhost:21000] > connect some_node;
Connected to some_node:21000
Server version: impalad version 1.0 RELEASE (build d1bf0d1dac339af3692ffa17a5e3fdae0aed751f)
[some_node:21000] > select count(*) from your_favorite_table;
Query: select count(*) from your_favorite_table
Query finished, fetching results ...
+-----------+
| count(*)  |
+-----------+
| 302052158 |
+-----------+
Returned 1 row(s) in 2.35s
```

Ta-da! The above query takes a good few minutes in Hive, BTW.

## Other Notes

- Impala does not support custom SerDe's so it won't work if you're relying on JSON. It does support Avro.
- There is no support for UDF's, so our [HiveSwarm](https://github.com/livingsocial/HiveSwarm) is of no use.
- INSERT OVERWRITE works, which is good.
- LZO support works too.
- *Security Warning*: It appears that everything Impala does will
  appear in HDFS as the user under which Impala is running. Be careful
  with this if you're relying on HDFS permissions to prevent an
  inadvertent "INSERT OVERWRITE", as you might inadvertently give your
  users superuser privs on HDFS via Hue, for example. (Oh did I
  mention Hue completely supports Impala too?). From what I can tell
  there is no way to set a username, this is a bit of a show-stopper
  for us, actually.


