---
layout: post
title: "Building a Go Web App in 2017"
date: 2017-04-27 15:00
comments: true
categories:
published: true
---

Update: [part 2](/blog/2017/04/27/simplistic-go-web-app-part-2/) is
here, enjoy. And [part 3](/blog/2017/04/27/go-web-app-part-3/). And
[part 4](/blog/2017/04/27/go-web-app-part-4/).

A few weeks ago I started building yet another web-based app, in
[Go](https://golang.org/). Being mostly a back-end developer, I don't
have to write web apps very often, and every time I do, it seems like a great challenge.
I often wish someone would write a guide to web development for people
who do not have all day to get into the intricacies of great design
and just need to build a functional site that works without too much
fuss.

I've decided to use this opportunity to start from scratch and build
it to the best of my understanding of how an app ought to be built in
2017. I've spent many hours getting to the bottom of all things I've
typically avoided in the past, just so that for once in many years I
can claim to have a personal take on the matter and have a reusable
recipe that at least works for me, and hopefully not just me.

This post is the beginning of what I expect to be a short series
highlighting what I've learned in the process. The first post is a
general introduction describing the present problematic state of
affairs and why I think Go is a good choice. The subsequent posts have
more details and code. I am curious whether my experience resonates
with others, and what I may have gotten wrong, so don't hesitate to
comment!

Edit: If you'd rather just see code, it's [here](https://github.com/grisha/gowebapp).

### Introduction ###

In the past my basic knowledge of HTML, CSS and JavaScript has been
sufficient for my modest site building needs. Most of the apps I've
ever built were done using [mod_python](https://github.com/grisha/mod_python)
directly using the publisher handler. Ironically for an early Python adopter,
I've also done a fair bit of work with [Rails](http://rubyonrails.org/). For the past several years
I focused on (big) data infrastructure, which isn't web development at all,
though having to build web-based UI's is not uncommon. In fact the app I'm referring to
here is a data app, but it's not open source and what it does really
doesn't matter for this discussion. Anyway, this should provide some
perspective of where I come from when approaching this problem.

### Python and Ruby ###

As recently as a year ago, Python and Ruby would be what I would
recommend for a web app environment. There may be other similar
languages, but from where I stand, the world is dominated by Python and
Ruby.

For the longest time the main job of a web application was constructing
web pages by piecing HTML together server-side. Both Python and Ruby
are very well suited for the template-driven work of taking data from
a database and turning it into a bunch of HTML. There are lots of
frameworks/tools to choose from, e.g. Rails, Django, Sinatra, Flask,
etc, etc.

And even though these languages have certain significant limitations,
such as the [GIL](https://en.wikipedia.org/wiki/Global_interpreter_lock),
the ease with which they address the complexity of
generating HTML is far more valuable than any trade-offs that came
with them.

### The GIL ###

The Global Interpreter Lock is worthy of a separate mention. It is the
elephant in the room, by far the biggest limitation of any Python or
Ruby solution. It is so crippling, people can get emotional talking
about it, there are endless GIL discussions in both Ruby and Python
communities.

For those not familiar with the problem - the GIL only lets one thing
happen at a time. When you create threads and it "looks" like parallel
execution, the interpreter is still executing instructions
sequentially. This means that a single process can only take advantage
of a single CPU.

There do exist alternative implementations, for example JVM-based, but
they are not the norm. I'm not exactly clear why, they may not be
fully interchangeable, they probably do not support C extensions
correctly, and they might still have a GIL, not sure, but as far as I
can tell, the C implementation is what everyone uses out
there. Re-implementing the interpreter without the GIL would amount to
a complete rewrite, and more importantly it may affect the behavior of
the language (at least that's my naive understanding), and so for this
reason I think the GIL is here to stay.

Web apps of any significant scale absolutely require the ability to
serve requests in parallel, taking advantage of every CPU a machine
has. Thus far the only possible solution known is to run multiple
instances of the app as separate processes.

This is typically done with help of additional software such as
Unicorn/Gunicorn with every process listening on its own port and
running behind some kind of a connection balancer such as Nginx and/or
Haproxy. Alternatively it can be accomplished via Apache and its
modules (such as mod_python or mod_wsgi), either way it's
complicated. Such apps typically rely on the database server as the
arbiter for any concurrency-sensitive tasks. To implement caching
without keeping many copies of the same thing on the same server a
separate memory-based store is required, e.g. Memcached or Redis,
usually both. These apps also cannot do any background processing, for
that there is a set of tools such as Resque. And then all these
components need to be monitored to make sure it's working. Logs need
to be consolidated and there are additional tools for that. Given the
inevitable complexity of this set up there is also a requirement for a
configuration manager such as Chef or Puppet. And still, these set ups
are generally not capable of maintaining a large number of long term
connections, a problem known as C10K.

Bottom line is that a simple database-backed web app requires a whole
bunch of moving parts before it can serve a "Hello World!" page. And
nearly all of it because of the GIL.

### Emergence of Single Page Applications ###

More and more, server-side HTML generation is becoming a thing of the
past. The latest (and correct) trend is for UI construction and
rendering to happen completely client-side, driven by JavaScript. Apps
whose user interface is fully JS-driven are sometimes called
[Single Page Applications](https://en.wikipedia.org/wiki/Single-page_application),
and are in my opinion the future whether we like it or not. In an SPA
scenario the server only serves data, typically as JSON, and no HTML
is constructed there. In this set up, the tremendous complexity
introduced primarily so that a popular scripting language could be
used isn't worth the trouble. Especially considering that Python or
Ruby bring little to the table when all of the output is JSON.

### Enter Golang ###

Go is gradually disrupting the the world of web applications. Go
natively supports parallel execution which eliminates the requirement
for nearly all the components typically used to work around the GIL
limitation.

Go programs are binaries which run natively, so there is no need for
anything language-specific to be installed on the server. Gone is the
problem of ensuring the correct runtime version the app requires,
there is no separate runtime, it's part of the binary.  Go programs
can easily and elegantly run tasks in the background, thus no need for
tools like Resque. Go programs run as a single process which makes
caching trivial and means Memcached or Redis is not necessary either.
Go can handle an unlimited number of parallel connections, eliminating
the need for a front-end guard like Nginx.

With Go the tall stack of Python, Ruby, Bundler, Virtualenv, Unicorn,
WSGI, Resque, Memcached, Redis, etc, etc is reduced to just one
binary. The only other component generally still needed is a database
(I recommend PostgreSQL). It's important to note that all of these
tools are available as before for optional use, but with Go there is
the option of getting by entirely without them.

To boot this Go program will most likely outperform any Python/Ruby
app by an order of magnitude, require less memory, and with fewer
lines of code.

### So Is there a Popular Framework Yet? ###

The short answer is: a framework is entirely optional and not
recommended. There are many projects claiming to be great frameworks,
but I think it's best to try to get by without one.  This isn't just
my personal opinion, I find that it is generally shared in the Go
community.

It helps to think why frameworks existed in the first place. On the
Python/Ruby side this was because these languages were not initially
designed to serve web pages, and lots of external components were
necessary to bring them up to the task. Same can be said for Java,
which just like Python and Ruby, is about as old as the web as we know
it, or even pre-dates it slightly.

As I remember it, out of the box, early versions of Python did not
provide anything to communicate with a database, there was no
templating, HTTP support was confusing, networking was non-trivial,
bundling crypto would not even be legal then, and there was a whole
lot of other things missing. A framework provided all the necessary
pieces and set out rules for idiomatic development for all the common
web app use cases.

Go, on the other hand, was built by people who already experienced and
understood web development. It includes just about everything
necessary. An external package or two can be needed to deal with certain
specific aspects, e.g. OAuth, but by no means does a couple of
packages constitute a "framework".

If the above take on frameworks not convincing enough, it's helpful to
consider the framework learning curve and the risks. It took me about
two years to get comfortable with Rails. Frameworks can become
abandoned and obsolete, porting apps to a new framework is hard if
not impossible. Given how quickly the information technology sands
shift, frameworks are not to be chosen lightly.

I'd like to specifically single out tools and frameworks that attempt
to mimic idioms common to the Python, Ruby or the JavaScript
environments. Anything that looks or feels or claims to be "Rails for
Go", features techniques like injection, dynamic method publishing
and the like which require relying heavily on reflection are not the
Go way of doing things, it's best to stay away from those.

Frameworks definitely do make some things easier, especially in the
typical business CRUD world, where apps have many screens with lots of
fields, manipulating data in complex and ever-changing database
schemas. In such an environment, I'm not sure Go is a good choice in
the first place, especially if performance and scaling are not a
priority.

Another issue common to frameworks is that they abstract lower level
mechanisms from the developer often in way that over time grows to be
so arcane that it is literally impossible to figure out what is
actually happening. What begins with an idiomatic alias for a single
line of JavaScript becomes layers upon layers of transpilers,
minimizers on top of helpers hidden somewhere in a sub-dependency. One
day something breaks and it's impossible to know where to even look
for the problem. It's nice to know exactly what is going on sometimes,
Go is generally very good about that.

### What about the database and ORM? ###

Similarly to frameworks, Go culture is not big on ORM's. For starters,
Go specifically does not support objects, which is what the O in ORM
stands for.

I know that writing SQL by hand instead of relying on
`User.find(:all).filter...` convenience provided to by the likes of
ActiveRecord is unheard of in some communities, but I think this
attitude needs to change. SQL is an amazing language. Dealing with SQL
directly is not that hard, and quite liberating, as well as incredibly
powerful. Possibly the most tedious part of it all is copying the data
from a database cursor into structures, but here I found the sqlx
project very useful.

### In Conclusion ###

I think this sufficiently describes the present situation of the
server side. The client side I think could be separate post, so I'll
pause here for now. To sum up, thus far it looks like we're building
an app with roughly the following requirements:

* Minimal reliance on third party packages.
* No web framework.
* PostgreSQL backend.
* Single Page Application.

[part 2](/blog/2017/04/27/simplistic-go-web-app-part-2/)
