---
layout: post
title: "The Bitcoin Blockchain PostgresSQL Schema"
date: 2017-12-15 08:28
comments: true
categories:
published: true
---

In a [previous post](/blog/2017/10/10/postgre-as-a-full-node/) I wrote
some initial thoughts on storing the blockchain in Postgres. It's been
a couple of months and I've made some progress on the
[import project](https://github.com/blkchain/blkchain). This post documents
the latest incarnation of the SQL schema used to store the
blockchain as well as thoughts on why it was decided to be this way.

## Blockchain Data Structure Overview ##

The [Bitcoin blockchain](https://bitcoin.org/en/developer-reference#block-chain)
consists of *[blocks](https://bitcoin.org/en/developer-reference#serialized-blocks)*.
A block is a set of *[transactions](https://bitcoin.org/en/developer-reference#raw-transaction-format)*.
A block also contains some [block-specific information](https://bitcoin.org/en/developer-reference#block-headers),
such as the nonce for the [Proof-Of-Work](https://en.bitcoin.it/wiki/Proof_of_work) validating the block.

A transaction consist of *inputs* and *outputs*. The inputs reference
outputs from prior transactions, which may include transactions in the
same block. When an output is referenced by an input, the output is
considered spent in its entirety, i.e. there is no way to spend a part
of an output.

When two *different* transactions' inputs reference the same output, it is
considered a *[double spend](https://en.wikipedia.org/wiki/Double-spending)*,
and only one of the spending transactions is valid (the details
of how validity is determined are outside the scope of this write up).

A transaction's input value is the sum of its inputs and the output
value is the sum of its outputs. Naturally, the output value cannot
exceed the input value, but it is normal for the output value to be
*less* than the input value. The discrepancy between the input and the
output is the transaction *[fee](https://en.bitcoin.it/wiki/Transaction_fees)*
and is taken by the miner solving the block in which the transaction is included.

The first transaction in a block is referred to as the
*coinbase*. Coinbase is a special transaction where the inputs refer
to a (non-existent) transaction hash of all zeros. Coinbase outputs
are the sum of all the fees and the *[miner reward](https://en.bitcoin.it/wiki/Mining#Reward)*.

Curiously it is possible for the same coinbase transaction to be
included in more than one block, and there is at least
[one case](https://blockchain.info/tx/e3bf3d07d4b0375638d5f1db5255fe07ba2c4cb067cd81b84ee974b6585fb468)
of this in the blockchain. The implication of this is that the second
instance of such a transaction is unspendable. This oddity was
addressed by a change in the consensus which requires the block
*height* to be referenced in the coinbase and is since then no longer
possible (see [BIP30](https://github.com/bitcoin/bips/blob/master/bip-0030.mediawiki).

The same transaction can be included in more than one block. This is
common during chain splits, i.e. when more than one miner solves a
block. Eventually one of such blocks will become *orphaned*, but there
is a period of time during which it is not known which chain is
considered "best", and the database structure needs to accommodate
this. Chain splits also cause multiple blocks to have the same height
which implies that height alone cannot identify a particular block or
that it is unique.

With introduction of *SegWit* transactions also include *witness*
data. Witness is stored at the end of a transaction as a list where
each entry corresponds to an input. A witness entry is in turn a list,
because an input can have multiple signatures (aka witness). Presently
per-input witness list is stored in the input record as a BYTEA.

## Row Ids and Hashes ##

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

## Integers ##

Most integers in Core are defined as `uint32_t`, which is an unsigned
4-byte integer. Postgres 4-byte `INT` is signed, which presents us
with two options: (1) use `BIGINT` instead, or (2) use `INT` with the
understanding that larger values may appear as negative. We are opting
for the latter as preserving space is more important and for as long as
all the bits are correct, whether the integer is interpreted as signed
or unsigned is of no consequence.

## Blocks ##

Blocks are collections of transactions. It is a many-to-many
relationship as multiple blocks can include to the same transaction. The
[CBlockHeader](https://github.com/bitcoin/bitcoin/blob/0.15/src/primitives/block.h#L20)
is defined in Core as follows:

``` c++
class CBlockHeader
{
public:
    // header
    int32_t nVersion;
    uint256 hashPrevBlock;
    uint256 hashMerkleRoot;
    uint32_t nTime;
    uint32_t nBits;
    uint32_t nNonce;
```

Our `blocks` table is defined as follows:

``` sql
  CREATE TABLE blocks (
   id           SERIAL
  ,height       INT NOT NULL
  ,hash         BYTEA NOT NULL
  ,version      INT NOT NULL
  ,prevhash     BYTEA NOT NULL
  ,merkleroot   BYTEA NOT NULL
  ,time         INT NOT NULL
  ,bits         INT NOT NULL
  ,nonce        INT NOT NULL
  ,orphan       BOOLEAN NOT NULL DEFAULT false
  ,status       INT NOT NULL
  ,filen        INT NOT NULL
  ,filepos      INT NOT NULL
  );

```

Columns `orphan`, `status`, `filen` and `filepos` are from the
[CBlockIndex](https://github.com/bitcoin/bitcoin/blob/0.15/src/chain.h#L170)
class which is serialized in LevelDb and contains information about
the file in which the block was stored on-disk as far as Core is
concerned. This information is only necessary for debugging purposes,
also note that it is unique to the particular instance of the Core
database, i.e. if you were to wipe it and download the chain from
scratch, location and even status of blocks is likely to be different.

Note that the C++ `CBlockHeader` class does not actually include the
hash, it is computed on-the-fly as needed. Same is true with respect
to transactions and its hash.

We also need a many-to-many link to transactions, which is the
`block_txs` table. Not only do we need to record that a transaction is
included in a block, but also its exact position relative to other
transactions, denoted by the `n` column:

``` sql
  CREATE TABLE block_txs (
   block_id      INT NOT NULL
  ,n             INT NOT NULL
  ,tx_id         BIGINT NOT NULL
  );

```

### Transactions ###

A transaction is a collection of inputs and outputs. The
[CTransaction](https://github.com/bitcoin/bitcoin/blob/0.15/src/primitives/transaction.h#L264)
C++ class is defined as follows:

``` c++
class CTransaction
{
public:
    const int32_t nVersion;
    const std::vector<CTxIn> vin;
    const std::vector<CTxOut> vout;
    const uint32_t nLockTime;
```

In Postgres transactions are in the `txs` table:

``` sql
  CREATE TABLE txs (
   id            BIGSERIAL
  ,txid          BYTEA NOT NULL
  ,version       INT NOT NULL
  ,locktime      INT NOT NULL
  );

```

The `txid` column is the transaction hash and should not be confused
with `tx_id` in other tables referencing the transaction. ("txid" is
what the transaction hash is typically called in code and
documentation).

## Outputs ##

In Core an output is represented by the
[CTxOut](https://github.com/bitcoin/bitcoin/blob/0.15/src/primitives/transaction.h#L131)
class:

``` c++
class CTxOut
{
public:
    CAmount nValue;
    CScript scriptPubKey;
```

The `CAmount` type above is a `typedef int64_t`, it is the value of
the output in *satoshis* which can be as high as `21M * 100M` (the
number of satoshis in a bitcoin).

In SQL, an output looks like this:

``` sql
  CREATE TABLE txouts (
   tx_id        BIGINT NOT NULL
  ,n            INT NOT NULL
  ,value        BIGINT NOT NULL
  ,scriptpubkey BYTEA NOT NULL
  ,spent        BOOL NOT NULL
  );
```

The `tx_id` column is the transaction to which this input belongs, `n`
is the position within the input list.

The `spent` column is an optimization, it is not part of the
blockchain. An output is spent if an input is referencing it. Core
maintains a separate LevelDb dataset called the *UTXO Set* (Unspent
Transaction Output Set) which contains all unspent outputs. The reason
Core does it this way is because by default it does not index
transactions, i.e. Core actually does not have a way of quickly
retrieving a transaction from the store as there generally is no need
for such retrieval as part of a node operation, while the UTXO Set is
both sufficient and smaller than a full transaction index. Since in
Postgres we have no choice but to index transactions, there is no
benefit in having UTXOs as a separate table, the `spent` flag serves
this purpose instead.

The UTXO Set does not include any outputs with the value of 0, since
there is nothing to spend there even though no input refers to them
and they are not technically spent.

## Inputs ##

An input in Core is represented by the
[CTxIn](https://github.com/bitcoin/bitcoin/blob/0.15/src/primitives/transaction.h#L61)
class, which looks like this:

``` c++
class CTxIn
{
public:
    COutPoint prevout;
    CScript scriptSig;
    uint32_t nSequence;
    CScriptWitness scriptWitness;
```

The `COutPoint` class is a combination of a hash and an integer
representing an output. `CScriptWitness` is an array of "witnesses" or
(roughly speaking) signatures, which are byte arrays, just like the
`scriptSig`.

In our schema, an input is defined as:

``` sql
  CREATE TABLE txins (
   tx_id         BIGINT NOT NULL
  ,n             INT NOT NULL
  ,prevout_hash  BYTEA NOT NULL
  ,prevout_n     INT NOT NULL
  ,scriptsig     BYTEA NOT NULL
  ,sequence      INT NOT NULL
  ,witness       BYTEA
  ,prevout_tx_id BIGINT
  );
```

As we already mentioned above `witness` is stored as opaque bytes. The
`prevout_tx_id` is the database row id of the transaction this input
is spending.

## Indexes and Foreign Key Constraints ##

Blocks and transactions are indexed by `id` as their primary index.
Blocks also need an index on `hash` (unique), as well as on `height`
and on `prevhash` (not unique).  Transactions need a unique index on
the `txid`.

Inputs and outputs need `(tx_id, n)` as primary indexes. Inputs are
also indexed on `(prevout_tx_id, prevout_n)` so that we can quickly
identify the spending input given an output.

Finally, we need a basic set of foreign key constraints that ensure
the integrity between all the related tables.

## Triggers ##

The `spent` column in the output and the `prevout_tx_id` of an input
are maintained by a trigger on the `txins` table. Every time an input
is inserted, it locates the database id of the transaction it spends
as well as updates the `spent` flag of the corresponding output.

Technically it is done using two triggers for performance
reasons. This is because a trigger that modifies the row being
inserted must be a BEFORE trigger, but BEFORE triggers are not allowed
to be to be CONSTRAINT triggers. CONSTRAINT triggers have the
advantage of being *deferrable*, i.e. they can be postponed until
(database) transaction commit time. Deferring constraints can speed up
inserts considerably, for this reason the code that updates `spent` is
in a separate AFTER trigger.

The trigger code is still rough around the edges, but here it is for
posterity anyway:

``` sql
CREATE OR REPLACE FUNCTION txins_before_trigger_func() RETURNS TRIGGER AS $$
  BEGIN
    IF (TG_OP = 'UPDATE' OR TG_OP = 'INSERT') THEN
      IF NEW.prevout_n <> -1 AND NEW.prevout_tx_id IS NULL THEN
        SELECT id INTO NEW.prevout_tx_id FROM txs WHERE txid = NEW.prevout_hash;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'Unknown prevout_hash %', NEW.prevout_hash;
        END IF;
      END IF;
      RETURN NEW;
    END IF;
    RETURN NULL;
  END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER txins_before_trigger
BEFORE INSERT OR UPDATE OR DELETE ON txins
  FOR EACH ROW EXECUTE PROCEDURE txins_before_trigger_func();

CREATE OR REPLACE FUNCTION txins_after_trigger_func() RETURNS TRIGGER AS $$
  BEGIN
    IF (TG_OP = 'DELETE') THEN
      IF OLD.prevout_tx_id IS NOT NULL THEN
        UPDATE txouts SET spent = FALSE
         WHERE tx_id = prevout_tx_id AND n = OLD.prevout_n;
      END IF;
      RETURN OLD;
    ELSIF (TG_OP = 'UPDATE' OR TG_OP = 'INSERT') THEN
      IF NEW.prevout_tx_id IS NOT NULL THEN
        UPDATE txouts SET spent = TRUE
         WHERE tx_id = NEW.prevout_tx_id AND n = NEW.prevout_n;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'Unknown prevout_n % in txid % (id %)', NEW.prevout_n, NEW.prevout_hash, NEW.prevout_tx_id;
        END IF;
      END IF;
      RETURN NEW;
    END IF;
    RETURN NULL;
  END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER txins_after_trigger
AFTER INSERT OR UPDATE OR DELETE ON txins DEFERRABLE
  FOR EACH ROW EXECUTE PROCEDURE txins_after_trigger_func();

```

## Identifying Orphaned Blocks ##

While this is not part of the schema, I thought it would be
interesting to the potential readers. An orphaned block is a block to
which no other `prevhash` refers. At the time of a chain split we
start out with two blocks referring to the same block as previous, but
the next block to arrive will identify one of the two as its previous
thereby orphaning the other of the pair.

To identify orphans we need to walk the chain backwards starting from
the highest height. Any block that this walk does not visit is an
orphan.

In SQL this can be done using the `WITH RECURSIVE` query like so:

``` sql
UPDATE blocks
   SET orphan = a.orphan
  FROM (
    SELECT blocks.id, x.id IS NULL AS orphan
      FROM blocks
      LEFT JOIN (
        WITH RECURSIVE recur(id, prevhash) AS (
          SELECT id, prevhash, 0 AS n
            FROM blocks
                            -- this should be faster than MAX(height)
           WHERE height IN (SELECT height FROM blocks ORDER BY height DESC LIMIT 1)
          UNION ALL
            SELECT blocks.id, blocks.prevhash, n+1 AS n
              FROM recur
              JOIN blocks ON blocks.hash = recur.prevhash
            %s
        )
        SELECT recur.id, recur.prevhash, n
          FROM recur
      ) x ON blocks.id = x.id
   ) a
  WHERE blocks.id = a.id;

```

The WITH RECURSIVE part connects rows by joining prevhash to hash,
thereby building a list which starts at the highest hight and going
towards the beginning until no parent can be found.

Then we LEFT JOIN the above to the blocks table, and where there is
no match (x.id IS NULL) we mark it as orphan.


## Conclusion ##

Devising this schema was surprisingly tedious and took many trial and
error attempts to reimport the entire blockchain which collectively
took weeks. Many different variations on how to optimize operations
were attempted, for example using an *expression index* to only index
a subset of a hash (first 10 bytes are still statistically unique),
etc.

I would love to hear comments from the database experts out there. I'm
not considering this version "final", there is probably still room for
improvement and new issues might be discovered as I progress to
writing up how to insert new blocks and actually verify blocks and
transactions.
