---
layout: post
title: "Parsing Table Names from SQL"
date: 2016-11-14 14:40
comments: true
categories:
---

Sometimes it is useful to extract table names from an SQL statement,
for example if you are trying to figure out dependencies for your Hive
or BigQuery (or whatever) tables.

It is actually a lot simpler than it seems and you don't need to write
your own SQL parser or find one out there. In SQL table names always
follow the FROM and JOIN keywords. So all you have to do is split the
statemement into tokens, and scan the list for any mention of FROM or
JOIN and grab the next token.

Here is a very simplistic Python function that does this using regular
expressions:

{% codeblock lang:python %}
def tables_in_query(sql_str):

    # remove the /* */ comments
    q = re.sub(r"/\*[^*]*\*+(?:[^*/][^*]*\*+)*/", "", sql_str)

    # remove whole line -- and # comments
    lines = [line for line in q.splitlines() if not re.match("^\s*(--|#)", line)]

    # remove trailing -- and # comments
    q = " ".join([re.split("--|#", line)[0] for line in lines])

    # split on blanks, parens and semicolons
    tokens = re.split(r"[\s)(;]+", q)

    # scan the tokens. if we see a FROM or JOIN, we set the get_next
    # flag, and grab the next one (unless it's SELECT).

    result = set()
    get_next = False
    for tok in tokens:
        if get_next:
            if tok.lower() not in ["", "select"]:
                result.add(tok)
            get_next = False
        get_next = tok.lower() in ["from", "join"]

    return result
{% endcodeblock %}

This is obviously not perfect, for example in BigQuery there is a
possibility that what follows `SELECT` is a UDF name, but I'll leave
working around that as an exercise for the reader.
