---
layout: post
title: "Tgres Load Testing Follow Up"
date: 2017-02-28 21:40
comments: true
categories:
---

To follow up on the [previous post](/blog/2017/02/23/can-tgres-outperform-graphite/),
after a bunch
of tweaking, here is Tgres ([commit](https://github.com/tgres/tgres/commit/90924e4afa4ac8bef61caf46c3439794983660ec)) receiving over 150,000 data points per
second across 500,000 time series without any signs of the queue size
or any other resource blowing up.

This is both Tgres and Postgres running on the same i2.2xlarge EC2 instance (8 cores, 64GB, SSD).

{% img /images/tgres_aws1_150k.png %}

At this point I think there's been enough load testing and optimization, and I am
going to get back to crossing the t's and dotting the i's so that we can release
the first version of Tgres.
