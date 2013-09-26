---
layout: post
title: "Running a WSGI app on Apache should not be this hard"
date: 2013-09-25 20:08
comments: true
categories: 
---

If I have a Django app in `/home/grisha/mysite`, then all I should
need to do to run it under Apache is:

```sh
$ mod_python create /home/grisha/mysite_httpd \
    --listen=8888 \
    --pythonpath=/home/grisha/mysite \
    --pythonhandler=mod_python.wsgi \
    --pythonoption="wsgi.application mysite.wsgi::application"

$ mod_python start /home/grisha/mysite_httpd/conf/httpd.conf
```

That's all. There should be no need to become root, tweak various
configurations, place files in the right place, check permissions,
none of that.

Well... With [mod_python](http://www.modpython.org/) 3.4.0 (alpha)
that's exactly how it is...

Please help me [test it](https://github.com/grisha/mod_python/issues/4).
