---
layout: post
title: "Ruby, HiveServer2 and Kerberos"
date: 2014-08-19 08:03
comments: true
categories:
---

Recently I found myself needing to connect to HiveServer2 with
Kerberos authentication enabled from a Ruby app. As it turned out
[rbhive gem](https://github.com/forward3d/rbhive) we were using did not have
support for Kerberos authentication. So I had to
[roll my own](https://github.com/forward3d/rbhive/pull/23).

This post is to document the experience of figuring out the details of
a SASL/GSSAPI connection before it is lost forever in my neurons and synapses.

First, the terminology. The authentication system that Hadoop uses is
_Kerberos_. Note that [Kerberos](http://www.ietf.org/rfc/rfc4120.txt) is not a
network protocol. It describes the method by which
authentication happens, but not the format of how to send Kerberos
tickets and what not over the wire. For that, you need _SASL_ and
_GSSAPI_.

[SASL](http://tools.ietf.org/html/rfc2222) is a generic protocol
designed to be able to wrap just about any authentication
handshake. It's very simple: the client sends a START followed by some
payload, and expects an OK, BAD or COMPLETE from the server. OK means
that there are more steps to this conversation, BAD is
self-explanatory and COMPLETE means "I'm satisfied". The objective is
to go from START via a series of OK's to each side sending the other a
COMPLETE.

SASL doesn't define the payload of each message. The payload is
specified by [GSSAPI](http://tools.ietf.org/html/rfc2743)
protocol. GSSAPI is another generic protocol. Unlike SASL it is
actually very complex and covers a variety of authentication methods,
including Kerberos.

The combination of SASL and GSSAPI and what happens at the network
layer is documented in
[RFC4752](http://tools.ietf.org/html/rfc4752).

Bottom line is you need to read at least four RFC's to be able to
understand every detail of this process:
[RFC4120](http://tools.ietf.org/html/rfc4120),
[RFC2222](http://tools.ietf.org/html/rfc2222),
[RFC2743](http://tools.ietf.org/html/rfc2743) and
[RFC4752](http://tools.ietf.org/html/rfc4752). Fun!

## The Handshake in Ruby

First, you'll need some form of binding to the GSSAPI libraries. I've
been using the most excellent [GSSAPI gem](https://github.com/zenchild/gssapi)
by [Dan Wanek](http://distributed-frostbite.blogspot.ru/) which wraps the MIT GSSAPI library.

If you follow the code in
[sasl_client_transport.rb](https://github.com/grisha/rbhive/blob/gssapi/lib/thrift/sasl_client_transport.rb),
you'll see the following steps are required to establish a connection.

First, we instantiate a GSSAPI object passing it the remote host and
the remote principal. Note that there is no TCP port number to be
specifies anywhere, because this isn't to establish a TCP connection,
but only for Kerberos _host authentication_. (Kerberos requires that
not only the client authenticates itself to the host, but also that
the host authenticates itself to the client.)

```ruby
# Thrift::SaslClientTransport.initialize()
@gsscli = GSSAPI::Simple.new(@sasl_remote_host, @sasl_remote_principal)
```

The rest of the action takes place in the
`initiate_hand_shake_gssapi()` method.

First, we call `@gsscli.init_context()` with no arguments. This call
creates a token based on our current Kerberos credentials. (If there
are no credentials in our cache, this call will fail).

```ruby
      token = @gsscli.init_context
```

Next we compose a SASL message which consists of START (0x01)
followed by payload length, followed by the actual payload, which is
the SASL mechanism name: 'GSSAPI'. Without waiting for response, we
also send an OK (0x02) and the token returned from init_context().

```ruby
      header = [NEGOTIATION_STATUS[:START], @sasl_mechanism.length].pack('cl>')
      @transport.write header + @sasl_mechanism
      header = [NEGOTIATION_STATUS[:OK], token.length].pack('cl>')
      @transport.write header + token
      status, len = @transport.read(STATUS_BYTES + PAYLOAD_LENGTH_BYTES).unpack('cl>')
```

Next we read 5 bytes of response. The first byte is the status
returned from the server, which hopefully is OK, followed by the
length of the payload, and then we read the payload itself:

```ruby
      status, len = @transport.read(STATUS_BYTES + PAYLOAD_LENGTH_BYTES).unpack('cl>')
      case status
      when NEGOTIATION_STATUS[:BAD], NEGOTIATION_STATUS[:ERROR]
        raise @transport.to_io.read(len)
      when NEGOTIATION_STATUS[:COMPLETE]
        raise "Not expecting COMPLETE at initial stage"
      when NEGOTIATION_STATUS[:OK]
        challenge = @transport.to_io.read len
```

The payload is a _challenge_ created for us by the server. We can
verify this challenge by calling `init_context()` a second time, this
time passing in the challenge to verify it:

```ruby
        challenge = @transport.to_io.read len
        unless @gsscli.init_context(challenge)
          raise "GSSAPI: challenge provided by server could not be verified"
        end
```

If the challenge verifies, then it is our turn to send an OK (with an
empty payload this time):

```ruby
        header = [NEGOTIATION_STATUS[:OK], 0].pack('cl>')
        @transport.write header
```

At this point in the SASL 'conversation' we have verified that the
server is who they claim to be.

Next the server sends us another challenge, this one is so that we can
authenticate ourselves to the server and at the same time agree on the
_protection level_ for the communication channel.

We need to decrypt ("unwrap" in the GSSAPI terminology) the challenge,
examine the protection level and if it is acceptable, encrypt it on
our side and send it back to the server in a SASL COMPLETE message. In
this particular case we're agreeable to any level of protection (which
is none in case of HiveServer2, i.e. the conversation is not
encrypted). Otherwise there are additional steps that RFC4752
describes whereby the client can select an acceptable protection
level.

```ruby
        status2, len = @transport.read(STATUS_BYTES + PAYLOAD_LENGTH_BYTES).unpack('cl>')
        case status2
        when NEGOTIATION_STATUS[:BAD], NEGOTIATION_STATUS[:ERROR]
          raise @transport.to_io.read(len)
        when NEGOTIATION_STATUS[:COMPLETE]
          raise "Not expecting COMPLETE at second stage"
        when NEGOTIATION_STATUS[:OK]
          challenge = @transport.to_io.read len
          unwrapped = @gsscli.unwrap_message(challenge)
          rewrapped = @gsscli.wrap_message(unwrapped)
          header = [NEGOTIATION_STATUS[:COMPLETE], rewrapped.length].pack('cl>')
          @transport.write header + rewrapped
```

The server should then respond with COMPLETE as well, at which point
we're done with the authentication process and cat start sending
whatever we want over this connection:

```ruby
          status3, len = @transport.read(STATUS_BYTES + PAYLOAD_LENGTH_BYTES).unpack('cl>')
          case status3
          when NEGOTIATION_STATUS[:BAD], NEGOTIATION_STATUS[:ERROR]
            raise @transport.to_io.read(len)
          when NEGOTIATION_STATUS[:COMPLETE]
            @transport.to_io.read len
            @sasl_complete = true
          when NEGOTIATION_STATUS[:OK]
            raise "Failed to complete GSS challenge exchange"
          end
```
