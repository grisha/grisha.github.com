---
layout: post
title: "Avro performance"
date: 2013-06-11 00:17
comments: true
categories: 
---

Here are some un-scientific results on how Avro performs with verious
codecs, as well as vs JSON-lzo files in Hive and Impala. This testing
was done using a 100 million row table that was generated using random
two strings and an integer.

```
| Format    | Codec          | Data Size     | Hive count(1) time | Impala count(1) time
|-----------|----------------|---------------|--------------------|----------------------
| JSON      | null           | 686,769,821   | not tested         | N/A                  
| JSON      | LZO            | 285,558,314   | 79s                | N/A                  
| JSON      | Deflate (gzip) | 175,878,038   | not tested         | N/A                  
| Avro      | null           | 301,710,126   | 40s                | .4s                  
| Avro      | Snappy         | 260,450,980   | 38s                | .9s                  
| Avro      | Deflate (gzip) | 156,550,144   | 64s                | 2.8s                 
```

So the winner appears to be Avro/Snappy or uncompressed Avro.
