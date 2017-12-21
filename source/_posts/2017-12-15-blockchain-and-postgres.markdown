---
layout: post
title: "Blockchain and Postgres"
date: 2017-12-15 08:28
comments: true
categories:
published: false
---

In a [previous post](/blog/2017/10/10/postgre-as-a-full-node/) I wrote
some initial thoughts on storing the blockchain in Postgres. It's been
a couple of months and I've made some progress on this project. This
post documents the latest incarnation of the schema used in Postgres
to store the blockchain as well as thoughts on why it was decided to
be this way.

### Why Store the Blockchain in  Postgres? ###

Because there is a considerable advantage in the flexibility afforded
by storing the blockchain in a relational database. The gain comes in
all the features of a relational database, most importantly SQL, but
also transactions, referential integrity, triggers, as well as backups
and replication.

A tengential goal of this project is to learn (and share the
knowledge) of the blockchain data structures. There is no better way
to do this than to import it into Postgres and try to run a few
queries.

On the subject of efficiency of Postgres, it would be fair to state
that it is not going to be as space-efficient and as fast as the
LevelDb-based storage that Core nodes use. Core uses the blockchain in
a very specific and well understood way and the code is optimized for
this use case. We are not trying to improve on it, it is already
nearly perfect. However LevelDb will not let one run SQL queries
against the data, for example.

### Blockchain Data Structure Overview ###

The blockchain consists of *blocks*. A block is a set of
*transactions*. A block also contains some block-specific information,
including the Proof-Of-Work which validates the block.

A transaction consist of *inputs* and *outputs*. The inputs reference
outputs from prior transactions, which may include transactions in the
same block. When an output is referenced by an input it is considered
spent in its entirety, i.e. there is no way to spend a part of an
output.

Note that a transaction's inputs are allowed to reference an output
more than once within the same transaction. When two *different*
transactions reference the same output, it is considered a *double
spend*, and only one of the spending transaction is valid (the details
of how validity is determined are outside the scope of this write up).

The transaction input value is the sum of its inputs. The transaction
output is the sum of its outputs. Naturally the output value cannot
exceed the input value, but it is normal for the output value to be
*less* than the input value. The discrepancy between the input and the
output is the transaction *fee* and is taken by the miner solving the
block in which the transaction is included.

The first transaction in a block is referred to as the
*coinbase*. Coinbase is a special transaction where the inputs refer
to a (non-existent) transaction hash of all zeros. Coinbase outputs
are the sum of all the fees and the *miner reward*.

Curiously it is possible for the same coinbase to be included in more
than one block, and there is at least one case of this in the
blockchain. The implication of this is that the second instance of
such a transaction is unspendable. This oddity was addressed by a
change in the consensus which requires the block *height* to be
referenced in the coinbase and is no longer possible.

The same transaction can be included in more than one block. This is
common during chain splits, i.e. when more than one miner solves a
block. Eventually one of such blocks will become *orphaned*, but there
is a period of time during which it is not known which chain is
considered "best", and because of that the database structure needs to
accomodate this. Chain splits also cause multiple blocks to have the
same height which implies that height alone cannot identify a
particular block.

### Row Ids and Hashes ###

In the blockchain blocks and transactions are always referred to
through their *hash*. A hash is an array of 32 bytes. While in theory
we could build a schema which relies on the hash as the record
identifier, in practice it is cumbersome compared to the traditional
integer ids. Firstly, 32 bytes is four times larger than a BIGINT and
eight times larger than an INT, which impacts greatly the amount of
space required to store inputs and outputs as well as degrades index
performance. For this reason we use INT for block ids and BIGINT for
transaction ids (INT is not big enough and would overflow in a few
years).

There is also an ambiguity in how the hash is printed versus how it is
stored. While the SHA standard does not specify the endian-ness of the
hash and refers to it as an array of bytes, Satoshi Nakomoto decided
to treat hashes as little-endian 256-bit integers. The implication
being that when the hash is printed (as a transaction id) the order of
bytes is the reverse of how it is stored in the blockchain.

Using integer ids creates a complication in how inputs reference
outputs. Whereas in the blockchain it is done entirely via a
transaction hash, here we need to also store the integer id of the
referenced transaction (`prevout_tx_id`). This is an easily
justifiable optimization, without it to lookup the input transaction
would require first finding the transaction integer id. The downside
is that during the initial import maintaining the hash to integer id
correspondence in an efficient manner is bit of a challenge.

### Blocks ###

Blocks are
