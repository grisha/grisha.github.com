---
layout: post
title: "Relative Imports Hack in Golang"
date: 2018-10-18 12:42
comments: true
categories:
---

If you have multiple packages in your program's Go source code, you
probably have come across a situation where if you create a fork on
Github or move/rename your top level directory, all your import
statements need to be adjusted.

There is a simple hack to accomplish relative imports by using the
`vendor` directory and symlinks. If you have a package called `mypkg`,
then the following should work:

{% codeblock lang:sh %}

$ mkdir -p vendor/relative
$ ln -s ../../mypackage vendor/relative/mypkg

{% endcodeblock %}

And now, your Go code could do this:

{% codeblock lang:go %}

package main

import (
    "fmt"

    "relative/mypkg"
)

{% endcodeblock %}

I cannot think of any downsides to doing this, if you know of any,
please do comment!
