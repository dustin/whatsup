#!/usr/bin/env python

from twisted.words.xish import domish
from twisted.words.protocols.jabber.jid import JID
from wokkel.xmppim import MessageProtocol, AvailablePresence

import wu_commands
import wu_config
import models

class WhatsupProtocol(MessageProtocol):
    def connectionMade(self):
        print "Connected!"

        self.commands=dict([(x.name, x) for x in wu_commands.all_commands])
        print "Loaded commands: ", `self.commands.keys()`

        # send initial presence
        self.send(AvailablePresence())

    def connectionLost(self, reason):
        print "Disconnected!"


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
        print "Incoming message:  %s" % msg.toXml()

        if msg["type"] == 'chat' and hasattr(msg, "body") and msg.body:
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