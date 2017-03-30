---
layout: post
title: "mod_python: the long story"
date: 2013-10-25 20:05
comments: true
categories:
---

This story started back in 1996. I was in my early twenties, working
as a programmer at a small company specializing in on-line reporting of
certain pharmaceutical data.

There was a web-based application (which was extremely cool
considering how long ago this was), but unfortunately it was written
in Visual Basic by a contractor and I was determined to do something
about it. As was very fashionable at the time, I was very pro Open
Source, had Linux running on my home 386 and had recently heard
[Guido’s talk](http://boston-linux-unix-general-discussion-list.996279.n3.nabble.com/fwd-LOCAL-Washington-DC-Linux-User-Group-meeting-and-Python-talk-td3733.html)
at the DC Linux user group presenting his new language he called
Python. Python seemed like a perfect alternative to the VB
monstrosity.

I spent a few weeks quietly in my cubicle learning Python and
rewriting the whole app in it. (Back in those days this is how
programmers worked, there was no “agile” and “daily stand ups”,
everyone understood that things take time. I miss those days very
much). Python was fantastic, and soon the app was completely
re-written.

Then I realized that explaining what I’ve been working on to my bosses
might be a bit of a challenge. You see, for a while there nobody knew
that the web app they’ve been using had been re-written in Python, but
sooner or later I would have to reveal the truth and, more
importantly, justify my decision. I needed a good reason, and stuff
about object-oriented programming, clean code, open source, etc would
have fallen on deaf ears.

Just around that time the Internet Programming with Python book came
out, and in it there was a chapter on how to embed the Python
interpreter in the Netscape Enterprise web server. The idea seemed
very intriguing to me and it might have contained exactly the
justification I was looking for - it would make the app
faster. ("Faster" is nearly as good as "cheaper" when it comes to
selling to the management). I can’t say that I knew much C back then,
but with enough tinkering around I was able to make something work,
and lo and behold it was quite noticeably faster.

And so a few days later I held a presentation in the big conference
room regarding this new tool we’ve started using something called Python which
can crunch yall’s numbers an order of magnitude faster than the
Microsoft product we’ve been using. And oh, by the way, I quickly
hacked something together last night - let’s do a live demo, look how
fast this is!  They were delighted.

Little did they know, the app had been running in Python for months,
and the reason for the speed up had little to do with the language
itself. It was all because I was able to embed the interpreter within
the web server. Then I thought that to make it all complete I would
make my little tool open source and put it on my website free for
everyone to use. I called it
[NSAPy](http://www.ispol.com/home/grisha/nsapy/) as a combination of
the Netscape Server API and Python.

But I didn’t stop there, and soon I was able to replicate this on an
Apache web server, which was taking the Internet by storm back
then. The name mod_python came naturally since there already was a
mod_perl.

Things were going very well back then. These were the late nineties,
the dawn of e-commerce on the World Wide Web. I started working for a
tiny ISP which soon transformed into a humongous Web Hosting company,
we ran millions of sites, built new data centers with thousands of
servers pushing gigabits of traffic and (in short) were taking over
the world (or so it seemed). With the rise of our company’s stock
price, me and my colleagues were on our way to becoming
millionaires. Mod_python was doing very well too. It had a busy
website, a large and very active mailing list and an ever growing
number of devoted users. I went to various Open Source conferences to
present about it (and couldn’t really believe that without exception
everyone knew what mod_python was).

Then came 2001. We just bought a house and our second son was not even
a year old when one beautiful sunny summer day I was summoned to a
mandatory meeting. In that meeting about two thirds of our office was
let go. Even though we all felt it was coming, it was still a shock. I
remember coming home that morning and having to explain my wife that
I’d just been fired. This after constant all-nighters, neglect for
family life under the excuse of having the most important job doing
the most important thing and changing the world and rants about how
we’d be all set financially in just a year or two. In my personally
opinion the 2007 financial crash was nothing compared to the dot-com
bust. Everyone was getting laid off everywhere, the Internet became a
dirty word, software development was being outsourced to India.

For the next couple of years I made a living doing contracting work
here and there. Needless to say, mod_python wasn’t exactly at the top
of my priority list. But it was getting ever more popular, the mailing
list busier, though it didn’t make any money (for me at least). I
tried my best to keep everything running in whatever spare time I had,
answering emails and releasing new versions periodically. Finding time
for it was increasingly difficult, especially given that most of the
work I was doing had nothing to do with mod_python or Python.

One day I had this thought that donating mod_python to the Apache
Software Foundation would ensure its survival, even if I can no longer
contribute. And so it was done. Initially things went very well - the
donation did affiliate mod_python with the solid reputation of Apache
and that was great. Mod_python gained a multitude more users and most
importantly contributors.

At the same time my life was becoming ever more stressful. Free time
for mod_python hacking was getting more and more scarce until there
was none. I also think I was experiencing burnout. Answering questions
on the mailing list became an annoyance. I had to read through
enormous threads with proposals for various features or how things
ought to work and respond to them, and it was just never ending. It
wasn’t fun anymore.

I also felt that people didn’t understand what mod_python was and that
I’m not able to explain it very well. (For what it’s worth, I still
feel this way). In my mind it was primarily an interface to the Apache
internals, but since making every structure and API accessible from
within Python was impractical, only selected pieces were
exposed. Secondly, mod_python provided means to perform certain things
that were best done in Apache, e.g. global locking, caching. Lastly,
it provided certain common tasks but implemented in Apache-specific
ways (using Apache pools, APR, etc.) for maximal performance; things
like cookies and sessions fell into that category. Publisher and PSP
didn’t strictly belong in mod_python, but were there for the sake of
battery-includedness - you could build a rudimentary app without any
additional tool.

The rest of the world saw it as a web-development framework. It wasn’t
a particularly good one, especially when it came to development,
because it required root privileges to run. It also didn’t do a very
good job at reloading changed modules very well which complicated
development. A very considerable effort was put in by one of the
contributors to address the particular issue of module loading and
caching, and I never thought it to be important because to me
restarting Apache seemed like the answer, I didn’t think that people
without root access would ever use mod_python.

As I was growing more disinterested in mod_python it got to a point
where I just let it be. I would skim through emails from people I
trusted and responded affirmatively to whatever they proposed without
giving it much thought. I didn’t see any point in keeping and
defending my vision for mod_python. I think that by about 2006 or so I
was so disconnected I no longer had a good grasp of what the latest
features of mod_python were being worked on. Not sure if it was my
lack of interest or that other contributors felt burned out as well,
but new commits slowed down to a trickle and stopped eventually, and
my quarterly reports to the ASF Board became a cut-and-paste email of
“no new activity”.

This is where the negative aspect of the ASF patronage begun to
surface. Sadly, the ASF rules are that projects and their community
must be active, and soon the project got moved to the attic. And even
though I kept telling myself that I couldn’t care less, I must admit
it hurt. The attic is a like a one-way trash can - once there, a
project cannot go back, other than through the incubation process.

Fast forward to 2013. Why get back to hacking on it? First of all I
got tired of “mod_python is dead” plastered all over the web.  Every
time I see some kid who wasn’t old enough to speak back when I first
released it tweet that it is this or that, I can’t help but take it a
little personally. It’s an open source project people, it’s only dead
if you do not contribute to it.

For the skeptics in the crowd I most certainly disagree that
mod_python as a concept is dead, I’d even argue that its time hasn’t
come yet. The vision has not changed. Mod_python is still an interface
to Apache which lets you take advantage of its versatile architecture
to do some very powerful things. It’s not quite a web development
framework, and it’s not even a tool for running your favorite web
development framework in production (though it can certainly do that
quite nicely).

These days there is more demand than ever for high volume servers that
do not have a user interface and thus do not need a WSGI framework to
power them - I think this is one of the areas where mod_python could
be most useful. There are also all kinds of possibilities for using
Apache and mod_python for distributed computing and big data stuff
taking advantage of the fact that Apache is an excellent job
supervisor - anyone up for writing a map/reduce framework in
mod_python?

I must also note that hacking on it in the past weeks has been fun
once again. I wanted to get up to speed with the latest on Python 3
and Apache internals, especially the event/epoll stuff and this has
been a great way to do just that. I also very much enjoy that I can
once again do whatever I want without any scrutiny.

If there is one thing I’ve learned it’s that few open source projects
can exist without their founders’ continuous involvement. The Little
Prince once said - “You become responsible forever for what you have
tamed”. It seems like mod_python is my rose and if I don’t water it,
no one will.

P.S. Did I mention mod_python now supports Python 3? Please help
me [test it](https://github.com/grisha/mod_python/issues/9)!

<p>
<iframe src="http://ghbtns.com/github-btn.html?user=grisha&repo=mod_python&type=watch&count=true&size=large"
  allowtransparency="true" frameborder="0" scrolling="0" width="170" height="30"></iframe>

<iframe src="http://ghbtns.com/github-btn.html?user=grisha&repo=mod_python&type=fork&count=true&size=large"
  allowtransparency="true" frameborder="0" scrolling="0" width="170" height="30"></iframe>

<a href="https://twitter.com/mod_python" class="twitter-follow-button" data-show-count="false" data-size="large">Follow @mod_python</a>
<script>!function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0],p=/^http:/.test(d.location)?'http':'https';if(!d.getElementById(id)){js=d.createElement(s);js.id=id;js.src=p+'://platform.twitter.com/widgets.js';fjs.parentNode.insertBefore(js,fjs);}}(document, 'script', 'twitter-wjs');</script>
</p>
