import sys
import time
import types
import datetime
import re
import sre_constants

from twisted.words.xish import domish
from twisted.web import client
from sqlalchemy.orm import exc

import models

all_commands={}

class CountingFile(object):
    """A file-like object that just counts what's written to it."""
    def __init__(self):
        self.written=0
    def write(self, b):
        self.written += len(b)
    def close(self):
        pass
    def open(self):
        pass
    def read(self):
        return None

class BaseCommand(object):
    """Base class for command processors."""

    def __get_extended_help(self):
        if self.__extended_help:
            return self.__extended_help
        else:
            return self.help

    def __set_extended_help(self, v):
        self.__extended_help=v

    extended_help=property(__get_extended_help, __set_extended_help)

    def __init__(self, name, help=None, extended_help=None):
        self.name=name
        self.help=help
        self.extended_help=extended_help

    def __call__(self, user, prot, args, session):
        raise NotImplementedError()

    def is_a_url(self, u):
        try:
            s=str(u)
            # XXX:  Any good URL validators?
            return True
        except:
            return False

class ArgRequired(BaseCommand):

    def __call__(self, user, prot, args, session):
        if self.has_valid_args(args):
            self.process(user, prot, args, session)
        else:
            prot.send_plain(user.jid, "Arguments required for %s:\n%s"
                % (self.name, self.extended_help))

    def has_valid_args(self, args):
        return args

    def process(self, user, prot, args, session):
        raise NotImplementedError()

class WatchRequired(BaseCommand):

    def __call__(self, user, prot, args, session):
        if self.has_valid_args(args):
            a=args.split(' ', 1)
            newarg=None
            if len(a) > 1: newarg=a[1]
            try:
                watch=session.query(models.Watch).filter_by(
                    url=a[0]).filter_by(user_id=user.id).one()
                self.process(user, prot, watch, newarg, session)
            except exc.NoResultFound:
                prot.send_plain(user.jid, "Cannot find watch for %s" % a[0])
        else:
            prot.send_plain(user.jid, "Arguments required for %s:\n%s"
                % (self.name, self.extended_help))

    def has_valid_args(self, args):
        return self.is_a_url(args)

    def process(self, user, prot, watch, args, session):
        raise NotImplementedError()

class StatusCommand(BaseCommand):

    def __init__(self):
        super(StatusCommand, self).__init__('status', 'Check your status.')

    def __call__(self, user, prot, args, session):
        rv=[]
        rv.append("Jid:  %s" % user.jid)
        rv.append("Jabber status:  %s" % user.status)
        rv.append("Whatsup status:  %s"
            % {True: 'Active', False: 'Inactive'}[user.active])
        rv.append("You are currently watching %d URLs." % len(user.watches))
        if user.is_quiet():
            rv.append("All alerts are quieted until %s" % str(user.quiet_until))
        prot.send_plain(user.jid, "\n".join(rv))

class GetCommand(ArgRequired):

    def __init__(self):
        super(GetCommand, self).__init__('get', 'Get a web page.')

    def process(self, user, prot, args, session):
        if args:
            start=time.time()
            cf = CountingFile()
            jid=user.jid
            def onSuccess(value):
                prot.send_plain(jid, "Got %d bytes in %.2fs" %
                    (cf.written, (time.time() - start)))
            client.downloadPage(args, cf).addCallbacks(
                callback=onSuccess,
                errback=lambda error:(prot.send_plain(
                    jid, "Error getting the page: %s (%s)"
                    % (error.getErrorMessage(), dir(error)))))
        else:
            prot.send_plain(user.jid, "I need a URL to fetch.")

    def has_valid_args(self, args):
        return self.is_a_url(args)

class HelpCommand(BaseCommand):

    def __init__(self):
        super(HelpCommand, self).__init__('help', 'You need help.')

    def __call__(self, user, prot, args, session):
        rv=[]
        if args:
            c=all_commands.get(args.strip().lower(), None)
            if c:
                rv.append("Help for %s:\n" % c.name)
                rv.append(c.extended_help)
            else:
                rv.append("Unknown command %s." % args)
        else:
            for k in sorted(all_commands.keys()):
                rv.append('%s\t%s' % (k, all_commands[k].help))
        prot.send_plain(user.jid, "\n".join(rv))

class WatchCommand(ArgRequired):

    def __init__(self):
        super(WatchCommand, self).__init__('watch', 'Start watching a page.')

    def process(self, user, prot, args, session):
        w=models.Watch()
        w.url=args
        w.user=user
        user.watches.append(w)
        prot.send_plain(user.jid, "Started watching %s" % w.url)

    def has_valid_args(self, args):
        return self.is_a_url(args)

class UnwatchCommand(WatchRequired):

    def __init__(self):
        super(UnwatchCommand, self).__init__('unwatch', 'Stop watching a page.')

    def process(self, user, prot, watch, args, session):
        session.delete(watch)
        prot.send_plain(user.jid, "Stopped watching %s" % watch.url)

class WatchingCommand(BaseCommand):
    def __init__(self):
        super(WatchingCommand, self).__init__('watching', 'List your watches.')

    def __call__(self, user, prot, args, session):
        watches=[]
        rv=[("You are watching %d URLs:" % len(user.watches))]
        h={True: 'enabled', False: 'disabled'}
        for w in user.watches:
            watches.append("%s %s - (%s -- %d patterns, last=%s)"
                % (w.status_emoticon(), w.url, h[w.active], len(w.patterns),
                `w.status`))
        rv += sorted(watches)
        prot.send_plain(user.jid, "\n".join(rv))

class InspectCommand(WatchRequired):
    def __init__(self):
        super(InspectCommand, self).__init__('inspect', 'Inspect a watch.')

    def process(self, user, prot, w, args, session):
        rv=[]
        rv.append("Status for %s: %s"
            % (w.url, {True: 'enabled', False: 'disabled'}[w.active]))
        if w.is_quiet():
            rv.append("Alerts are quiet until %s" % str(w.quiet_until))
        rv.append("Last update:  %s" % str(w.last_update))
        if w.patterns:
            for p in w.patterns:
                rv.append("\t%s %s" % ({True: '+', False: '-'}[p.positive],
                    p.regex))
        else:
            rv.append("No match patterns configured.")
        prot.send_plain(user.jid, "\n".join(rv))

class BaseMatchCommand(WatchRequired):

    def process(self, user, prot, w, args, session):
        try:
            regex=args
            re.compile(regex) # Check the regex
            m=models.Pattern()
            m.positive=self.isPositive()
            m.regex=regex
            w.patterns.append(m)
            prot.send_plain(user.jid, "Added pattern.")
        except sre_constants.error, e:
            prot.send_plain(user.jid, "Error configuring pattern:  %s" % e.message)

class MatchCommand(BaseMatchCommand):
    def __init__(self):
        super(MatchCommand, self).__init__('match', 'Configure a match for a URL')
        self.extended_help="""Add a positive regex match for a URL.

Usage:  match http://www.example.com/ working
"""

    def isPositive(self):
        return True

class NegMatchCommand(BaseMatchCommand):
    def __init__(self):
        super(NegMatchCommand, self).__init__('negmatch', 'Configure a negative match for a URL')
        self.extended_help="""Add a negative regex match for a URL.

Usage: negmatch http://www.example.com/ hac?[kx]ed.by
"""

    def isPositive(self):
        return False

class ClearMatchesCommand(WatchRequired):
    def __init__(self):
        super(ClearMatchesCommand, self).__init__('clear_matches', 'Clear all matches for a URL')

    def process(self, user, prot, w, args, session):
        w.patterns=[]
        prot.send_plain(user.jid, "Cleared all matches for %s" % w.url)

class DisableCommand(WatchRequired):
    def __init__(self):
        super(DisableCommand, self).__init__('disable', 'Disable checks for a URL')

    def process(self, user, prot, w, args, session):
        w.active=False
        prot.send_plain(user.jid, "Disabled checks for %s" % w.url)

class EnableCommand(WatchRequired):
    def __init__(self):
        super(EnableCommand, self).__init__('enable', 'Enable checks for a URL')

    def process(self, user, prot, w, args, session):
        w.active=True
        prot.send_plain(user.jid, "Enabled checks for %s" % w.url)

class OnCommand(BaseCommand):
    def __init__(self):
        super(OnCommand, self).__init__('on', 'Enable monitoring.')

    def __call__(self, user, prot, args, session):
        user.active=True
        prot.send_plain(user.jid, "Enabled monitoring.")

class OffCommand(BaseCommand):
    def __init__(self):
        super(OffCommand, self).__init__('off', 'Disable monitoring.')

    def __call__(self, user, prot, args, session):
        user.active=False
        prot.send_plain(user.jid, "Disabled monitoring.")

class QuietCommand(ArgRequired):
    def __init__(self):
        super(QuietCommand, self).__init__('quiet', 'Temporarily quiet alerts.')
        self.extended_help="""Quiet alerts for a period of time.

Available time units:  m, h, d

You can either quiet an individual URL like this:

  quiet 5m http://broken.example.com/

or from everything:

  quiet 1h
"""

    def process(self, user, prot, args, session):
        if not args:
            prot.send_plain(user.jid, "How long would you like me to be quiet?")
            return
        m = {'m': 1, 'h': 60, 'd': 1440}
        parts=args.split(' ', 1)
        time=parts[0]
        url=None
        if len(parts) > 1: url=parts[1]
        match = re.compile(r'(\d+)([hmd])').match(time)
        if match:
            t = int(match.groups()[0]) * m[match.groups()[1]]
            u=datetime.datetime.now() + datetime.timedelta(minutes=t)

            if url:
                try:
                    w=session.query(models.Watch).filter_by(
                        url=url).filter_by(user_id=user.id).one()
                    w.quiet_until=u
                    prot.send_plain(user.jid, "%s will be quiet until %s"
                        % (w.url, str(u)))
                except exc.NoResultFound:
                    prot.send_plain(user.jid, "Cannot find watch for %s" % url)
            else:
                user.quiet_until=u
                prot.send_plain(user.jid,
                    "You won't hear from me again until %s" % str(u))
        else:
            prot.send_plain(user.jid, "I don't understand how long you want "
                "me to be quiet.  Try 5m")

# Automatically register commands.
for __t in (t for t in globals().values() if isinstance(type, type(t))):
    if BaseCommand in __t.__mro__:
        try:
            i = __t()
            all_commands[i.name] = i
        except TypeError:
            # Ignore abstract bases
            pass
