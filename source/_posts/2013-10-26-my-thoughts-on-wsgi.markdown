---
layout: post
title: "My thoughts on WSGI"
date: 2013-10-26 11:24
comments: true
categories:
---

I'm not very fond of it. Here is why.

## CGI Origins

WSGI is based on CGI, as the "GI" (Gateway Interface) suggests right
there in the name.

CGI solved a very important problem using the very limited tools at
hand available at the time. Though CGI wasn't a standard, it was
ubiquitous in the early days of the WWW, despite its inherent slowness
and other limitations. It became popular because it worked with any
language, was easy to turn on and provided such a thick wall of
isolation that admins could turn it on for their users without too much concern
for problems caused by user-generated CGI scripts.

There is now an RFC ([RFC3875](http://www.ietf.org/rfc/rfc3875))
describing CGI, but I hazard that
[Ken Coar](http://ken.coar.org/) wrote the RFC not because he thought CGI was great, but rather
out of discontent with the present state of affairs - everyone was
using CGI, yet there never was a formal document describing it.

So if I were to attempt to unite all Python web applications under the
same standard, CGI wouldn't be the first thing I would consider. There are
other efforts at solving the same problem in more elegant ways which
could be used as a model, e.g. (dare I mention?) Java Servlets.

## Headers

CGI dictated that HTTP headers be passed to the CGI script by way of
[environment variables](http://en.wikipedia.org/wiki/Environment_variable). The
same environment that contain your `$PATH` and `$TERM`.  (Note this
also explains the origin of the term *environment* in WSGI - in HTTP
there is no *request environment*, there is simply a *request*). So as
to not clash with any other environment variables, CGI would prepend
`HTTP_` to every header name. It also swapped dashes with underscores
because dashes are not allowed in shell variable names. And because
environment variables in DOS and Unix are typically case-insensitive,
they were capitalized. Thus `"content-type"` would become `"HTTP_CONTENT_TYPE"`.

And how much sense applying the same transformation make in the realm
in which WSGI operates? The headers are typically read by the
webserver and stored in some kind of a structure, which ought to be
directly accessible so the application can get headers in the
original, unmodified format. For example in Apache this would be the
`req.headers_in` table.  What is the benefit of combing through that
structure converting every key to some capitalized HTTP_ string at
every request? Why are WSGI developers forced to use
`env['HTTP_CONTENT_LENGTH']` rather than `env['Content-length']`?

Another thing about the environment is that the WSGI standard states
that it must be a real Python dictionary, thereby dictating that a
memory allocation happen to satisfy this requirement, *at every
request*.

## start_response()

In order to be able to write anything to the client a WSGI application
must envoke the start_response() function passed to it which would
return a write() method.

Ten points for cuteness here, but the practicality of this solution
eludes me. This is certainly a clever way to make the fact that the start
of a response is an irreversible action in HTTP because the headers are
sent first, but seriosly - do programmers who code at this level not
know it? Why can't the header sending part happen implicitly at the
first write(), and why can't an application write without sending any
headers?

There is also another problem here - function calls are relatively
expensive in Python. The requirement that the app must beg for the
write object every time introduces a completely unnecessary function
call.

The request object with a write() method should simply be passed
in. This is how it has always worked in mod_python (cited in PEP3333 a
number of times!).

## Error handling

First, I must confess that after re-reading the section of the PEP3333
describing the `exc_info` argument several times I still can't say I
grok what it's saying. Looking at some implementations out there I am
releived to know I am not the only one.

But the gist of it that an exception can be supplied along with some
headers. It seems to me there is confusion between HTTP errors and
Python errors here, the two are not related. What is the expected
outcome of passing a Python exception to an HTTP server? The server
would probably convert it to a 500 Internal Server Error (well it only
has so many possibilities to chose from), and what's the point of that?

Wouldn't the outcome be same if the application simply raised an
exception?

If the spec wanted to provide means for the application Python errors
to somehow map to HTTP errors, why not define a special exception
class which could be used to send HTTP errors? What was wrong with
mod_python's:

```
raise apache.SERVER_RETURN, apache.HTTP_INTERNAL_SERVER_ERROR
```

I think it's simple and self-explanatory.

## Other things

What is `wsgi.run_once`, why does it matter and why should the web
server provide it? What would be a good use case for such a thing?

There is a long section describing "middleware". Middleware is a
wrapper, an example of the [pipeline design pattern](http://www.cise.ufl.edu/research/ParallelPatterns/PatternLanguage/AlgorithmStructure/Pipeline.htm)
and there doesn't seem to be anything special with this concept that
the WSGI spec should even mention it. (I also object to the term
"middleware" - my intuition suggests it's a layer between "hardware"
and "software", not a wrapper.)

## SCRIPT_NAME and PATH_INFO

Perhaps the most annoying part of CGI were these two mis-understood
variables, and sadly WSGI uses them too.

Remember that in CGI we always had a script. A typical CGI script
resided somewhere on the filesystem to which the request URI maps. As
part of serving the request the server traversed the URI mapping each
element to an element of the filesystem path to locate the
script. Once the script was found, the portion of the URI used thus far
was assigned to the SCRIPT_NAME variable, while the remainder of the
URI got assigned to PATH_INFO.

But where is *the script* in WSGI? Is my Python module the script?
What relatioship does there exist between the request URI and the
(non-existent) script?

## Bottom line

I am not convinced that there should be a universal standard for
Python web applications to begin with. I think that what we refer to
as "web applications" is still not very well understood by us
programmers.

But if we are to have one, I think that WSGI approach is not the right
one. It brings the world of Python web development to the lowest
common denominator - CGI and introduces some problems of its own on
top of it.

## Other notes

### What is the Gateway in CGI

I did some digging into the etymology of “Common Gateway Interface”,
because I wanted to know what the original author (Rob McCool) meant
by it when he came up with it. From reading [this](http://web.archive.org/web/20100127191128/http://hoohoo.ncsa.illinois.edu/cgi/intro.html)
it’s apparent that he saw it as the Web daemon’s gateway to an outside
program:

“For example, let's say that you wanted to "hook up" your Unix
database to the World Wide Web, to allow people from all over the
world to query it. Basically, you need to create a CGI program that
the Web daemon will execute to transmit information to the database
engine, and receive the results back again and display them to the
client. This is an example of a gateway, and this is where CGI,
currently version 1.1, got its origins.”

I always perceived it the other way around, I thought the “gateway”
was a gateway to the web server. I think that when Phillip J. Eby
first proposed the name WSGI he was under the same misperception as I.
