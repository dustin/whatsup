#!/usr/bin/env python

from twisted.words.xish import domish
from wokkel.xmppim import MessageProtocol, AvailablePresence

class WhatsupProtocol(MessageProtocol):
    def connectionMade(self):
        print "Connected!"

        # send initial presence
        self.send(AvailablePresence())

    def connectionLost(self, reason):
        print "Disconnected!"

    def onMessage(self, msg):
        print "Incoming message:  %s" % msg.toXml()

        if msg["type"] == 'chat' and hasattr(msg, "body") and msg.body:
            reply = domish.Element((None, "message"))
            reply["to"] = msg["from"]
            reply["from"] = msg["to"]
            reply["type"] = 'chat'
            reply.addElement("body", content="echo: " + str(msg.body))

            self.send(reply)