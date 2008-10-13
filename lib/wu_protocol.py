#!/usr/bin/env python

from twisted.words.xish import domish
from twisted.words.protocols.jabber.jid import JID
from wokkel.xmppim import MessageProtocol, PresenceClientProtocol
from wokkel.xmppim import AvailablePresence

import wu_commands
import wu_config
import models

class WhatsupProtocol(MessageProtocol, PresenceClientProtocol):

    def connectionInitialized(self):
        MessageProtocol.connectionInitialized(self)
        PresenceClientProtocol.connectionInitialized(self)

    def connectionMade(self):
        print "Connected!"

        self.commands=wu_commands.all_commands
        print "Loaded commands: ", `self.commands.keys()`

        # send initial presence
        self.send(AvailablePresence())

    def connectionLost(self, reason):
        print "Disconnected!"

    def typing_notification(self, jid):
        """Send a typing notification to the given jid."""

        msg = domish.Element((None, "message"))
        msg["to"] = jid
        msg["from"] = wu_config.SCREEN_NAME
        msg.addElement(('jabber:x:event', 'x')).addElement("composing")

        self.send(msg)

    def send_plain(self, jid, content):
        msg = domish.Element((None, "message"))
        msg["to"] = jid
        msg["from"] = wu_config.SCREEN_NAME
        msg["type"] = 'chat'
        msg.addElement("body", content=content)

        self.send(msg)

    def get_user(self, msg, session):
        jid=JID(msg['from'])
        return models.User.by_jid(jid.userhost(), session)

    def onMessage(self, msg):
        if msg["type"] == 'chat' and hasattr(msg, "body") and msg.body:
            self.typing_notification(msg['from'])
            a=str(msg.body).split(' ', 1)
            args = None
            if len(a) > 1:
                args=a[1]
            if self.commands.has_key(a[0].lower()):
                session=models.Session()
                self.commands[a[0].lower()](self.get_user(msg, session), self, args)
                session.commit()
            else:
                self.send_plain(msg['from'], 'No such command: ' + a[0])

    # presence stuff
    def availableReceived(self, entity, show=None, statuses=None, priority=0):
        print "Available from %s (%s, %s)" % (entity.full(), show, statuses)
        models.User.update_status(entity.userhost(), show)

    def unavailableReceived(self, entity, statuses=None):
        print "Unavailable from %s" % entity.userhost()
        models.User.update_status(entity.userhost(), 'unavailable')

    def subscribedReceived(self, entity):
        print "Subscribe received from %s" % (entity.userhost())

    def unsubscribedReceived(self, entity):
        print "Unsubscribed received from %s" % (entity.userhost())
        models.User.update_status(entity.userhost(), 'unsubscribed')
        self.unsubscribe(entity)
        self.unsubscribed(entity)

    def subscribeReceived(self, entity):
        print "Subscribe received from %s" % (entity.userhost())
        self.subscribe(entity)
        self.subscribed(entity)

    def unsubscribeReceived(self, entity):
        print "Unsubscribe received from %s" % (entity.userhost())
        models.User.update_status(entity.userhost(), 'unsubscribed')
        self.unsubscribe(entity)
        self.unsubscribed(entity)