#!/usr/bin/env python

from twisted.internet import task
from twisted.words.xish import domish
from twisted.words.protocols.jabber.jid import JID
from wokkel.xmppim import MessageProtocol, PresenceClientProtocol
from wokkel.xmppim import AvailablePresence
from wokkel.client import XMPPHandler

import xmpp_commands
import config
import models

class WhatsupProtocol(MessageProtocol, PresenceClientProtocol):

    def __init__(self):
        super(WhatsupProtocol, self).__init__()
        self._watching=-1
        self._users=-1

    def connectionInitialized(self):
        MessageProtocol.connectionInitialized(self)
        PresenceClientProtocol.connectionInitialized(self)

    def connectionMade(self):
        print "Connected!"

        self.commands=xmpp_commands.all_commands
        print "Loaded commands: ", `self.commands.keys()`

        # send initial presence
        self._watching=-1
        self._users=-1
        self.update_presence()

    @models.wants_session
    def update_presence(self, session):
        watching=session.query(models.Watch).count()
        users=session.query(models.User).count()
        if watching != self._watching or users != self._users:
            status="Watching %s URLs for %s users" % (watching, users)
            self.available(None, None, {None: status})
            self._watching = watching
            self._users = users

    def connectionLost(self, reason):
        print "Disconnected!"

    def typing_notification(self, jid):
        """Send a typing notification to the given jid."""

        msg = domish.Element((None, "message"))
        msg["to"] = jid
        msg["from"] = config.SCREEN_NAME
        msg.addElement(('jabber:x:event', 'x')).addElement("composing")

        self.send(msg)

    def send_plain(self, jid, content):
        msg = domish.Element((None, "message"))
        msg["to"] = jid
        msg["from"] = config.SCREEN_NAME
        msg["type"] = 'chat'
        msg.addElement("body", content=content)

        self.send(msg)

    def get_user(self, msg, session):
        jid=JID(msg['from'])
        try:
            rv=models.User.by_jid(jid.userhost(), session)
        except:
            print "Getting user without the jid in the DB (%s)" % jid.full()
            rv=models.User.update_status(jid.userhost(), None, session)
            self.subscribe(jid)
        return rv;

    @models.wants_session
    def _handleCommand(self, msg, cmd, args, session):
        self.commands[cmd.lower()](self.get_user(msg, session),
            self, args, session)
        session.commit()

    def onMessage(self, msg):
        if msg["type"] == 'chat' and hasattr(msg, "body") and msg.body:
            self.typing_notification(msg['from'])
            a=unicode(msg.body).split(' ', 1)
            args = a[1] if len(a) > 1 else None
            if self.commands.has_key(a[0].lower()):
                self._handleCommand(msg, a[0], args)
            else:
                self.send_plain(msg['from'], 'No such command: ' + a[0])
            self.update_presence()

    # presence stuff
    def availableReceived(self, entity, show=None, statuses=None, priority=0):
        print "Available from %s (%s, %s)" % (entity.full(), show, statuses)
        models.User.update_status(entity.userhost(), show)

    def unavailableReceived(self, entity, statuses=None):
        print "Unavailable from %s" % entity.userhost()
        models.User.update_status(entity.userhost(), 'unavailable')

    @models.wants_session
    def subscribedReceived(self, entity, session):
        print "Subscribe received from %s" % (entity.userhost())
        welcome_message="""Welcome to whatsup.

I'll look at web pages so you don't have to.  The most basic thing you can do to add a monitor is the following:

  watch http://www.mywebsite.com/

But I can do more.  Type "help" for more info.
"""
        self.send_plain(entity.full(), welcome_message)
        msg = "New subscriber: %s ( %d )" % (entity.userhost(),
            session.query(models.User).count())
        for a in config.ADMINS:
            self.send_plain(a, msg)

    def unsubscribedReceived(self, entity):
        print "Unsubscribed received from %s" % (entity.userhost())
        models.User.update_status(entity.userhost(), 'unsubscribed')
        self.unsubscribe(entity)
        self.unsubscribed(entity)

    def subscribeReceived(self, entity):
        print "Subscribe received from %s" % (entity.userhost())
        self.subscribe(entity)
        self.subscribed(entity)
        self.update_presence()

    def unsubscribeReceived(self, entity):
        print "Unsubscribe received from %s" % (entity.userhost())
        models.User.update_status(entity.userhost(), 'unsubscribed')
        self.unsubscribe(entity)
        self.unsubscribed(entity)
        self.update_presence()

# From https://mailman.ik.nu/pipermail/twisted-jabber/2008-October/000171.html
class KeepAlive(XMPPHandler):

    interval = 300
    lc = None

    def connectionInitialized(self):
        self.lc = task.LoopingCall(self.ping)
        self.lc.start(self.interval)

    def connectionLost(self, *args):
        if self.lc:
            self.lc.stop()

    def ping(self):
        print "Stayin' alive"
        self.send(" ")
