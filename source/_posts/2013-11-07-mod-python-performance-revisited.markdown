---
layout: post
title: "mod_python performance part 2: high(er) concurrency"
date: 2013-11-07 17:51
comments: true
categories:
---

### Tl;dr

As is evident from the table below, mod_python [3.5](https://github.com/grisha/mod_python/tree/3.5.x)
(in pre-release testing as of this writing) is currently the fastest tool when it
comes to running Python in your web server, and second-fastest as a
WSGI container.

<table border="1">
  <tr>
    <th>Server</th>
    <th>Version</th>
    <th>Req/s</th>
    <th>% of httpd static</th>
    <th>Notes</th>
  </tr>
  <tr>
    <th><a href="https://bitbucket.org/yarosla/nxweb/wiki/Benchmarks">nxweb</a> static file</th>
    <td>3.2.0-dev</td>
    <td>512,767</td>
    <td> 347.1 % </td>
    <td>"memcache":false. (626,270 if true)</td>
  </tr>
  <tr>
    <th><a href="http://nginx.com/">nginx</a> static file</th>
    <td>1.0.15</td>
    <td>430,135</td>
    <td> 291.1 %</td>
    <td>stock CentOS 6.3 rpm</td>
  </tr>
  <tr>
    <th><a href="http://httpd.apache.org/">httpd</a> static file</th>
    <td>2.4.4, mpm_event</td>
    <td>147,746</td>
    <td> 100.0 % </td>
    <td></td>
  </tr>
  <tr>
    <th>mod_python <a href="http://modpython.org/live/current/doc-html/pythonapi.html#overview-of-a-request-handler">handler</a></th>
    <td>3.5, Python 2.7.5</td>
    <td>125,139</td>
    <td> 84.7 % </td>
    <td></td>
  </tr>
  <tr>
    <th><a href="https://uwsgi-docs.readthedocs.org/en/latest/">uWSGI</a></th>
    <td>1.9.18.2</td>
    <td>119,175</td>
    <td> 80.7 % </td>
    <td>-p 16 --threads 1</td>
  </tr>
  <tr>
    <th>mod_python <a href="http://modpython.org/live/current/doc-html/handlers.html#wsgi-handler">wsgi</a></th>
    <td>3.5, Python 2.7.5</td>
    <td>87,304</td>
    <td> 59.1 % </td>
    <td></td>
  </tr>
  <tr>
    <th><a href="http://code.google.com/p/modwsgi/">mod_wsgi</a></th>
    <td>3.4</td>
    <td>76,251</td>
    <td> 51.6 % </td>
    <td>embedded mode</td>
  </tr>
  <tr>
    <th>nxweb wsgi</th>
    <td>3.2.0-dev, Python 2.7.5</td>
    <td>15,141</td>
    <td> 10.2 % </td>
    <td>posibly misconfigured?</td>
  </tr>
</table>

## The point of this test

I wanted to see how mod_python compares to other tools of similar
purpose on high-end hardware and with relatively high concurrency. As
I've [written before](http://grisha.org/blog/2013/10/10/mod-python-performance/)
you'd be foolish to base your platform decision on these numbers
because speed in this case matters very little. So the point of this
is just make sure that mod_python is in the ballpark with the rest and
that there isn't anything seriously wrong with it. And surprisingly,
mod_python is actually pretty fast, *fastest*, even, though in its own
category (a raw mod_python handler).

## Test rig

The server is a 24-core Intel Xeon 3GHz with 64GB RAM, running Linux
2.6.32 (CentOS 6.3).

The testing was done with
[httpress](https://bitbucket.org/yarosla/httpress/wiki/Home), which
was chosen after having tried
[ab](http://httpd.apache.org/docs/2.4/programs/ab.html),
[httperf](http://www.hpl.hp.com/research/linux/httperf/) and
[weighttp](http://redmine.lighttpd.net/projects/weighttp/wiki). The exact command was:

```
httpress -n 5000000 -c 120 -t 8 -k http://127.0.0.1/
```

Concurrency of 120 was chosen as the highest number I could run across
all setups without getting strange errors. "Strange errors" could be
disconnects, delays and stuck connections, all tunable by anything
from Linux kernel configuration to specific tool configs. I very much
wanted concurrency to be at least a few times higher but it quickly
became apparent that getting to that level would require very
significant system tweaking for which I just didn't have the time. 120
concurrent requests is nothing to sneeze at though: if you sustained
this rate for a day of python handler serving, you'd have processed
10,812,009,600 requests (on a single server!).

I should also note that in my tweaking of various configurations I
couldn't get the requests/s numbers any significantly higher than what
you see above. Increasing concurrency and number of workers mostly
increased errors rather than r/s, which is also interesting because
it's important how gracefuly each of these tools fails, but failure
mode is a whole different subject.

The tests were done via the loopback (127.0.0.1) because having tried
hitting the server from outside it became apparent that the network
was the bottleneck.

Keepalives were in use (-k), which means that all of the 5 million
requests are processed over only about fifty thousand TCP
connections. Without keepalives this would be more of the Linux kernel
test because the bulk of the work establishing and taking down a
connection happens in the kernel.

Before running the 5 million requests I ran 100,000 as a "warm up".

This post does not include the actual code for the WSGI app and mod_python handlers because it was same as
in my [last post on mod_python performance testing](http://grisha.org/blog/2013/10/10/mod-python-performance/).

## Why httpress

[ab](http://httpd.apache.org/docs/2.4/programs/ab.html) simply can't run more than about 150K requests per second, so it
couldn't adequately test nxweb and nginx static file serving.

[httperf](http://www.hpl.hp.com/research/linux/httperf/) looked
promising at first, but as is [noted here](http://gwan.com/en_apachebench_httperf.html) its requests per
second cannot be trusted because it gradually increases the
load.

[weighttp](http://redmine.lighttpd.net/projects/weighttp/wiki) seemed
good, but somehow got stuck on idle but not yet closed connections
which affected the request/s negatively.

[httpress](https://bitbucket.org/yarosla/httpress/wiki/Home) claimed that it "promptly timeouts stucked connections,
forces all hanging connections to close after the main run, does not
allow hanging or interrupted connections to affect the measurement",
which is just what I needed. And it worked really great too.

## The choice of contenders

mod_python and mod_wsgi are the obvious choices, uWSGI/Nginx combo is
known as a low-resource and fast alternative. I came across nxweb
while looking at httpress (it's written by the same person
([Yaroslav Stavnichiy](https://bitbucket.org/yarosla)), it looks to be the
fastest (open source) web server currently out there, faster than (closed source)
G-WAN, even.

## Specific tool notes

The code used for testing and the configs were essentially same as what
I used in my [previous post on mod_python performance testing](http://grisha.org/blog/2013/10/10/mod-python-performance/).
The key differences are listed below.

### Apache

The key config on Apache was:

```
ThreadsPerChild 25    # default
StartServers 16
MinSpareThreads 400
```

MinSpareThreads ensures that Apache starts all possible processes and
threads on startup (25 * 16 = 400) so that there is no ramp up
period and it's tsunami-ready right away.

### uWSGI

The comparison with uWSGI isn't entriely appropriate because it was
running listening on a unix domain socket behind Nginx. The -p 16
--threads 1 (16 worker processes with a single thread each) was chosen
as the best performing option after some experimentation. Upping -p to
32 reduced r/s to 86233, 64 to 47296. Upping --threads to 2 (with 16
workers) reduced r/s to 55925 (by half, which is weird - mod_python has no
problems with 25 threads). --single-interpreter didn't seem to have
any significant impact.

The actual uWSGI command was:

```
uwsgi -s logs/uwsgi.sock --pp htdocs  -M -p 16 --threads 1 -w mp_wsgi -z 30 -l 120 -L
```

A note on the uWSGI performance. Initially it seemed to be
outperforming the mod_python handler by nearly a factor of two. Then
after all kinds of puzzled head-scratching, I decided to verify that
every hit ran my Python code - I did this by writing a dot to a file
and making sure that the file size matches the number of hits in the
end. It turned out that about one third of the requests from Nginx to
uWSGI were erroring out, but httpress didn't see them as errors. So if
you're going to attempt to replicate this, watch out for this
condition. EDIT: Thanks to uWSGI's author Roberto De Loris' help, it
turned out that this was a result of misconfiguration on my part - the
-l parameter should be set higher than 120. (This explains how I
arrived at 120 as the concurrency chosen for the test too). The
request/s number and uWSGI's position in my table is still correct.

### Nginx

The relevant parts of the nginx config were (Note: this is not the
complete config for brevity):

```
worker_processes 24;
...
events {
  worker_connections 1024;
}
...
http {
  server_tokens off;
  keepalive_timeout 65;
  sendfile on;
  tcp_nopush on;
  tcp_nodelay on;

  access_log /dev/null main;
...
  upstream uwsgi {
     ip_hash;
     server unix:logs/uwsgi.sock;
  }
...
```

### Conclusion

Mod_python is plenty fast. Considering that unlike with other
contenders large parts of the code are written in Python and thus are
readable and debuggable by not just C programmers, it's quite a feat.

I was surprised by Apache's slow static file serving compared to Nginx
and Nxweb (the latter, although still young and in development seems like a
very cool web server).

On the other hand I am not all that convinced that the Nginx/uWSGI set
up is as cool as it is touted everywhere. Unquestionably Nginx is a
super solid server and Apache has some catching up to do when it comes
to acting as a static file server or a reverse proxy. But when it
comes to serving Python-generated content, my money would be on Apache
rather than uWSGI. The "low" 120 concurrency level for this test was
largely chosen because of uWSGI (Apache started going haywire on me at
about 400+ concurrent connections). EDIT: Thanks to Roberto's comment,
this turned out to be an error on my part (see comments). uWSGI can
handle higher concurrencies if -l is set higher.

It's also interesting that on my laptop a mod_python handler
outperformed the Apache static file, but it wasn't the case on the big
server.

I didn't do Python 3 testing, it would be interesting to see how much
difference it makes as well.

I realize this post may be missing key config data - I had to leave
out a lot because of time contraints (and my lazyness) - so if you see
any obvious gaps, please comment, I will try to address them.

P.S. Did I mention mod_python 3.5 supports Python 3? Please help
me [test it](https://github.com/grisha/mod_python/issues/9)!

<p>
<iframe src="http://ghbtns.com/github-btn.html?user=grisha&repo=mod_python&type=watch&count=true&size=large"
  allowtransparency="true" frameborder="0" scrolling="0" width="170" height="30"></iframe>

<iframe src="http://ghbtns.com/github-btn.html?user=grisha&repo=mod_python&type=fork&count=true&size=large"
  allowtransparency="true" frameborder="0" scrolling="0" width="170" height="30"></iframe>

<a href="https://twitter.com/mod_python" class="twitter-follow-button" data-show-count="false" data-size="large">Follow @mod_python</a>
<script>!function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0],p=/^http:/.test(d.location)?'http':'https';if(!d.getElementById(id)){js=d.createElement(s);js.id=id;js.src=p+'://platform.twitter.com/widgets.js';fjs.parentNode.insertBefore(js,fjs);}}(document, 'script', 'twitter-wjs');</script>
</p>
