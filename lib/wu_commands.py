import time

from twisted.words.xish import domish
from twisted.web import client

all_commands={}

def __register(cls):
    c=cls()
    all_commands[c.name]=c

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

    def __init__(self, name, help=None, extended_help=None):
        self.name=name
        self.help=help
        self.__extended_help=extended_help

    def extended_help(self):
        if self.__extended_help:
            return self.__extended_help
        else:
            return self.help

    def __call__(self, user, prot, args):
        raise NotImplementedError()

class StatusCommand(BaseCommand):

    def __init__(self):
        super(StatusCommand, self).__init__('status', 'Check your status.')

    def __call__(self, user, prot, args):
        rv=[]
        rv.append("Jid:  %s" % user.jid)
        rv.append("Jabber status:  %s" % user.status)
        rv.append("Whatsup status:  %s"
            % {True: 'Active', False: 'Inactive'}[user.active])
        rv.append("You are currently watching %d URLs." % len(user.watches))
        prot.send_plain(user.jid, "\n".join(rv))

__register(StatusCommand)

class GetCommand(BaseCommand):

    def __init__(self):
        super(GetCommand, self).__init__('get', 'Get a web page.')

    def __call__(self, user, prot, args):
        if args:
            start=time.time()
            cf = CountingFile()
            def onSuccess(value):
                prot.send_plain(user.jid, "Got %d bytes in %.2fs" %
                    (cf.written, (time.time() - start)))
            client.downloadPage(args, cf).addCallbacks(
                callback=onSuccess,
                errback=lambda error:(prot.send_plain(user.jid, "Error getting the page: %s" % `error`)))
        else:
            prot.send_plain(user.jid, "I need a URL to fetch.")

__register(GetCommand)

class HelpCommand(BaseCommand):

    def __init__(self):
        super(HelpCommand, self).__init__('help', 'You need help.')

    def __call__(self, user, prot, args):
        rv=[]
        if args:
            c=all_commands.get(args.strip().lower(), None)
            if c:
                rv.append("Help for %s:\n" % c.name)
                rv.append(c.extended_help())
            else:
                rv.append("Unknown command %s." % args)
        else:
            for k in sorted(all_commands.keys()):
                rv.append('%s\t%s' % (k, all_commands[k].help))
        prot.send_plain(user.jid, "\n".join(rv))

__register(HelpCommand)