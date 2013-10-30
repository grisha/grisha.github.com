---
layout: post
title: "Separate Request and Response or a single Request object?"
date: 2013-10-30 13:18
comments: true
categories:
---

Are you in favor of a single request object, or two separate objects:
request and response?  Hold on to your strong opinion here - you and
your opponents are likely talking apples and oranges without realizing
it.

I thouhgt I always was in favor of a single request object which I
[expressed on the Web-SIG mailing list thread](https://mail.python.org/pipermail/web-sig/2003-October/000162.html)
dating back to October 2003 (ten years ago!). But it is only now that
I’ve come to realize that both proponents of a single object and two
separate objects were correct, they were just talking about different
things.

The confusion lies in the distinction between what I am going to term
a web application and a request handler.

A *request handler* exists in the realm of an HTTP server, which
(naturally) serves HTTP requests. An HTTP request consists of a
request (a method, such as “GET”, along with some HTTP headers and
possibly a body) and a response (a status line, some HTTP headers and
possibly a body) sent over the TCP connection. There is a one-to-one
correspondence between a request and a response established by the
commonality of the connection. An HTTP request is incomplete if the
response is missing, and a response cannot exist without a
request. (Yes, the term "request" is used to denote both the request
and response, as well as just the request part of the request, and
that's confusing).

A *web application* is a layer on top of the HTTP request handler. A web
application operates in requests and responses as well, but those
should not be confused with the HTTP request/response pairs.

Making the conceptual distinction between a web application request
and an HTTP request is difficult because both web applications and
request handlers use HTTP headers and status to accomplish their
objectives. The difference is that strictly speaking a web application
does not have to use HTTP and ideally should be protocol-agnostic,
though it is very common for a web application to rely on
HTTP-specific features these days. Not every HTTP request exists as
part of a web application. But because it is difficult to imagine a
web application without HTTP, we tend to lump the two concepts
together. It is also exacerbated by the fact that HTTP headers carry
both application-specific and HTTP-specific information.

A good example of the delineation between a web application response
and an HTTP response is handling of an error condition. A web
application error is typically not an HTTP error.  Imagine an “invalid
login” page. It is a web application error, but not an HTTP error. An
“invalid login” page should send a “200 OK” status line and a body
explaining that the credentials supplied were not valid. But then HTTP
provides its own authentication mechanism, and an HTTP “401
Unauthorized” (which ought not be used by web applications) is often
misunderstood as something that web applications should incorporate
into how they do things.

Another example of a place where the line gets blurry is a redirect. A
redirect is quite common in a web application, and it is typically
accomplished by way of an HTTP redirect (3XX status code), yet the two
are not the same. An HTTP redirect, for example, may happen
unbeknownst to the web application for purely infrastructural reasons,
and a web application redirect does not always cause an HTTP redirect.

Yet another example: consider a website serving static content where
same URI responds with different content according to the
Accept-Language header in the request. Is this a “web application”?
Hardly. Could you have some Python (or whatever you favorite language
is) help along with this process? Certainly. Wouldn’t this code be
part of a “web application”?  Good question. It is not uncommon for a
web application to consider the Accept-Language header in its
response. You could also accomplish this entirely in an http server by
configuring it correctly. Sometimes it just depends on how you're
looking at it, but you do have to decide for yourself which it is.

Getting to the original problem, the answer to the question of whether
to use separate response/request objects or not depends very much on
which realm you’re operating in. A request handler only needs one
request object representing the HTTP request because it is
conceptually similar to a file - you don’t typically open a file twice
once for reading and once for writing. Whereas a web application,
which may chose between different responses depending on what’s in the
request is possibly best served with two separate objects.

I think that misunderstanding of what a “web application” is happens
to be the cause of a lot of bad decisions plaguing the world of web
development these days. It is not uncommon to see people get stuck on
low-level HTTP subtleties while referring to web application issues and
vise-versa. We’d all get along better if we took some time to think
about the distinction between web applications and HTTP request
handlers.

P.S. This will get even more complicated when HTTP 2.0 comes around
where responses may exist without a request. And I haven’t even
mentioned SSL/TLS.
