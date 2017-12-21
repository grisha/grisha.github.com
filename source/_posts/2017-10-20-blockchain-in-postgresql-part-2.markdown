---
layout: post
title: "Blockchain in PostgreSQL Part 2"
date: 2017-10-20 08:05
comments: true
published: true
categories:
---

In a [previous post](/blog/2017/10/10/postgre-as-a-full-node/) I
described a simplistic schema to store the Bitcoin blockchain in
PostgreSQL. In this post I'm investigating pushing the envelope
with a bit of C programming.

### The Missing Functionality ###

Postgres cannot do certain things required to fully handle
transactions. The missing functionality is (at least):

1. Support for [Variable Length Integer](https://en.bitcoin.it/wiki/Protocol_documentation#Variable_length_integer)
   used in the blockchain and more generally the binary encoding of a transaction or its components.

3. [Elliptic Curve Signature](https://en.wikipedia.org/wiki/Elliptic_Curve_Digital_Signature_Algorithm). Even
   though postgres integrates with OpenSSL, which has that functionality, there is no way to call
   the EC functions.

4. Ability to parse and evaluate Bitcoin [script](https://en.bitcoin.it/wiki/Script). This is a biggie,
   as transaction verification requires it, and it is one of the more complex and bug-prone
   aspects of Bitcoin.

It is also important that all of the above be performant. Even though
varints, script and even elliptic curve could be implemented in plain
[PL/pgSQL](https://www.postgresql.org/docs/current/static/plpgsql.html),
it probably wouldn't be fast enough for practical use. Which leaves us with the only possible option:
a [C extension](https://www.postgresql.org/docs/current/static/xfunc-c.html).

### Avoid Reinventing the Wheel ###

Anything is possible in C, but can we avoid having to reimplement it
from scratch? Are there libraries that could be leveraged?

As it is now, the Bitcoin protocol is primarily specified by its
source code, and the source of all truth is the [Bitcoin Core](https://github.com/bitcoin/bitcoin).
It is [possible](https://www.postgresql.org/docs/current/static/xfunc-c.html#extend-cpp) to use C++ in PG
extensions, which means at least in theory the Bitcoin Core code could be leveraged somehow.

My initial conclusion is that this would be a daunting task. Bitcoin
Core code requires at least C++11, as well as Boost. It also seems
that the core code assumes its own specific storage and caching mechanism and
isn't easily abstracted away from it. Not to mention that using C++
libs from Postgres has complexities of its own.

I looked around for a plain C implementation of Bitcoin and found a few
rather incomplete ones. The most functional one seems to be Jeff Garzik's
[picocoin](https://github.com/jgarzik/picocoin). With the looming
[Segwit2x fork](https://bitcointechtalk.com/how-segwit2x-replay-protection-works-1a5e41767103)
and all the controversy surrounding it this may seem like an odd
choice of a library, but for the purpose of what we are doing, I think
it's fine. It also seems like Picocoin isn't actively developed,
which is not great. I would very much appreciate opinions/advice on this, if
you know of a better C lib, do leave a comment.

### The C extension ###

Thanks to this excellent [series of posts](http://big-elephants.com/2015-10/writing-postgres-extensions-part-i/)
and Postgres' superb documentation, I was able to put together a proof-of-concept extension,
available at [https://github.com/blkchain/pg_blkchain](https://github.com/blkchain/pg_blkchain).
While the C internals of it would be subject for a whole separate post (or
few), suffice it to say that it is fairly rudimentary and all the
heavy lifting is delegated to the picocoin lib.

As of now, the extension provides a handful of functions:

* `get_vin(tx bytea)` This is a [Set Returning Function](https://www.postgresql.org/docs/current/static/functions-srf.html) (SRF),
  which returns the transaction inputs as rows.

* `get_vout(tx bytea)` Similarly to get_vin(), an SRF that returns outputs.

* `parse_script(script bytea)` An SRF which parses a Bitcoin script and returns (more or less) human-readable rows.

* `verify_sig(tx bytea, previous_tx bytea, n int)` Verifies a specific input of a transaction (denoted by `n`),
given a the previous transaction to which the input refers. Returns a boolean.

This is hardly enough to support all of what would be required by a
full node, but this is sufficient to do some interesting stuff.

Note that the function names and signatures are not final, this is a
work in progress and I expect this all to evolve and change. For
example, initially I implemented get_vout() which returned an array,
but in the end an SRF seemed like a more flexible approach.

### The Schema ###

In the last post I used separate tables for the transaction, inputs
and outputs. With the ability to serialize/deserialize transactions at
our disposal, there are more interesting options.

The most compact way to store transactions is to just use the
serialized binary form in a binary (bytea) column. We can get at any
particulars of it by using our functions.

The examples below are based on a single table created as

{% codeblock lang:sql %}
CREATE TABLE rtxs (
   id            BIGINT NOT NULL,
   tx            BYTEA NOT NULL
);
{% endcodeblock %}

I imported the first 100K blocks or so into this table, how it was
done I might describe in a separate post.

I'll introduce the extension with my favorite example: the decoding of the
signature of the genesis block [input](https://blockchain.info/tx/4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b):

{% codeblock lang:sql %}
SELECT (sig).op_sym, encode((sig).data, 'escape')
  FROM (
    SELECT parse_script((get_vin(tx)).scriptSig) AS sig FROM rtxs
    WHERE digest(digest(tx, 'sha256'), 'sha256') = E'\\x3ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a'
  ) x;
   op_sym    |                                encode
-------------+-----------------------------------------------------------------------
 OP_PUSHDATA | \377\377\000\x1D
 OP_PUSHDATA | \x04
 OP_PUSHDATA | The Times 03/Jan/2009 Chancellor on brink of second bailout for banks
{% endcodeblock %}

### Expression Indexes ###

One neat feature of PostgreSQL is ability to
[index expressions](https://www.postgresql.org/docs/current/static/indexes-expressional.html).
For example, we know that we can compute a transaction hash with

{% codeblock lang:sql %}
select digest(digest(tx, 'sha256'), 'sha256') from rtxs limit 1;
                               digest
--------------------------------------------------------------------
 \x6e29b04a029e308344995fab2b75e953e1efa914d306ad47c14a3cebc84564fd
{% endcodeblock %}

Note that this is [little-endian](https://en.wikipedia.org/wiki/Endianness),
while conventionally transaction id's are represented with bytes
reversed (big-endian): [fd6445c8eb3c4ac147ad06d314a9efe153e9752bab5f994483309e024ab0296e](https://blockchain.info/tx/fd6445c8eb3c4ac147ad06d314a9efe153e9752bab5f994483309e024ab0296e)

Now if we want to be able to look up transactions quickly by the
transaction hash, as is the convention, we can create an expression
index like so:

{% codeblock lang:sql %}
CREATE INDEX ON rtxs(digest(digest(tx, 'sha256'), 'sha256'));
{% endcodeblock %}

When we do this, PostgreSQL scans the entire table, computes the hash
and stores it in the index. An index, after all, is just another table
(of sorts), and there is nothing wrong with indexes containing values
that do not exist in the table to which the index refers.

Once we do this, any time the expression `digest(digest(tx, 'sha256'), 'sha256')`
is used in reference to the `rtxs` table, PostgreSQL will not execute
the `digest()` function, but would instead use the value stored in
the index.

We can attest to this with

{% codeblock lang:sql %}
explain analyze SELECT id
FROM rtxs
WHERE digest(digest(tx, 'sha256'), 'sha256') = E'\\x6e29b04a029e308344995fab2b75e953e1efa914d306ad47c14a3cebc84564fd';
                                                                    QUERY PLAN
--------------------------------------------------------------------------------------------------------------------------------------------------
 Index Scan using rtxs_digest_idx on rtxs  (cost=0.42..8.44 rows=1 width=8) (actual time=0.020..0.020 rows=1 loops=1)
   Index Cond: (digest(digest(tx, 'sha256'::text), 'sha256'::text) = '\x6e29b04a029e308344995fab2b75e953e1efa914d306ad47c14a3cebc84564fd'::bytea)
 Planning time: 0.077 ms
 Execution time: 0.037 ms
(4 rows)
{% endcodeblock %}

This is pretty clever - even though we do not have an actual
"transaction hash" column in our table, we do have the value and an
index in the database.

### Views ###

But what if we wanted to have a better readable representation of
transactions, for example something that includes the transaction
hash?

The best way to do this is via a view:

{% codeblock lang:sql %}
CREATE VIEW tx_view AS
  SELECT id, digest(digest(tx, 'sha256'), 'sha256') AS txid, tx
    FROM rtxs;
{% endcodeblock %}

Postgres is clever enough to use the above index for the view:

{% codeblock lang:sql %}
explain analyze SELECT * FROM tx_view
 WHERE txid = E'\\x6e29b04a029e308344995fab2b75e953e1efa914d306ad47c14a3cebc84564fd';
--------------------------------------------------------------------------------------------------------------------------------------------------
 Index Scan using rtxs_digest_idx on rtxs  (cost=0.42..8.45 rows=1 width=318) (actual time=0.045..0.046 rows=1 loops=1)
   Index Cond: (digest(digest(tx, 'sha256'::text), 'sha256'::text) = '\x6e29b04a029e308344995fab2b75e953e1efa914d306ad47c14a3cebc84564fd'::bytea)
 Planning time: 0.104 ms
 Execution time: 0.067 ms
{% endcodeblock %}

A similar technique can applied to inputs and outputs, for example for
outputs we could create a view like so:

{% codeblock lang:sql %}
CREATE VIEW rtxouts AS
 SELECT id, (vout).n, (vout).value, (vout).scriptpubkey
  FROM ( SELECT id, get_vout(tx) vout FROM rtxs) x;
{% endcodeblock %}

The outputs are now easily accessibly as:

{% codeblock lang:sql %}
# select * from rtxouts limit 3;
 id | n |   value    |                                                               scriptpubkey
----+---+------------+------------------------------------------------------------------------------------------------------------------------------------------
  1 | 0 | 5000000000 | \x4104678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5fac
  2 | 0 | 5000000000 | \x410496b538e853519c726a2c91e61ec11600ae1390813a627c66fb8be7947be63c52da7589379515d4e0a604f8141781e62294721166bf621e73a82cbf2342c858eeac
  3 | 0 | 5000000000 | \x41047211a824f55b505228e4c3d5194c1fcfaa15a456abdf37f9b9d97a4040afc073dee6c89064984f03385237d92167c13e236446b417ab79a0fcae412ae3316b77ac
(3 rows)
{% endcodeblock %}

Want to know the most popular opcode used in scripts?

{% codeblock lang:sql %}
--Note: this is obviously not the full blockchain

SELECT (parse_script(scriptpubkey)).op_sym, count(1)
  FROM (SELECT scriptpubkey FROM rtxouts) x
GROUP BY op_sym
ORDER BY count(1);
  op_sym     |  count
----------------+---------
 OP_NOP         |       5
 OP_DUP         | 1007586
 OP_EQUALVERIFY | 1007586
 OP_HASH160     | 1007586
 OP_PUSHDATA    | 1139431
 OP_CHECKSIG    | 1151434
(6 rows)
{% endcodeblock %}

Anyway, that's it for now. Please comment your questions/comments
below, or via twitter, I am very curious on what people think on this
approach!
