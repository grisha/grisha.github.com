---
layout: post
title: "Golang receiver vs function argument"
date: 2016-09-22 08:15
comments: true
categories:
---

What is the difference between a Go _receiver_ (as in "method receiver")
and a function _argument_? Consider these two bits of code:

{% codeblock lang:go %}
func (d *duck) quack() { // receiver
   // do something
}
{% endcodeblock %}

versus

{% codeblock lang:go %}
func quack(d *duck) { // funciton argument
  // do something
}
{% endcodeblock %}

The "do something" part above would work exactly the same regardless of
how you declare the function. Which begs the question, which should
you use?

In the object-oriented world we were used to objects doing things, and
in that context `d.quack()` may seem more intuitive or familiar than
`quack(d)`, because it reads better. After all, one could argue that
the former is a duck quacking, but the latter reads like you're
quacking a duck, and what does that even mean? I have learned that you
should not think this way in the Go universe, and here is why.

First, what is the essential difference? It is that at the time of the
call, the receiver is an _interface_ and the function to be called is
determined _dynamically_. If you are not using interfaces, then this
doesn't matter whatsoever and the only benefit you are getting from
using a method is syntactic sweetness.

But what if you need to write a test where you want to stub out
`quack()`. If your code looks like this, then it is not possible,
because methods are attached to their types inflexibly, you cannot
change them, and there is no such thing as a "method variable":

{% codeblock lang:go %}
type duck struct {}

func (d *duck) quack() {
   // do something
}

// the function we are testing:
func testme(d *duck) {
  d.quack() // cannot be stubbed
}
{% endcodeblock %}

However, if you used a function argument, it would be easy:

{% codeblock lang:go %}
type duck struct {}

var quack = func(d *duck) {
   // do something
}

// the function we are testing:
func foo(d *duck) {
  quack(d)
}
{% endcodeblock %}

Now you can assign another function to quack at test time, e.g. `quack = func(d *duck) { // do something else }`  and all is
well.

Alternatively, you can use an interface:

{% codeblock lang:go %}
type quacker interface {
  quack()
}

type duck struct {}

var func (d *duck) quack() { // satisfies quacker
   // do something
}

// the function we are testing:
func foo(d quacker) {
  d.quack()
}
{% endcodeblock %}

Here, if we need to test `foo()` we can provide a different
`quacker`.

Bottom line is that it only makes sense to use a receiver if this
function is part of an interface implementation, OR if you never ever
need to augment (stub) that function for testing or some other
reason. As a practical matter, it seems like (contrary to how it's
done in the OO world) it is better to always start out with `quack(d)`
rather than `d.quack()`.
