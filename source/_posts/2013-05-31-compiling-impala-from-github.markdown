---
layout: post
title: "Compiling Impala from Github"
date: 2013-05-31 10:48
comments: true
categories: 
---

Apparently Impala has two versions of source code, one internal to
Cloudera, the other available on Github. I'm presuming that code gets
released to Github once undergone some level of internal scrutiny, but
I've not seen any documentation on how one could tie publically
available code to the official Impala (binary) release, currently 1.0.

Anyway, I tried compiling the github code last night, and here are the
steps that worked for me.

My setup: 

- Linux CentOS 6.2 (running inside a VirtualBox instance on an Early 2011 MacBook, Intel i7).

- CDH 4.3 installed using Cloudera RPM's. No configuration was done, I
  just ran yum install as described in the installation guide.

- Impala checked out from Github, HEAD is 60cb0b75 (Mon May 13 09:36:37 2013).

- Boost 1.42, compiled and installed manually (see below).

The steps I followed:

- Check out Impala:

```sh
git clone git://github.com/cloudera/impala.git
<...>

git branch -v
* master 60cb0b7 Fixed formatting in README

```

- Install Impala pre-requisites as per Impala README, except for Boost:
```
sudo yum install libevent-devel automake libtool flex bison gcc-c++ openssl-devel \
    make cmake doxygen.x86_64 glib-devel python-devel bzip2-devel svn \
    libevent-devel cyrus-sasl-devel wget git unzip
```

- Install LLVM. Follow the precise steps in the Impala README, it works.

- Make sure you have the Oracle JDK 6, not OpenJDK. I found [this link](http://www.if-not-true-then-false.com/2010/install-sun-oracle-java-jdk-jre-6-on-fedora-centos-red-hat-rhel/) helpful.

- Remove the CentOS version of Boost (1.41) if you have it. Impala
  needs uuid, which is only supported in 1.42 and later:
```sh
# YMMV - this is how I did it, you may want to be more cautious
sudo yum erase `rpm -qa | grep boost`
```

- Download and untar Boost 1.42 from [http://www.boost.org/users/history/version_1_42_0.html](http://www.boost.org/users/history/version_1_42_0.html)

- Compile and install Boost. Note that Boost *must* be compiled with multi-threaded support and the layout matters too. I ended up up using the following:

```sh
cd boost_1_42_0/
./bootstrap.sh
# not sure how necessary the --libdir=/usr/lib64 is, there was a post mentioning it, i followed this advice blindly
./bjam --libdir=/usr/lib64 threading=multi --layout=tagged
sudo ./bjam --libdir=/usr/lib64 threading=multi --layout=tagged install

```

- Install Maven, just like the README says, only the URL didn't work, I used
  [http://archive.apache.org/dist/maven/binaries/apache-maven-3.0.4-bin.tar.gz](http://archive.apache.org/dist/maven/binaries/apache-maven-3.0.4-bin.tar.gz) instead

- Now you should be able to compile Impala - just follow the steps in the README starting with `. bin/impala-config.sh`


