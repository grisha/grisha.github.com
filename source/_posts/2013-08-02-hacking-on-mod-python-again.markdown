---
layout: post
title: "Hacking on mod_python (again)"
date: 2013-08-02 16:19
comments: true
categories: 
---

Nearly eight years after my last [commit](https://github.com/grisha/mod_python/commit/726e2697c0547dbbb4b09ce3348f76118bb911c4)
to [Mod_python](http://www.modpython.org/) I've decided to spend some time hacking on it again.

Five years without active development and thirteen since its first
release, it still seems to me an entirely useful and viable tool. The
code is exceptionally clean, the documentation is amazing, and the
test suite is awesome.  Which is a real testament to the noble efforts
of all the people who contributed to its development.

We live in this new
[c10k](http://en.wikipedia.org/wiki/C10k_problem) world now where
Apache Httpd no longer has the market dominance it once enjoyed, while
the latest Python web frameworks run without requiring or recommending
Mod_python. My hunch, however, is that given a thorough dusting it
could be quite useful (perhaps more than ever) and applied in very
interesting ways to solve the new problems. I also think the Python
language is at a very important inflection point. Pyhton 3 is now
mature, and is slowly but steadily becoming the preferred language of
many interesting communities such as data science, for example.

The current status of Mod_python as an Apache project is that it's
in the [attic](http://attic.apache.org/). This means that the
[ASF](http://www.apache.org/) isn't providing much in the way of
infrastructure support any longer, nor will you see an "official" ASF
release any time soon. (If ever - Mod_python would have to re-enter as
an [incubator](http://incubator.apache.org/) project and at this point
it is entirely premature to even consider such an option).

For now the main goal is to re-establish the community, and as part of
that I will have to sort out how to do issue tracking, discussion
groups, etc. At this point the only thing I've decided is that the
main repository will live on
[github](https://github.com/grisha/mod_python).

The latest code is in [4.0.x branch](https://github.com/grisha/mod_python/tree/4.0.x).  My initial
development goal is to bring it up to compatibility with Python 2.7
and Apache Httpd 2.4 (I'm nearly there already), then potentially move
on to Python 3 support. I have rolled back a few commits (most notably
the new importer) because I did not understand them. There are still a
few changes in Apache 2.4 that need to be addressed, but they seem
relatively minor at this point. Authentication has been changed
significantly in 2.4, though mod_python never had much coverage in that
area.

Let's see where this takes us? And if you like this, feel free to
star and fork [Mod_python](https://github.com/grisha/mod_python) on github and follow it on Twitter:

<p>
<iframe src="http://ghbtns.com/github-btn.html?user=grisha&repo=mod_python&type=watch&count=true&size=large"
  allowtransparency="true" frameborder="0" scrolling="0" width="170" height="30"></iframe>

<iframe src="http://ghbtns.com/github-btn.html?user=grisha&repo=mod_python&type=fork&count=true&size=large"
  allowtransparency="true" frameborder="0" scrolling="0" width="170" height="30"></iframe>

<a href="https://twitter.com/mod_python" class="twitter-follow-button" data-show-count="false" data-size="large">Follow @mod_python</a>
<script>!function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0],p=/^http:/.test(d.location)?'http':'https';if(!d.getElementById(id)){js=d.createElement(s);js.id=id;js.src=p+'://platform.twitter.com/widgets.js';fjs.parentNode.insertBefore(js,fjs);}}(document, 'script', 'twitter-wjs');</script>
</p>


