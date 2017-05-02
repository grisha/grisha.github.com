---
layout: post
title: "Building a Go Web App - Part 2"
date: 2017-04-28 15:59
comments: true
categories:
published: true
---

This is a continuation of [part 1](/blog/2017/04/27/simplistic-go-web-app/).
(There is also [part 3](/blog/2017/05/01/go-web-app-part-3/)).

So our app is going to have two major parts to it: client and
server. (What year is this?). The server side is going to be in Go,
and the client side in JS. Let's talk about the server side first.

## The Go (Server) Side ##

The server side of our application is going to be responsible for
initially serving up all the necessary JavaScript and supporting files
if any, aka static assets and data in the form of JSON. That's it,
just two functions: (1) static assets and (2) JSON.

It's worth noting that serving assets is optional: assets could be
served from a CDN, for example. But what is different is that it is not
a problem for our Go app, unlike a Python/Ruby app it can perform on
par with Ngnix and Apache serving static assets. Delegating assets to
another piece of software to lighten its load is no longer necessary,
though certainly makes sense in some situations.

To make this simpler, let's pretend we're making an app that lists
people (just first and last name) from a database table, that's
it. The code is here [https://github.com/grisha/gowebapp](https://github.com/grisha/gowebapp).

### Directory Layout ###

It has been my experience that dividing functionality across packages
early on is a good idea in Go. Even if it is not completely clear how
the final program will be structured, it is good to keep things
separate to the extent possible.

For a web app I think something along the lines of the following
layout makes sense:

```
# github.com/user/foo

foo/            # package main
  |
  +--daemon/    # package daemon
  |
  +--model/     # package model
  |
  +--ui/        # package ui
  |
  +--db/        # package db
  |
  +--assets/    # where we keep JS and other assets
```

### Top level: `package main` ###

At the top level we have package `main` and its code in `main.go`. The
key advantage here is that with this layout `go get github.com/user/foo`
can be the only command required to install the whole application into
`$GOPATH/bin`.

Package `main` should do as little as possible. The only code that
belongs here is to parse the command argument flags. If the app had a
config file, I'd stick parsing and checking of that file into yet
another package, probably called `config`. After that main should pass
the control to the `daemon` package.

An essential main.go is:
{% codeblock lang:go %}
package main

import (
    "github.com/user/foo/daemon"
)

var assetsPath string

func processFlags() *daemon.Config {
    cfg := &daemon.Config{}

    flag.StringVar(&cfg.ListenSpec, "listen", "localhost:3000", "HTTP listen spec")
    flag.StringVar(&cfg.Db.ConnectString, "db-connect", "host=/var/run/postgresql dbname=gowebapp sslmode=disable", "DB Connect String")
    flag.StringVar(&assetsPath, "assets-path", "assets", "Path to assets dir")

    flag.Parse()
    return cfg
}

func setupHttpAssets(cfg *daemon.Config) {
    log.Printf("Assets served from %q.", assetsPath)
    cfg.UI.Assets = http.Dir(assetsPath)
}

func main() {
    cfg := processFlags()

    setupHttpAssets(cfg)

    if err := daemon.Run(cfg); err != nil {
        log.Printf("Error in main(): %v", err)
    }
}
{% endcodeblock %}

The above program accepts three parameters, `-listen`, `-db-connect`
and `-assets-path`, nothing earth shattering.

#### Using structs for clarity ####

In line `cfg := &daemon.Config{}` we are creating a `daemon.Config`
object. It's main purpose is to pass around configuration in a
structured and clear format. Every one of our packages defines its own
`Config` type describing the parameters it needs, and packages can
include other package configs. We see an example of this in
`processFlags()` above: `flag.StringVar(&cfg.Db.ConnectString,
...`. Here `db.Config` is included in `daemon.Config`. I find doing
this very useful. These structures also keep open the possibility of
serializing configs as JSON, TOML or whatever.

#### Using http.FileSystem to serve assets ####

The `http.Dir(assetsPath)` in `setupHttpAssets` is in preparation to
how we will serve the assets in the `ui` package. The reason it's done
this way is to leave the door open for `cfg.UI.Assets` (which is a
`http.FileSystem` interface) to be provided by other implementations,
e.g. serving this content from memory.  I will describe it in more
detail in a later post.

Lastly, main calls `daemon.Run(cfg)` which is what actually starts our
app and where it blocks until it's terminated.

### `package daemon` ###

Package `daemon` contains everything related to running a
process. Stuff like which port to listen on, custom logging would
belong here, as well anything related to a graceful restart, etc.

Since the job of the `daemon` package is to initiate the database
connection, it will need to import the `db` package. It's also
responsible for listening on the TCP port and starting the user
interface for that listener, therefore it needs to import the `ui`
package, and since the `ui` package needs to access data, which is
done via the `model` package, it will need to import `model` as well.

A bare bones `daemon` might look like this:
{% codeblock lang:go %}
package daemon

import (
    "log"
    "net"
    "os"
    "os/signal"
    "syscall"

    "github.com/grisha/gowebapp/db"
    "github.com/grisha/gowebapp/model"
    "github.com/grisha/gowebapp/ui"
)

type Config struct {
    ListenSpec string

    Db db.Config
    UI ui.Config
}

func Run(cfg *Config) error {
    log.Printf("Starting, HTTP on: %s\n", cfg.ListenSpec)

    db, err := db.InitDb(cfg.Db)
    if err != nil {
        log.Printf("Error initializing database: %v\n", err)
        return err
    }

    m := model.New(db)

    l, err := net.Listen("tcp", cfg.ListenSpec)
    if err != nil {
        log.Printf("Error creating listener: %v\n", err)
        return err
    }

    ui.Start(cfg.UI, m, l)

    waitForSignal()

    return nil
}

func waitForSignal() {
    ch := make(chan os.Signal)
    signal.Notify(ch, syscall.SIGINT, syscall.SIGTERM)
    s := <-ch
    log.Printf("Got signal: %v, exiting.", s)
}
{% endcodeblock %}

Note how `Config` includes `db.Config` and `ui.Config` as I described
earlier.

All the action happens in `Run(*Config)`. We initialize a database
connection, create a `model.Model` instance, and start the `ui`
passing in the config, a pointer to the model and the listener.

### `package model` ###

The purpose of `model` is to separate how data is stored in the
database from the `ui`, as well as to contain any business logic an
app might have. It's the brains of the app if you will.

The `model` package should define a struct (`Model` seems like an
appropriate name) and a pointer to an instance of the struct should be
passed to all the `ui` functions and methods. There should only be one
such instance in our app - for extra credit you can enforce that
programmatically by making it a singleton, but I don't think that's
necessary.

Alternatively you could get by without a `Model` and just use the
package `model` itself. I don't like this approach, but it's an
option.

The model should also define structs for the data entities we are
dealing with. In our example it would be a `Person` struct. Its
members should be exported (capitalized) because other packages will
be accessing those. If you use
[sqlx](https://github.com/jmoiron/sqlx), this is where you would also
specify tags that map elements to db column names, e.g. `` `db:"first_name"` ``

Our Person type:
{% codeblock lang:go %}
type Person struct {
    Id          int64
    First, Last string
}
{% endcodeblock %}

In our case we do not need tags because our column names match the
element names, and sqlx conveniently takes care of the capitalization,
so `Last` matches the column named `last`.

#### package model should NOT import db ####

Somewhat counter-intuitive, `model` cannot import `db`. This is
because `db` needs to import `model`, and circular imports are not
allowed in Go. This is one case where interfaces come in
handy. `model` needs to define an interface which `db` should
satisfy. For now all we know is we need to list people, so we can
start with this definition:

{% codeblock lang:go %}
type db interface {
    SelectPeople() ([]*Person, error)
}
{% endcodeblock %}

Our app doesn't really do much, but we know it lists people, so our
model should probably have a `People() ([]*Person, error)` method:

{% codeblock lang:go %}
func (m *Model) People() ([]*Person, error) {
    return m.SelectPeople()
}
{% endcodeblock %}

To keep things tidy, code should be in separate files, e.g. `Person`
definition should be in `person.go`, etc. For readability, here is a
single file version of our `model`:

{% codeblock lang:go %}
package model

type db interface {
    SelectPeople() ([]*Person, error)
}

type Model struct {
    db
}

func New(db db) *Model {
    return &Model{
        db: db,
    }
}

func (m *Model) People() ([]*Person, error) {
    return m.SelectPeople()
}

type Person struct {
    Id          int64
    First, Last string
}
{% endcodeblock %}

### `package db` ###

`db` is the actual implementation of the database interaction. This is
where the SQL statements are constructed and executed. This package
also imports `model` because it will need to construct those structs
from database data.

First, `db` needs to provide the `InitDb` function which will
establish the database connection, as well as create the necessary
tables and prepare the SQL statements.

Our simplistic example doesn't support migrations, but in theory this
is also where they might potentially happen.

We are using PostgreSQL, which means we need to import the
[pq](https://github.com/lib/pq) driver. We are also going to rely on
sqlx, and we need our own `model`. Here is the beginning of our `db`
implementation:

{% codeblock lang:go %}
package db

import (
    "database/sql"

    "github.com/grisha/gowebapp/model"
    "github.com/jmoiron/sqlx"
    _ "github.com/lib/pq"
)

type Config struct {
    ConnectString string
}

func InitDb(cfg Config) (*pgDb, error) {
    if dbConn, err := sqlx.Connect("postgres", cfg.ConnectString); err != nil {
        return nil, err
    } else {
        p := &pgDb{dbConn: dbConn}
        if err := p.dbConn.Ping(); err != nil {
            return nil, err
        }
        if err := p.createTablesIfNotExist(); err != nil {
            return nil, err
        }
        if err := p.prepareSqlStatements(); err != nil {
            return nil, err
        }
        return p, nil
    }
}
{% endcodeblock %}

Out `InitDb()` creates an instance of a `pgDb`, which is our Postgres
implementation of the `model.db` interface. It keeps all that we need
to communicate with the database, including the prepared statements,
and exports the necessary methods to satisfy the interface.

{% codeblock lang:go %}
type pgDb struct {
    dbConn *sqlx.DB

    sqlSelectPeople *sqlx.Stmt
}
{% endcodeblock %}

Here is the code to create the tables and the statements. From the SQL
perspective this is rather simplistic, it could be a lot more
elaborate, of course:

{% codeblock lang:go %}
func (p *pgDb) createTablesIfNotExist() error {
    create_sql := `

       CREATE TABLE IF NOT EXISTS people (
       id SERIAL NOT NULL PRIMARY KEY,
       first TEXT NOT NULL,
       last TEXT NOT NULL);

    `
    if rows, err := p.dbConn.Query(create_sql); err != nil {
        return err
    } else {
        rows.Close()
    }
    return nil
}

func (p *pgDb) prepareSqlStatements() (err error) {

    if p.sqlSelectPeople, err = p.dbConn.Preparex(
        "SELECT id, first, last FROM people",
    ); err != nil {
        return err
    }

    return nil
}
{% endcodeblock %}

Finally, we need to provide the method to satisfy the interface:

{% codeblock lang:go %}
    people := make([]*model.Person, 0)
    if err := p.sqlSelectPeople.Select(&people); err != nil {
        return nil, err
    }
    return people, nil
{% endcodeblock %}

Here we're taking advantage of sqlx to run the query and construct a
slice from results with a simple call to `Select()` (NB:
`p.sqlSelectPeople` is a `*sqlx.Stmt`). Without sqlx we would have to
iterate over the result rows, processing each with `Scan`, which would
be considerably more verbose.

Beware of a very subtle "gotcha" here. `people` could also be defined
as `var people []*model.Person` and the method would work just the
same. However, if the database returned no rows, the method would
return `nil`, not an empty slice. If the result of this method is
later encoded as JSON, the former would become `null` and the latter
`[]`. This could cause problems if the client side doesn't know how to
treat `null`.

That's it for `db`.

### package ui ###

Finally, we need to serve all that stuff via HTTP and that's what the
`ui` package does.

Here is a very simplistic variant:

{% codeblock lang:go %}
package ui

import (
    "fmt"
    "net"
    "net/http"
    "time"

    "github.com/grisha/gowebapp/model"
)

type Config struct {
    Assets http.FileSystem
}

func Start(cfg Config, m *model.Model, listener net.Listener) {

    server := &http.Server{
        ReadTimeout:    60 * time.Second,
        WriteTimeout:   60 * time.Second,
        MaxHeaderBytes: 1 << 16}

    http.Handle("/", indexHandler(m))

    go server.Serve(listener)
}

const indexHTML = `
<!DOCTYPE HTML>
<html>
  <head>
    <meta charset="utf-8">
    <title>Simple Go Web App</title>
  </head>
  <body>
    <div id='root'></div>
  </body>
</html>
`

func indexHandler(m *model.Model) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprintf(w, indexHTML)
    })
}
{% endcodeblock %}

Note how `indexHTML` contains next to nothing. This is 100% of the
HTML that this app will ever serve. It will evolve a little as we get
into the client side of the app, but only by a few lines.

Also noteworthy is how the handler is defined. If this idiom is not
familiar, it's worth spending a few minutes (or a day) to internalize
it completely as it is very common in Go. `indexHandler()` is not a
handler, it _returns_ a handler function. It is done this way so
that we can pass in a `*model.Model` via closure, since an HTTP
handler function definition is fixed and a model pointer is not one of
the parameters.

In the case of `indexHandler()` we're not actually doing anything with
the model pointer, but when we get to implementing an actual list of
people we will need it.

### Conclusion ###

Above is essentially all the knowledge required to build a basic Go
web app, at least the Go side of it. Next week I'll get into the
client side and we will complete the people listing code.

Continue to [part 3](/blog/2017/05/01/go-web-app-part-3/).
