---
layout: post
title: "mod_python performance and why it matters not."
date: 2013-10-10 13:04
comments: true
categories:
---

*TL;DR: It's faster than you think.*

Tonight I thought I'd spend some time looking into how the new
[mod_python](http://www.modpython.org/)
fares against other frameworks of similar purpose. In this article I
am going to show the results of my findings, and then I will explain
*why it really does not matter*.

I am particularly interested in the following:

- a pure mod_python handler, because this is as fast as mod_python gets.
- a mod_python wsgi app, because WSGI is so popular these days.
- mod_wsgi, because it too runs under Apache and is written entirely in C.
- uWSGI, because it claims to be super fast.
- Apache serving a static file (as a point of reference).

# The Test

I am testing this on a CentOS instance running inside VirtualBox on an
early 2011 MacBook Pro. The VirtualBox has 2 CPU's and 6GB of RAM
allocated to it. Granted this configuration can't possibly be very
performant [if there is such a word], but it should be enough to
compare.

Real-life performance is very much affected by issues related to
concurrency and load. I don't have the resources or tools to
comprehensively test such scenarios, and so I'm just using concurrency
of 1 and seeing how fast each of the afore-listed set ups can process
small requests.

I'm using mod_python 3.4.1 (pre-release), revision
[35f35dc](https://github.com/grisha/mod_python/tree/35f35dc2a8d23e92e5c8dc7dccea2a1b6bcc353e),
compiled against Apache 2.4.4 and Python 2.7.5. Version of mod_wsgi is
3.4, for uWSGI I use 1.9.17.1.

The Apache configuration is pretty minimal (It could probably trimmed
even more, but this is good enough):

```
LoadModule unixd_module /home/grisha/mp_test/modules/mod_unixd.so
LoadModule authn_core_module /home/grisha/mp_test/modules/mod_authn_core.so
LoadModule authz_core_module /home/grisha/mp_test/modules/mod_authz_core.so
LoadModule authn_file_module /home/grisha/mp_test/modules/mod_authn_file.so
LoadModule authz_user_module /home/grisha/mp_test/modules/mod_authz_user.so
LoadModule auth_basic_module /home/grisha/mp_test/modules/mod_auth_basic.so
LoadModule python_module /home/grisha/src/mod_python/src/mod_python/src/mod_python.so

ServerRoot /home/grisha/mp_test
PidFile logs/httpd.pid
ServerName 127.0.0.1
Listen 8888
MaxRequestsPerChild 1000000

<Location />
      SetHandler mod_python
      PythonHandler mp
      PythonPath "sys.path+['/home/grisha/mp_test/htdocs']"
</Location>
```

I should note that `<Location />` is there for a purpose - the latest
mod_python forgoes the map_to_storage phase when inside a `<Location>`
section, so this makes it a little bit faster.

And the `mp.py` file referred to by the `PythonHandler` in the config
above looks like this:

```python
from mod_python import apache

def handler(req):

    req.content_type = 'text/plain'
    req.write('Hello World!')

    return apache.OK
```

As the benchmark tool, I'm using the good old
[ab](http://httpd.apache.org/docs/2.4/programs/ab.html), as follows:

```sh
$ ab -n 10  http://localhost:8888/
```

For each test in this article I run 500 requests first as a "warm up",
then another 500K for the actual measurement.

For the mod_python WSGI handler test I use the following config (relevant section):

```
<Location />
    PythonHandler mod_python.wsgi
    PythonPath "sys.path+['/home/grisha/mp_test/htdocs']"
    PythonOption mod_python.wsgi.application mp_wsgi
</Location>
```

And the `mp_wsgi.py` file looks like this:

```python
def application(environ, start_response):
    status = '200 OK'
    output = 'Hello World!'

    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]
```

For mod_wsgi test I use the exact same file, and the config as follows:

```
LoadModule wsgi_module /home/grisha/mp_test/modules/mod_wsgi.so
WSGIScriptAlias / /home/grisha/mp_test/htdocs/mp_wsgi.py
```

For uWSGI (I am not an expert), I first used the following command:
```
/home/grisha/src/mp_test/bin/uwsgi \
   --http 0.0.0.0:8888 \
   -M -p 1 -w mysite.wsgi -z 30 -l 120 -L
```

Which yielded a pretty dismal result, so I tried using a unix socket
`-s /home/grisha/mp_test/uwsgi.sock` and ngnix as
the front end as described
[here](http://nichol.as/benchmark-of-python-web-servers), which did
make uWSGI come out on top (even if proxied uWSGI is an orange among
the apples).


###The results, requests per second, fastest at the top:

```
| uWSGI/nginx         | 2391 |
| mod_python handler  | 2332 |
| static file         | 2312 |
| mod_wsgi            | 2143 |
| mod_python wsgi     | 1937 |
| uWSGI --http        | 1779 |
```

What's interesting and unexpected at first is that uWSGI and the
mod_python handler perform better than sending a static file, which I
expected to be the fastest. On a second thought though it does make
sense, once you consider that no (on average pretty expensive)
filesystem operations are performed to serve the request.

Mod_wsgi performs better than the mod_python WSGI handler, and that is
expected, because the mod_python version is mostly Python, vs
mod_wsgi's C version.

I think that with a little work mod_python wsgi handler could perform
on par with uWSGI, though I'm not sure the effort would be worth
it. Because as we all know,
[premature optimization is the root of all evil](http://en.wikiquote.org/wiki/Donald_Knuth#Computer_Programming_as_an_Art_.281974.29).

# Why It Doesn't Really Matter

Having seen the above you may be tempted to jump on the uWSGI wagon,
because after all, what matters more than speed?

But let's imagine a more real world scenario, because it's not likely
that all your application does is send `"Hello World!".`

To illustrate the point a little better I created a very simple Django
app, which too sends `"Hello World!"`, only it does it using a template:

```python
def hello(request):
    t = get_template("hello.txt")
    c = Context({'name':'World'})
    return HttpResponse(t.render(c))
```

Using the mod_python wsgi handler (the slowest), we can process 455
req/s, using uWSGI (the fastest) 474. This means that by moving this
"application" from mod_pyhton to uWSGI we would improve performance by
a measley 5%.

Now let's add some database action to our so-called "application". For
every request I'm going to pull my user record from the Django
auth_users table:

```python
from django.contrib.auth.models import User

def hello(request):
    grisha = User.objects.get(username='grisha')
    t = get_template("hello.txt")
    c = Context({'name':str(grisha)[0:5]}) # world was 5 characters
    return HttpResponse(t.render(c))
```

Now we are down to 237 req/s for the mod_python WSGI handler and 245
req/s in uWSGI, and the difference between the two has shrunk to just
over 3%.

Mind you, our "application" still has less than 10 lines of code. In a
real-world situation the difference in performance is more likely to
amount to less than a tenth of a percent.

Bottom line: it's foolish to pick your web server based on speed
alone. Factors such as your comfort level with using it, features,
documentation, security, etc., are far more important than how fast it
can crank out "Hello world!".

Last, but not least, mod_python 3.4.1 (used in this article) is
ready for pre-release testing, please help me [test it](https://github.com/grisha/mod_python/issues/8)!

