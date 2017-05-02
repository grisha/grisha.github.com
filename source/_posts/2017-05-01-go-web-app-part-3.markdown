---
layout: post
title: "Building a Go Web App - Part 3"
date: 2017-05-01 12:22
comments: true
categories:
---

This is part 3. See [part 1](/blog/2017/04/27/simplistic-go-web-app/)
and [part 2](/blog/2017/04/28/simplistic-go-web-app-part-2/).

The previous two posts got us to a point where we had a Go app which
was able to serve a tiny bit of HTML. This post will talk about the
client side, which, alas, is mostly JavaScript, not Go.

### JavaScript in 2017 ###

This is what gave me the most grief. I don't really know how to
categorize the mess that present day JavaScript is, nor do I really
know what to attribute it to, and trying to rationalize it would make
for a great, but entirely different blog post. So I'm just going to
accept this as the reality we cannot change and move on to how to best
work with it.

### Variants of JS ###

The most common variant of JS these days is known as ES2015 (aka ES6 or
ECMAScript 6th Edition), and it is *mostly* supported by the more or
less latest browsers. The latest released spec of JavaScript is ES7
(aka ES2016), but since the browsers are sill catching up with ES6, it
looks like ES7 is never really going to be adopted as such, because
most likely the next coming ES8 which might be released in 2017 will
supersede it before the browsers are ready.

Curiously, there appears to be no simple way to construct an
environment fully specific to a particular ECMAScript version. There
is not even a way to revert to an older fully supported version ES5 or
ES4, and thus it is not really possible to test your script for
compliance. The best you can do is to test it on the browsers you have
access to and hope for the best.

Because of the ever changing and vastly varying support for the
language across platforms and browsers, _transpilation_ has emerged as
a common idiom to address this. Transpilation mostly amounts to
JavaScript code being converted to JavaScript that complies with a
specific ES version or a particular environment. For example `import
Bar from 'foo';` might become `var Bar = require('foo');`. And so if a
particular feature is not supported, it can be made available with the
help of the right plug-in or transpiler. I suspect that the
transpilation proliferation phenomenon has led to additional problems,
such as the input expected by a transpiler assuming existence of a
feature that is no longer supported, same with output. Often this
might be remedied by additional plugins, and it can be very difficult
to sort out. On more than one occasion I spent a lot of time trying to
get something to work only to find out later that my entire approach
has been obsoleted by a new and better solution now built-in to some
other tool.

### JS Frameworks ###

There also seems to be a lot of disagreement on which JS framework is
best. It is even more confusing because the same framework can be so
radically different from one version to the next I wonder why they
didn't just change the name.

I have no idea which is best, and I only had the patience to try a
couple. About a year ago I spent a bunch of time tinkering with
AngularJS, and this time, for a change, I tinkered with React. For me,
I think React makes more sense, and so this is what this example app
is using, for better or worse.

### React and JSX ###

If you don't know what React is, here's my (technically incorrect)
explanation: it's HTML embedded in JavaScript. We're all so
brainwashed into JavaScript being embedded in HTML as the natural
order of things, that inverting this relationship does not even occur
as a possibility. For the fundamental simplicity of this revolutionary (sic)
concept I think React is quite brilliant.

A react "Hello World!" looks approximately like this:

{% codeblock lang:javascript %}
class Hello extends React.Component {
  render() {
    let who = "World";
    return (
      <h1> Hello {who}! </h1>
    );
  }
}
{% endcodeblock %}

Notice how the HTML just begins without any escape or
delimiter. Surprisingly, the opening "<" works quite reliably as the
marker signifying beginning of HTML. Once inside HTML, the opening
curly brace indicates that we're back to JavaScript temporarily, and
this is how variable values are interpolated inside HTML. That's pretty
much all you need to know to "get" React.

Technically, the above file format is known as `JSX`, while React is
the library which provides the classes used to construct React objects
such as `React.Component` above. JSX is transpiled into regular
JavaScript by a tool known as Babel, and in fact JSX is not even
required, a React component can be written in plain JavaScript, and
there is a school of thought whereby React is used without JSX. I
personally find the JSX-less approach a little too noisy, and I also
like that Babel allows you to use a more modern dialect of JS (though
not having to deal with a transpiler is definitely a win).

### Minimal Working Example ###

First, we need three pieces of external JavaScript. They are (1) React
and ReactDOM, (2) Babel in-browser transpiler and (3) a little lib
called Axios which useful for making JSON HTTP requests. I get them
out of Cloudflare CDN, there are probably other ways. To do this, we
need to augment our `indexHTML` variable to look like this:

{% codeblock lang:go %}
const (
	cdnReact           = "https://cdnjs.cloudflare.com/ajax/libs/react/15.5.4/react.min.js"
	cdnReactDom        = "https://cdnjs.cloudflare.com/ajax/libs/react/15.5.4/react-dom.min.js"
	cdnBabelStandalone = "https://cdnjs.cloudflare.com/ajax/libs/babel-standalone/6.24.0/babel.min.js"
	cdnAxios           = "https://cdnjs.cloudflare.com/ajax/libs/axios/0.16.1/axios.min.js"
)

const indexHTML = `
<!DOCTYPE HTML>
<html>
  <head>
    <meta charset="utf-8">
    <title>Simple Go Web App</title>
  </head>
  <body>
    <div id='root'></div>
    <script src="` + cdnReact + `"></script>
    <script src="` + cdnReactDom + `"></script>
    <script src="` + cdnBabelStandalone + `"></script>
    <script src="` + cdnAxios + `"></script>
    <script src="/js/app.jsx" type="text/babel"></script>
  </body>
</html>
`
{% endcodeblock %}

At the very end it now loads `"/js/app.jsx"` which we need to
accommodate as well. Back in part 1 we created a UI config variable
called `cfg.Assets` using `http.Dir()`. We now need to wrap it in
a handler which serves files, and Go conveniently provides one:

{% codeblock lang:go %}
    http.Handle("/js/", http.FileServer(cfg.Assets))
{% endcodeblock %}

With the above, all the files in `"assets/js"` become available under
`"/js/"`.

Finally we need to create the `assets/js/app.jsx` file itself:
{% codeblock lang:go %}
class Hello extends React.Component {
  render() {
    let who = "World";
    return (
      <h1> Hello {who}! </h1>
    );
  }
}

ReactDOM.render( <Hello/>, document.querySelector("#root"));
{% endcodeblock %}

The only difference from the previous listing is the very last line,
which is what makes the app actually render itself.

If we now hit the index page from a (JS-capable) browser, we should see a "Hello
World".

What happened was that the browser loaded "app.jsx" as it was
instructed, but since "jsx" is not a file type it is familiar with, it
simply ignored it. When Babel got its chance to run, it scanned our
document for any script tags referencing "text/babel" as its type, and
re-requested those pages (which makes them show up twice in developer
tools, but the second request ought to served entirely from cache). It
then transpiled it to valid JavaScript and executed it, which in turn
caused React to actually render the "Hello World".

### Listing People ###

We need to first go back to the server side and create a handler that
lists people. In order for that to happen, we need an http handler,
which might look like this:

{% codeblock lang:go %}
func peopleHandler(m *model.Model) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		people, err := m.People()
		if err != nil {
			http.Error(w, "This is an error", http.StatusBadRequest)
			return
		}

		js, err := json.Marshal(people)
		if err != nil {
			http.Error(w, "This is an error", http.StatusBadRequest)
			return
		}

		fmt.Fprintf(w, string(js))
	})
}
{% endcodeblock %}

And we need to register it:
{% codeblock lang:go %}
    http.Handle("/people", peopleHandler(m))
{% endcodeblock %}

Now if we hit `"/people"`, we should get a `"[]"` in response. If we
insert a record into our people table with something along the lines
of:

{% codeblock lang:sql %}
INSERT INTO people (first, last) VALUES('John', 'Doe');
{% endcodeblock %}

The response should change to `[{"Id":1,"First":"John","Last":"Doe"}]`.

Finally we need to hook up our React/JSX code to make it all
render.

For this we are going to create a `PersonItem` component, and
another one called `PeopleList` which will use `PersonItem`.

A `PersonItem` only needs to know how to render itself as a table row:

{% codeblock lang:javascript %}
class PersonItem extends React.Component {
  render() {
    return (
      <tr>
        <td> {this.props.id}    </td>
        <td> {this.props.first} </td>
        <td> {this.props.last}  </td>
      </tr>
    );
  }
}
{% endcodeblock %}

A `PeopleList` is slightly more complicated:

{% codeblock lang:javascript %}
class PeopleList extends React.Component {
  constructor(props) {
    super(props);
    this.state = { people: [] };
  }

  componentDidMount() {
    this.serverRequest =
      axios
        .get("/people")
        .then((result) => {
           this.setState({ people: result.data });
        });
  }

  render() {
    const people = this.state.people.map((person, i) => {
      return (
        <PersonItem key={i} id={person.Id} first={person.First} last={person.Last} />
      );
    });

    return (
      <div>
        <table><tbody>
          <tr><th>Id</th><th>First</th><th>Last</th></tr>
          {people}
        </tbody></table>

      </div>
    );
  }
}
{% endcodeblock %}

It has a constructor which initializes a `this.state` variable. It
also declared a `componentDidMount()` method, which React will call
when the component is about to be rendered, making it the (or one of)
correct place to fetch the data from the server. It fetches the data
via an Axios call, and saves the result in
`this.state.people`. Finally, `render()` iterates over the contents of
`this.state.people` creating an instance of `PersonItem` for each.

That's it, our app now responds with a (rather ugly) table listing
people from our database.


### Conclusion ###

In essence, this is all you need to know to make fully functional Web
App in Go. This app has a number of shortcomings, which I will
hopefully address later. For example in-browser transpilation is not
ideal, though it might be fine for a low volume internal app where
page load time is not important, so we might want to have a way to
pre-transpile it ahead of time. Also our JSX is confined to a single
file, this might get hard to manage for any serious size app where
there are lots of components. The app has no navigation. There is no
styling. There are probably things I'm forgetting about...

Enjoy!

P.S. Complete code is [here](https://github.com/grisha/gowebapp)

Continued in [part 4](/blog/2017/05/02/go-web-app-part-4/)...
