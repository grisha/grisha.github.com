---
layout: post
title: "On keeping lots of integers in memory"
date: 2013-03-25 22:09
comments: true
published: true
categories: [redis, 'big memory', 'recommendations'] 
---

Once upon a time (over a year ago) I found myself needing to store large numbers of
integers in memory. The goal was to store a graph of all our
purchasers and items purchased, so that we could quickly identify
like-minded purchasers based on common purchases and make real-time
recommendations of the form "people like you also bought". This
approach is commonly known as [collaborative filtering](http://en.wikipedia.org/wiki/Collaborative_filtering), 
and exactly how we did it would be a subject of some future post
(perhaps).

At the time, I was looking at tens of millions of purchases by tens of
millions people of hundreds of thousands of items. The only
information I needed to store were id's of people and items, which
were just integers. While this seemed like a lot of data, I
believed it was entirely feasible to store them all in memory.

I didn't have time to write my own implementation for storing this
graph, so I looked at a bunch of tools out there, asked around, and
the only one that seemed to fit the bill exactly in the end was
[Redis](http://redis.io/). Yes, there are a few projects out there
that tout graph storage as their specialty, but none of them could
scale anywhere close to the level I needed. And in the end the term
"graph database" turned out to be a red herring of sorts. Any language
such as Python, Ruby or Java provides the basic data structures
quite sufficient for storing a graph as an adjacency list
out-of-the-box. You can store a graph in any key-value store, or even
in your favorite RDBMS. (To this day I'm not convinced there is any
good use case for the so-called graph databases out there.)

There were a few things that set Redis apart: 

First, it keeps everything in RAM, which meant that updating this
dataset would be very fast, fast enough to keep it up-to-date in real
time.

The second great thing about Redis is [Sorted Sets](http://redis.io/commands#sorted_set). This data structure
and the operations it supports fit what we needed to do
precisely. (Again, sorry for sparing you the details, but roughly, you
need to store a Set of item ids for every person as well as a Set of
person ids for every item, and "people like you" then becomes the
union of all the Sets of items that are directly linked to "you".)

Thirdly, Redis supports replication, which meant that if the most
CPU-intensive task of computing the actual recommendations (which
requires union-ing of a large number of large Sorted Sets) becomes a
bottle neck, we could address this by running it on slaves, and
we could easily scale the system by simply adding more slaves.

Last (but hardly least) is Redis' ability to persist and quickly load
the in-memory database. You begin to appreciate the immense value of
this once you start populating Redis by pulling historical data from
your RDBMS and realize that it could take many hours or even days.

Everything was going great with my plan but soon I ran into a problem.
Not even a quarter of the way through the initial load process, I
noticed Redis reporting 20+ GB being used, which meant that the
particular machine I was testing this on wouldn't have enough
RAM. That was a bummer. Especially because it began to look like the
whole architecture would require more memory than would be financially
sensible for this project (yes, you could get a machine with 1TB of
memory, but it was and still is prohibitively expensive).

My hunch (supported by some quick back-of-the-napkin calculations) was
that this was a software problem, not a hardware one.

The first obvious inefficiency of storing integers on a 64-bit
system is how much space an integer takes up. 64 bits (or 8 bytes)
is enough to store a number as large as 92,23,372,036,854,775,807. Yet
this number takes up exactly as much memory as 17 or 1234 (pick your
favorite small number). In fact, the range of integers I was dealing
with was well under 1 billion and 32 bits would more than suffice.

Add to this that on a 64-bit system every *pointer* is also (you guessed
it) - 64 bits. So if you're storing a (singly) linked list of
integers, you end up with 8 bytes for the integer and 8 bytes for the
"next" pointer, or 16 bytes per integer. And if your data structure
is even more complex, such as a Redis Sorted Set, which is actually
implemented as two structures updated simultaneously (a Skip List and a
Hash), well, then you begin to see that our integers may end up taking
up as much if not less memory than the pointers pointing to them.

One simple way to reduce the memory bloat was to compile Redis in
32-bit mode.  Redis makes it super easy with "make 32bit".  Because of
the smaller pointer size the 32-bit mode uses much less memory, but of
course the caveat is that the total address space is limited to 32
bits or about 4GB.  While this did reduce the footprint by a great
deal, it wasn't sufficient for my data set, which still looked to be
more than 4GB in size.

Then I came across this page on [memory optimization](http://redis.io/topics/memory-optimization").  Little
did I know Redis already provided a very compact way of storing
integers. For small lists, sets or hashes, Redis uses a special
structure it calls <em>ziplist</em> that can store variable-length
integers and strings. The advantage is that it is very compact, but
the flipside is that such lists can only be processed
sequentially. (This is because you can't access an n-th element in
such a list because sizes of elements vary, so you must scan from
beginning). But it tunrs out that sequential processing is actually
more efficient for small lists rather than following a more complex
algorithm (hashing or whatever) because it requires no
indirection and can be accomplished with simple pointer math.

Redis' zset-max-ziplist-entries config setting sets a threshold - any
Sorted Set that has fewer elements than the setting is stored as a
ziplist and as soon as it reaches the number greater than the setting
it is converted to the full-fledged Sorted Set data
structure.

What was interesting is that in my tests bumping up the value from the
default of 128 to as high as 10000 didn't seem to have any noticeable
performance impact while reduced the memory usage by an order of
magnitude. My best guess is that even at 10K elements this list is
small enough to be processed entirely in the CPU cache.

The effect of tweaking this setting seemed like pure magic, so I just
had to dig deeper and figure out exactly how it works. You can see the
description of the format in the comments for this file in Redis
source: [src/ziplist.c](https://github.com/antirez/redis/blob/unstable/src/ziplist.c).

The technique is very simple - the first 4 bits are used to identify
the size of the integer. The relevant comment text:

``` c
* |11000000| - 1 byte
* Integer encoded as int16_t (2 bytes).
* |11010000| - 1 byte
* Integer encoded as int32_t (4 bytes).
* |11100000| - 1 byte
* Integer encoded as int64_t (8 bytes).
* |11110000| - 1 byte
* Integer encoded as 24 bit signed (3 bytes).
* |11111110| - 1 byte
* Integer encoded as 8 bit signed (1 byte).
* |1111xxxx| - (with xxxx between 0000 and 1101) immediate 4 bit integer.
* Unsigned integer from 0 to 12. The encoded value is actually from
* 1 to 13 because 0000 and 1111 can not be used, so 1 should be
* subtracted from the encoded 4 bit value to obtain the right value.
```

Actually, back when I looked at it, there was no 24-bit integer
encoding, which led me to submitting a [patch](https://github.com/antirez/redis/issues/469), which
was gladly accepted (and corrected for [two's complement](http://en.wikipedia.org/wiki/Two%27s_complement) support) by [antirez](http://invece.org/).

Since that time I've been noticing different takes on variable-length
integer storage in other projects.


For example [Bitcoin](http://www.bitcoin.org) uses [variable-length integers](https://en.bitcoin.it/wiki/Protocol_specification#Variable_length_integer) to minimize the total size of the block
chain. The bitcoin algo is as follows:

``` c
 * Examine at the first byte
 *  - If that first byte is less than 253, 
 *    use the byte literally
 *  - If that first byte is 253, read the next two bytes 
 *    as a little endian 16-bit number (total bytes read = 3)
 *  - If that first byte is 254, read the next four bytes 
 *    as a little endian 32-bit number (total bytes read = 5)
 *  - If that first byte is 255, read the next eight bytes 
 *   as a little endian 64-bit number (total bytes read = 9)
```

[SQLite3](http://sqlite.org/) uses its own variable-length integer format,
possibly cleverer than the two above:

``` c
** Cell content makes use of variable length integers.  A variable
** length integer is 1 to 9 bytes where the lower 7 bits of each
** byte are used.  The integer consists of all bytes that have bit 8 set and
** the first byte with bit 8 clear.  The most significant byte of the integer
** appears first.  A variable-length integer may not be more than 9 bytes long.
** As a special case, all 8 bytes of the 9th byte are used as data.  This
** allows a 64-bit integer to be encoded in 9 bytes.
**
**    0x00                      becomes  0x00000000
**    0x7f                      becomes  0x0000007f
**    0x81 0x00                 becomes  0x00000080
**    0x82 0x00                 becomes  0x00000100
**    0x80 0x7f                 becomes  0x0000007f
**    0x8a 0x91 0xd1 0xac 0x78  becomes  0x12345678
**    0x81 0x81 0x81 0x81 0x01  becomes  0x10204081
**
** Variable length integers are used for rowids and to hold the number of
** bytes of key and data in a btree cell.
```

There are also other more sophisticated techniques of storing lists of integers such as
[Elias encoding](http://en.wikipedia.org/wiki/Elias_gamma) and [Golomb coding](http://en.wikipedia.org/wiki/Golomb_coding).



