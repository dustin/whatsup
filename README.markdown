# What's Up?

What's up watches web sites for you and lets you know when they are
unavailable.

# Usage

IM `help` to [whatsup@jabber.org](xmpp://whatsup@jabber.org) to see what you
can do.

# When Checks Are Performed

Any monitors you set up will run about once every fifteen minutes, but only
while you're active on XMPP.

You are considered inactive if any of the following are true:

* You are not logged in to your XMPP server.
* You are logged in, but your status is do not disturb.
* You have specifically told whatsup not to bother you (via the `off` command)

# Running Your Own Instance

It's easy to run your own instance.  You'll need a recent version of
[twisted](http://twistedmatrix.com/trac/) (specifically names, web, and words),
and two items from the [cheese shop](http://www.python.org/pypi):

* SQLAlchemy
* PyYAML

You can install the requirements using <code>easy\_install</code>:

    easy_install SQLAlchemy
    easy_install PyYAML
