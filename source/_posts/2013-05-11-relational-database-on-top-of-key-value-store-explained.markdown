---
layout: post
title: "Relational database on top of key-value store explained (or why B-trees are cool)"
date: 2013-05-11 11:36
comments: true
categories: 
---

This post attempts to explain how a relational database can be
implemented atop a key/value store, a subject that I've long found
rather mysterious.

Every once in a while I would come across a mention that a relational
database can be implemented using a key/value store (aka dictionary,
hash table or hash map - for brevity I'll be using *map* from here on).

Whenever I thought about it, it just didn't make sense. A relational
database needs to store rows *in order*, and that's one feature that
maps do not provide. Imagine we have a table keyed by employee id
stored in a map and we need to traverse it by id in ascending order. A
hypothetical keys() method would return us a list of ids ordered
randomly. It's impossible to iterate over a hash map *in
order*. So how would a relational database work then?

It took a while for me to realize the root of my misunderstanding. I
naively was trying to picture how tables, rows and values can be
represented as key/value pairs, and that was the wrong path to take. I
was focusing on the wrong layer of abstraction. 

As it turns out the
key [NPI] to this problem is the clever data structure commonly used
to store data in a relational DB known as
*[B-Tree](http://en.wikipedia.org/wiki/B-tree)* (or a variation
thereof, *[B+Tree](http://en.wikipedia.org/wiki/B+tree)*). 
Okay, B-trees are nothing new and I'm sure we've all heard of them. In fact B-trees were 
desgined in the 1970's as a generalization of the
[Binary Search Tree](http://en.wikipedia.org/wiki/Binary_search_tree) that was 
more suited for block storage. 

But there is something about B-trees that I did not know, and which
now that I do know, seems absolutely essential as well as simply brilliant. In his 1979 paper "The
Ubiquitous B-Tree" [Douglas Comer](http://www.cs.purdue.edu/people/comer) writes: 

<blockquote> The availability of demand paging hardware suggests an
interesting implementation of B-trees.  Through careful allocation,
each node of the B-tree can be mapped into one page of the virtual
address space.  Then the user treats the B-tree as if it were in
memory.  Accesses to nodes (pages) which are not in memory cause the
system to "page-in" the node from secondary storage. </blockquote>

The above paragraph implies that the B-Tree and all its data can be
stored in *pages*. In fact, if you look at the file 
[format of a SQLite 3 database](http://www.sqlite.org/src/artifact/eecc84f02375b2bb7a44abbcbbe3747dde73edb2)
(who says source code comments are bad?) you'll see it states quite plainly  that the *file
is divided into pages*. (You will also see a fantastic description of exactly
how a B+tree works, but that's way outside the scope of this post.)

The important point is that the entire file consists of pages and
nothing else. Inside those pages live the B-tree structure, as well as
the data. Each table is a B-tree and to access it we need to know the
starting page number, which in turn is stored in the sqlite_master
table whose root page is always the first page of the file. The root
page of a table is the head of the B-tree strucutre, and it may refer
to other pages, which in turn may be additional nodes of the tree or
pure data.

All pages are of the same size and are numbered
sequentially, thus we can easily retreive any page by its number
because its offset into the file is the page number multiplied by the
page size. (By default a SQLite3 page is 1K and will hold 4 keys,
i.e. the order of the tree is 4).


And bingo, there is our key/value pair: the page number is the key,
and the page itself is the value! All you need to do is stick those
pages into your favorite key/value store keyed by page number and
you've got a relational database atop a key/value store. It's that
simple.

P.S. An astute reader may point out that there is such a thing as a
*sorted map*. But a sorted map is very different from a "pure" hash
map. The miracle of hashing is that not only does it let you find
elements in O(1) time, but more importantly that it is very suitable
for distributed processing, where the map may be spread across
multiple servers. And if you start thinking about how a *sorted* map
might be implemented in a distributed fashion, you will ultimately
loop back to B-trees, because that's typically how it's actually done.