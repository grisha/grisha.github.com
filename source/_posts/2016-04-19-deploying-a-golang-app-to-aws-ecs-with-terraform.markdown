---
layout: post
title: "Deploying a Golang app to AWS ECS with Terraform"
date: 2016-04-19 10:53
comments: true
categories:
---

I've put together a basic example of a "Hello World" Go program which
runs in Amazon AWS Elastic Compute Service (ECS), which allows running
applications in Docker containers and has the ability to scale on
demand.

I initially wanted to write about the components of this system and
the tools you use to deploy your application, but soon realized that
this would make for an extremely long post, as the number of
components required for a simple "Hello World" is mind
boggling. However problematic it may seem, it's par for the course,
this is what takes to run an application in our cloudy times.

I used [Terraform](https://github.com/hashicorp/terraform) to build
all the AWS infrastructure. Initially I was skeptical on how well it
could accomplish such a tedious task, but I have say my confidence in
Terraform grew the more I used it.

The main top level tool for everything is the good old
[make](https://en.wikipedia.org/wiki/Make_%28software%29),a tool that
stood the test of time.

Here is the code of the example, read the README, I hope you find it
useful:

[https://github.com/grisha/hello-go-ecs-terraform](https://github.com/grisha/hello-go-ecs-terraform)
