---
layout: post
title: "Graceful restart in Golang"
date: 2014-06-03 12:49
comments: true
categories:
---

Update (Apr 2015): [Florian von Bock](https://github.com/fvbock) has
turned what is described in this article into a nice Go package called
[endless](https://github.com/fvbock/endless).

If you have a Golang HTTP service, chances are, you will need to restart it
on occasion to upgrade the binary or change some configuration. And if
you (like me) have been taking graceful restart for granted because
the webserver took care of it, you may find this recipe very handy
because with Golang you need to roll your own.

There are actually two problems that need to be solved here. First is
the UNIX side of the graceful restart, i.e. the mechanism by which a
process can restart itself without closing the listening socket. The
second problem is ensuring that all in-progress requests are properly
completed or timed-out.

## Restarting without closing the socket

* Fork a new process which inherits the listening socket.
* The child performs initialization and starts accepting connections on
  the socket.
* Immediately after, child sends a signal to the parent causing the
  parent to stop accepting connecitons and terminate.

### Forking a new process

There is more than one way to fork a process using the Golang lib, but
for this particular case
[exec.Command](http://golang.org/pkg/os/exec/#Command) is the way to
go. This is because the [Cmd struct](http://golang.org/pkg/os/exec/#Cmd) this function returns has
this `ExtraFiles` member, which specifies open files (in addition to
stdin/err/out) to be inherited by new process.

Here is what this looks like:

```go
    file := netListener.File() // this returns a Dup()
    path := "/path/to/executable"
    args := []string{
        "-graceful"}

    cmd := exec.Command(path, args...)
    cmd.Stdout = os.Stdout
    cmd.Stderr = os.Stderr
    cmd.ExtraFiles = []*os.File{file}

    err := cmd.Start()
    if err != nil {
        log.Fatalf("gracefulRestart: Failed to launch, error: %v", err)
    }
```

In the above code `netListener` is a pointer to
[net.Listener](http://golang.org/pkg/net/#Listener) listening for HTTP
requests. The `path` variable should contain the path to the new
executable if you're upgrading (which may be the same as the currently
running one).

An important point in the above code is that `netListener.File()`
returns a
[dup(2)](http://pubs.opengroup.org/onlinepubs/009695399/functions/dup.html)
of the file descriptor. The duplicated file descriptor will not have
the [`FD_CLOEXEC` flag](http://pubs.opengroup.org/onlinepubs/009695399/functions/fcntl.html) set,
which would cause the file to be closed in the child (not what we want).

You may come across examples that pass the inherited file descriptor
number to the child via a command line argument, but the way
`ExtraFiles` is implemented makes it unnecessary. The documentation
states that "If non-nil, entry i becomes file descriptor 3+i." This
means that in the above code snippet, the inherited file descriptor in
the child will always be 3, thus no need to explicitely pass it.

Finally, `args` array contains a `-graceful` option: your program will
need some way of informing the child that this is a part of a graceful
restart and the child should re-use the socket rather than try opening
a new one. Another way to do this might be via an environment
variable.

### Child initialization

Here is part of the program startup sequence

```go

    server := &http.Server{Addr: "0.0.0.0:8888"}

    var gracefulChild bool
    var l net.Listever
    var err error

    flag.BoolVar(&gracefulChild, "graceful", false, "listen on fd open 3 (internal use only)")

    if gracefulChild {
        log.Print("main: Listening to existing file descriptor 3.")
        f := os.NewFile(3, "")
        l, err = net.FileListener(f)
    } else {
        log.Print("main: Listening on a new file descriptor.")
        l, err = net.Listen("tcp", server.Addr)
    }

```

### Signal parent to stop

At this point we're ready to accept requests, but just before we do
that, we need to tell our parent to stop accepting requests and exit,
which could be something like this:

```go
    if gracefulChild {
        parent := syscall.Getppid()
        log.Printf("main: Killing parent pid: %v", parent)
        syscall.Kill(parent, syscall.SIGTERM)
    }

    server.Serve(l)
```

## In-progress requests completion/timeout

For this we will need to keep track of open connections with a
[sync.WaitGroup](http://golang.org/pkg/sync/#WaitGroup). We will need
to increment the wait group on every accepted connection and decrement
it on every connection close.

```go
var httpWg sync.WaitGroup
```

At first glance, the Golang standard http package does not provide any
hooks to take action on Accept() or Close(), but this is where the
interface magic comes to the rescue. (Big thanks and credit to [Jeff R. Allen](http://nella.org/jra/)
for [this post](http://blog.nella.org/zero-downtime-upgrades-of-tcp-servers-in-go/)).

Here is an example of a listener which increments a wait group on
every Accept(). First, we "subclass" `net.Listener` (you'll see why we
need `stop` and `stopped` below):

```go
type gracefulListener struct {
    net.Listener
    stop    chan error
    stopped bool
}
```

Next we "override" the Accept method. (Nevermind `gracefulConn` for
now, it will be introduced later).

```go
func (gl *gracefulListener) Accept() (c net.Conn, err error) {
    c, err = gl.Listener.Accept()
    if err != nil {
        return
    }

    c = gracefulConn{Conn: c}

    httpWg.Add(1)
    return
}
```

We also need a "constructor":

```go
func newGracefulListener(l net.Listener) (gl *gracefulListener) {
    gl = &gracefulListener{Listener: l, stop: make(chan error)}
    go func() {
        _ = <-gl.stop
        gl.stopped = true
        gl.stop <- gl.Listener.Close()
    }()
    return
}
```

The reason the function above starts a goroutine is because this
cannot be done in our `Accept()` above since it will block on
`gl.Listener.Accept()`. The goroutine will unblock it by closing file
descriptor.

Our `Close()` method simply sends a `nil` to the stop channel for the
above goroutine to do the rest of the work.

```go
func (gl *gracefulListener) Close() error {
    if gl.stopped {
        return syscall.EINVAL
    }
    gl.stop <- nil
    return <-gl.stop
}
```

Finally, this little convenience method extracts the file descriptor
from the `net.TCPListener`.

```go
func (gl *gracefulListener) File() *os.File {
    tl := gl.Listener.(*net.TCPListener)
    fl, _ := tl.File()
    return fl
}
```

And, of course we also need a variant of a
[`net.Conn`](http://golang.org/pkg/net/#Conn) which decrements the
wait group on `Close()`:

```go
type gracefulConn struct {
    net.Conn
}

func (w gracefulConn) Close() error {
    httpWg.Done()
    return w.Conn.Close()
}
```

To start using the above graceful version of the Listener, all we need
is to change the `server.Serve(l)` line to:

```go
    netListener = newGracefulListener(l)
    server.Serve(netListener)
```

And there is one more thing. You should avoid hanging connections that
the client has no intention of closing (or not this week). It is
better to create your server as follows:

```go
server := &http.Server{
        Addr:           "0.0.0.0:8888",
        ReadTimeout:    10 * time.Second,
        WriteTimeout:   10 * time.Second,
        MaxHeaderBytes: 1 << 16}
```
