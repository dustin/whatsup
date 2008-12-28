---
layout: default
title: dustin/whatsup @ GitHub
---
Whatsup monitors web pages for you while you're online and lets you know
that they're operational and returning content that is interesting to
you.

To try it out, add [whatsup@jabber.org](xmpp:whatsup@jabber.org) to your roster
and have a blast.

## Dependencies
* Twisted (names, web, words)
* SQLAlchemy

## Install

1. Install dependencies
2. git submodule init &amp;&amp; git submodule update
3. copy whatsup.conf.sample to whatsup.conf
4. edit whatsup.conf
5. ./etc/create\_tables.py
6. twisted -ny whatsup.tac

## License

[MIT](http://www.opensource.org/licenses/mit-license.php)

## Authors

* Dustin Sallings (dustin@spy.net)
* Chris Eppstein (chris@eppsteins.net)
* dag (dag.odenhall@gmail.com)

## Contact

Dustin Sallings (dustin@spy.net)

You can download this project in either [zip][1] or [tar][2] formats.

You can also clone the project with [git](http://git-scm.com/) by running:

    $ git clone git://github.com/dustin/whatsup.git

[1]:http://github.com/dustin/whatsup/zipball/master
[2]:http://github.com/dustin/whatsup/tarball/master

