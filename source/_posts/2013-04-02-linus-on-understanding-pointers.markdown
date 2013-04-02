---
layout: post
title: "Linus on understanding pointers"
date: 2013-04-02 10:52
comments: true
categories: 
---

A while back [Linus Torvalds](http://en.wikipedia.org/wiki/Linus_Torvalds) [answered questions on Slashdot](http://meta.slashdot.org/story/12/10/11/0030249/linus-torvalds-answers-your-questions).

One of the answers was on the subject of understanding of pointers:

><small>At the opposite end of the spectrum, I actually wish more people
understood the really core low-level kind of coding. Not big, complex
stuff like the lockless name lookup, but simply good use of
pointers-to-pointers etc. For example, I've seen too many people who
delete a singly-linked list entry by keeping track of the "prev"
entry, and then to delete the entry, doing something like</small>

><small>if (prev)<br/>
  prev->next = entry->next;<br/>
else<br/>
  list_head = entry->next;<br/>
</small>

><small>and whenever I see code like that, I just go "This person doesn't
understand pointers". And it's sadly quite common.</small>

><small>People who understand pointers just use a "pointer to the entry
pointer", and initialize that with the address of the list_head. And
then as they traverse the list, they can remove the entry without
using any conditionals, by just doing a "*pp = entry->next"</small>

There were a few comments, but none explained what he really
meant. So here it is.

Imagine you have a linked list defined as:

```c
typedef struct list_entry {
    int val;
    struct list_entry *next;
} list_entry;
```

You need to iterate over it from the begining to end and remove a
specific element whose value equals the value of `to_remove`. The more
obvious way to do this would be:

```c
    list_entry *entry = head; /* assuming head exists and is the first entry of the list */
    list_entry *prev = NULL;

    while (entry) {
        if (entry->val == to_remove)     /* this is the one to remove */
            if (prev)
               prev->next = entry->next; /* remove the entry */
            else
                head = entry->next;      /* special case - first entry */

        /* move on to the next entry */
        prev = entry;
        entry = entry->next;
    }
```

What we are doing above is iterating over the list until `entry` is
NULL, which means we've reached the end of the list (line 4). When we
come across an entry we want removed (line 5), we assign the value of
current `next` pointer to the previous one, thus eliminating the
current element (line 7).

There is a special case above - at the beginning of the iteration
there is no previous entry (`prev` is NULL), and so to remove the
first entry in the list you have to modify `head` itself (line 9).

What Linus was saying is that the above code could be simplified by
making the previous element a *pointer to a pointer* rather than just a
pointer. The code then looks like this:

```c
    list_entry **pp = &head; /* pointer to a pointer */
    list_entry *entry = head;

    while (entry) {
        if (entry->val == to_remove)
            *pp = entry->next;

        pp = &entry->next;
        entry = entry->next;
    }

```

The above code is very similar to the previous variant, but notice how
we no longer need to watch for the special case of the first element
of the list, since `pp` is not NULL at the beginning. Simple and
clever.

Also, someone in that thread commented that the reason this is better
is because `*pp = entry->next` is *atomic*.  It is most certainly NOT
atomic. The above expression contains two dereference operators (`*`
and `->`) and one assignment, and neither of those three things is
atomic. This is a common misconception, but alas pretty much *nothing*
in C should ever be assumed to be atomic (including the `++` and `--`
operators)!






