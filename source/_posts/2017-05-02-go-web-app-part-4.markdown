---
layout: post
title: "Building a Go Web App - Part 4"
date: 2017-04-27 09:13
comments: true
categories:
---

This is part 4. See [part 1](/blog/2017/04/27/simplistic-go-web-app/),
[part 2](/blog/2017/04/27/simplistic-go-web-app-part-2/) and
[part 3](/blog/2017/04/27/go-web-app-part-3/).

In this part I will try to briefly go over the missing pieces in our
very simplistic Go Web App.

### HTTP Handler Wrappers ###

I tiny rant: I do not like the word "middleware". The concept of a
wrapper has been around since the dawn of computing, there is no need
to invent new words for it.

Having that out of the way, let's say we need to require
authentication for a certain URL. This is what our index handler
presently looks like:

{% codeblock lang:go %}
func indexHandler(m *model.Model) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(w, indexHTML)
	})
}
{% endcodeblock %}

We could write a function which takes an `http.Handler` as an argument
and returns a (different) `http.Handler`. The returned handler checks
whether the user is authenticated with `m.IsAuthenticated()` (whatever
it does is not important here) and redirects the user to a login page,
or executes the original handler by calling its `ServeHTTP()` method.

{% codeblock lang:go %}
func requireLogin(h http.Handler, m *model.Model) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !m.IsAuthenticated(r) {
			http.Redirect(w, r, loginURL, http.StatusFound)
			return
		}
		h.ServeHTTP(w, r)
	})
}
{% endcodeblock %}

Given the above, the function registration now would look like this:
{% codeblock lang:go %}
   http.Handle("/", requireLogin(indexHandler(m)), m)
{% endcodeblock %}

Handlers can be wrapped this way in as many layers as needed and this
approach is very flexible. Anything from setting headers to
compressing output can be accomplished via a wrapper. Note also that
we can pass in whatever arguments we need, for example our
`*model.Model`.

### URL Parameters ###

Sooner or later we might want to rely on URL parameters,
e.g. `/person/3` where `3` is a person id. Go standard library doesn't
provide any support for this leaving it as an exercise for the
developer. The software component responsible for this sort of thing
is known as a [Mux](https://golang.org/pkg/net/http/#ServeMux) or
"router" and it can be replaced by a custom implementation. A Mux also
provides a `ServeHTTP()` method which means it satisfies the
`http.Handler` interface, i.e. it is a handler.

A very popular implementation is the [Gorilla Mux](https://github.com/gorilla/mux).
It is easy to delegate entire
sub-urls to the Gorilla Mux wherever more flexibility is needed. For
example we can decide that everything from `/person` and below is
handled by an instance of a Gorilla router _and_ we want that to be
all authenticated, which might look like this:

{% codeblock lang:go %}
	// import "github.com/gorilla/mux"
	pr := mux.NewRouter().PathPrefix("/person").Subrouter()
	pr.Handle("/{id}", personGetHandler(m)).Methods("GET")
	pr.Handle("/", personPostHandler(m)).Methods("POST")
	pr.Handle("/{id}", personPutHandler(m)).Methods("PUT")
	http.Handle("/person/", requireLogin(pr))
{% endcodeblock %}

NB: I found that trailing slashes are important and the rules on when
they are required are a bit confusing.

There are many other router/mux implementations out there, the beauty
of not buying into any kind of a framework is that we can choose the
one that works best for us or write our own (they are not difficult
to implement).

### Asset Handling ###

One of the neatest things about Go is that a compiled program is a
single binary not a big pile of files like it is with most scripting
languages and even compiled ones. But if our program relies on assets
(JS, CSS, image and other files), we would need to copy those over to
the server at deployment time.

There is a way we can preserve the "one binary" characteristic of
our program by including assets as part of the binary itself. For
that there is the [go-bindata](https://github.com/jteeuwen/go-bindata/) project and its
nephew [go-bindata-assetfs](github.com/elazarl/go-bindata-assetfs).

Since packing assets into the binary is slightly beyond what
`go build` can accomplish, we will need some kind of a script to take care of it.
My personal preference is to use the tried and true `make`, and it
is not uncommon to see Go projects come with a `Makefile`.

Here is a relevant example Makefile rule

{% codeblock lang:sh %}
ASSETS_DIR = "assets"
build:
	@export GOPATH=$${GOPATH-~/go} && \
	go get github.com/jteeuwen/go-bindata/... github.com/elazarl/go-bindata-assetfs/... && \
	$$GOPATH/bin/go-bindata -o bindata.go -tags builtinassets ${ASSETS_DIR}/... && \
	go build -tags builtinassets -ldflags "-X main.builtinAssets=${ASSETS_DIR}"
{% endcodeblock %}

The above rule creates a `bindata.go` file which will be placed in the
same directory where `main.go` is and becomes part of package
`main`. `main.go` will somehow know that assets are built-in and this
is accomplished via an `-ldflags "-X main.builtinAssets=${ASSETS_DIR}"` trick,
which is a way to assign values to variables at compile time. This means
that our code can now check for the value of `builtinAssets` to decide
what to do, e.g.:

{% codeblock lang:go %}
	if builtinAssets != "" {
		log.Printf("Running with builtin assets.")
		cfg.UI.Assets = &assetfs.AssetFS{Asset: Asset, AssetDir: AssetDir, AssetInfo: AssetInfo, Prefix: builtinAssets}
	} else {
		log.Printf("Assets served from %q.", assetsPath)
		cfg.UI.Assets = http.Dir(assetsPath)
	}
{% endcodeblock %}

The second important thing is that we are defining a
[build tag](https://dave.cheney.net/2013/10/12/how-to-use-conditional-compilation-with-the-go-build-tool)
called `builtinassets`. We are also telling `go-bindata` about it, what this
means is "only compile me when builtinassets is set", and this controls
under which circumstances `bindata.go` (which contains our assets as
Go code) is to actually be compiled.

### Pre-transpilation of JavaScript ###

Last, but not the least, I want to briefly mention packing of web
assets. To describe it properly is enough material for a whole new
series of posts, and this would really have nothing to do with Go. But
I can at least list the following points.

* You might as well give in and install [npm](https://www.npmjs.com/),
  and make a `package.json` file.

* Once npm is installed, it is trivial to install the Babel command-line
  compiler, `babel-cli`, which is one way to transpile JavaScript.

* A more complicated, frustrating, but ultimately more flexible method
  is to use [webpack](https://webpack.github.io/). Webpack will
  pre-transpile and do things like combine all JS into a single
  file as well as minimize it.

* I was surprised by how difficult it was to provide module import
  functionality in JavaScript. The problem is that there is an ES6
  standard for `import` and `export` keywords, but there is no
  implementation, and even Babel assumes that something else
  implements it for you. In the end I settled on
  [SystemJS](https://github.com/systemjs/systemjs).  The complication
  with SystemJS is that now in-browser Babel transpilation needs to be
  something that SystemJS is aware of, so I had to use its Babel
  plugin for that. Webpack in turn (I think?) provides its own module
  support implementation, so SystemJS is not needed when assets are
  packed. Anyhow, it was all rather frustrating.

## Conclusion ##

I would say that in the set up I describe in this four part series Go
absolutely shines, while JavaScript not so much. But once I got over
the initial hurdle of getting it all to work, React/JSX was easy and
perhaps even pleasant to work with.

That's it for now, hope you find this useful.
