---
layout: post
title: "Bitcoin Transaction Hash in Pure PostgreSQL"
date: 2017-10-10 17:54
comments: true
published: true
categories:
---

Update: hacked together
[this](https://github.com/blkchain/pg_blkchain), more details to
follow later...

In theory, Postgres should be able to verify transactions and blocks,
as well as do a lot of other things that are currently only done by
full nodes. For this to be performant, it will most likely require an
extension written in C, but I'm curious how far we can get with bare
bones Postgres.

More importantly, would that actually be useful? A node is really
just a database, a very efficient one for a very specific purpose, but
would leveraging the full power of Postgres be somehow more beneficial
than just running Bitcoin-Qt or btcd, for example?

To get to the bottom of this would be a lot of work, and potentially a
lot of fun. It would also be a great blockchain learning exercise. (If
you're working on a PG extension for Bitcoin or more generally
blockchain, please do let me know!)

### Random Thoughts ###

The structure of the Bitcoin blockchain is relatively simple.  We have
*transactions*, which in turn have *inputs* and *outputs* and belong
to *blocks*. Four tables, that's it.

I've been able to import the whole blockchain with some fairly basic
Go code into my old Thinkpad running Linux overnight. The Go code
needs some more polishing and is probably worthy of a separate write
up, so I won't get into it for now. Below is the schema I used. I
intentionally left out referential integrity and indexes to keep it
simple and avoid premature optimization.

```
CREATE TABLE blocks (                     -- CBlockIndex (chain.h)
   id           BIGINT NOT NULL
  ,prev         BIGINT NOT NULL              -- .prev->nHeight  // genesis will have -1
  ,height       BIGINT NOT NULL              -- .nHeight
  ,hash         BYTEA NOT NULL            -- <computed>
  ,version      BIGINT NOT NULL              -- .nVersion
  ,prevhash     BYTEA NOT NULL            -- .pprev->GetBlockHash()
  ,merkleroot   BYTEA NOT NULL            -- .hashMerkleRoot
  ,time         BIGINT NOT NULL           -- .nTime
  ,bits         BIGINT NOT NULL           -- .nBits
  ,nonce        BIGINT NOT NULL           -- .nNonce
);

CREATE TABLE txs (
   id            BIGINT NOT NULL
  ,txid          BYTEA NOT NULL
  ,version       BIGINT NOT NULL
  ,locktime      BIGINT NOT NULL
);

CREATE TABLE txins (
   id            BIGINT NOT NULL
  ,tx_id         BIGINT NOT NULL
  ,n             BIGINT NOT NULL
  ,prevout_hash  BYTEA NOT NULL
  ,prevout_n     BIGINT NOT NULL
  ,scriptsig     BYTEA NOT NULL
  ,sequence      BIGINT NOT NULL
);

CREATE TABLE txouts (
   id           BIGINT NOT NULL
  ,tx_id        BIGINT NOT NULL
  ,n            BIGINT NOT NULL
  ,value        BIGINT NOT NULL
  ,scriptpubkey BYTEA NOT NULL
);

```

There are a couple projects out there that keep the blockchain in a
database, most notably
[Abe](https://github.com/bitcoin-abe/bitcoin-abe). I haven't studied
the code very carefully, but my initial impression was that Abe tries
to use standard SQL that would work across most big databases, which
is philosophically different from my objective of going 100% Postgres
and leveraging all that it can do for us.

Bitcoin uses a lot of uint32's. A Postgres INT is the correct size,
but it is signed, which means we have to use the next larger type,
BIGINT. It seems like it might be a waste to use 64 bits for a 32-bit
value, but I couldn't think of anything better than a BIGINT. For the
binary stuff it seems like BYTEA is the best match.

So what can we do with this? There is no easy way to create or verify an
[Elliptic Curve signature](https://en.wikipedia.org/wiki/Elliptic_Curve_Digital_Signature_Algorithm)
in Postgres, but with the help of the [pgcrypto](https://www.postgresql.org/docs/current/static/pgcrypto.html)
extension, we should be able to at least generate the correct SHA256
digest which is used in the signature. As a side note, EC signature math is actually
remarkably simple and could probably be implemented
as a PG function, but I'm too lazy. Here it is in a
[few lines of Python](https://github.com/wobine/blackboard101/blob/master/EllipticCurvesPart5-TheMagic-SigningAndVerifying.py).

The rules on how Bitcoin generates the hash (which is then signed) are
slightly [complicated](https://en.bitcoin.it/w/images/en/7/70/Bitcoin_OpCheckSig_InDetail.png), and that's an
[understatement](https://lists.linuxfoundation.org/pipermail/bitcoin-dev/2014-November/006878.html).

For the purposes of this exercise, I'd just be happy with a value that
matches, even if the code does not fully comply with the Bitcoin rules.

One problem I ran into was that, because Bitcoin blockchain is
little-endian except for where it isn't, you often need a way to
reverse bytes in a BYTEA. Strangely, Postgres does not provide a way
to do that, unless I'm missing something. But thanks to
[stackoverflow](https://stackoverflow.com/questions/11142235/convert-bigint-to-bytea-but-swap-the-byte-order),
here is one way to do this:

{% codeblock lang:sql %}
CREATE OR REPLACE FUNCTION reverse(bytea) RETURNS bytea AS $reverse$
    SELECT string_agg(byte,''::bytea)
       FROM (
          SELECT substr($1,i,1) byte
             FROM generate_series(length($1),1,-1) i) s
$reverse$ LANGUAGE sql;
{% endcodeblock %}

We also have no way to render a Bitcoin
[varint](https://en.bitcoin.it/wiki/Protocol_documentation#Variable_length_integer), but we can fake it
with some substringing for the time being.

Equipped with this, we can construct the following statement, sorry
it's a little long and I do not have the patience to explain it in
writing.

{% codeblock lang:sql %}
select digest(digest(tx_ser || hashtype, 'sha256'), 'sha256') as shasha from (
 select substring(reverse(int8send(version)) from 1 for 4) ||
       vin ||
       vout ||
       substring(reverse(int8send(locktime)) from 1 for 4) AS tx_ser,
       substring(reverse(int8send(1)) from 1 for 4) AS hashtype
  from txs t
  join txins tt ON tt.tx_id = t.id
  join lateral (
    select tx_id, substring(reverse(int8send(count(1))) from 1 for 1) || string_agg(txin_ser, '') as vin
    from (
      select
         ti.tx_id,
         reverse(prevout_hash) ||
         substring(reverse(int8send(prevout_n)) from 1 for 4) ||
         substring(reverse(int8send(length(CASE WHEN ti.n = tt.n THEN ptxout.scriptpubkey ELSE '' END))) from 1 for 1) ||
         CASE WHEN ti.n = tt.n THEN ptxout.scriptpubkey ELSE '' END ||
         substring(reverse(int8send(sequence)) from 1 for 4) as txin_ser
      from txins ti
      join txs ptx on ti.prevout_hash = ptx.txid
      join txouts ptxout on ptxout.tx_id = ptx.id and ti.prevout_n = ptxout.n
      order by ti.n
     ) x
   group by tx_id
   ) vin on vin.tx_id = tt.tx_id
   join (
      select tx_id, substring(reverse(int8send(count(1))) from 1 for 1) || string_agg(txout_ser, '') as vout
      from (
        select
          tx_id,
          reverse(int8send(value)) ||
          substring(reverse(int8send(length(scriptpubkey))) from 1 for 1) ||
          scriptpubkey as txout_ser
        from txouts
        order by n
        ) x
      group by tx_id
    ) out ON out.tx_id = tt.tx_id
 where tt.tx_id = 37898
) x;
-[ RECORD 1 ]--------------------------------------------------------------
shasha | \x23c3bf5091f3cdaf5996b0091c5f5bb6d82f3cdc2ce077018bb854f40274e512
-[ RECORD 2 ]--------------------------------------------------------------
shasha | \xbcd4d519931da3ab98ca9745a0ceba79f05306cad4fa6ee9863819d1783a2e00
{% endcodeblock %}

The particular transaction we are looking at is
[this](https://blockchain.info/tx/2847ae66175042438532c2eccc5b39935fd1216453e62e2c3cb9c8e5020cc771).
It happens to have id of 37898 in my database. In case you're
wondering, for this example I used a subset of the blockchain which
only has the first 182,000 blocks. On the full blockchain and without
indexes, this statement would have taken an eternity to execute.

What makes this particular transaction interesting is that it has two
inputs, which is slightly trickier, because to spend them, there need to
be two different signatures of the same transaction. This is because
before signing, the input scriptSig needs to be replaced with the
output's scriptPubKey (the oversimplified version). This is reflected in the SQL
in the use of `LATERAL` and `CASE`.

You do not have to take my word that the two hashes are correct, we
can verify them fairly easily with a bit of help from the Python ecdsa
library. Here is the code to verify the second hash. The key and the
signature are in the
[transaction itself](https://blockchain.info/tx/2847ae66175042438532c2eccc5b39935fd1216453e62e2c3cb9c8e5020cc771).

{% codeblock lang:python %}
import ecdsa
import codecs
key = codecs.decode(
    "04de99a4267263f495e07721f96241359b48b9f522973b9d333ed8e296357c595130535ca387601955f1406e335cf658bb6a12d62c177e9511498fefcafead1c0e",
    "hex")
der = '0V0\x10\x06\x07*\x86H\xce=\x02\x01\x06\x05+\x81\x04\x00\n\x03B\x00' + key
digest = codecs.decode("bcd4d519931da3ab98ca9745a0ceba79f05306cad4fa6ee9863819d1783a2e00", "hex")
signature = codecs.decode(
    "30460221008e95fd3536cfd437c49e4c1dfaeeb2ece0e521420c89f1487ca6eff94053485c022100ef3a8cdc9b0a6d6d403bf7758c6b617380db6936de2bbcd3b556ec5f45c03b54",
    "hex")
vk = ecdsa.VerifyingKey.from_der(der)
print vk.verify_digest(signature, digest, sigdecode=ecdsa.util.sigdecode_der)
# True
{% endcodeblock %}

I hope this was fun! Now I wonder how hard it would be to make an
extension to provide all the functionality required by Bitcoin....
