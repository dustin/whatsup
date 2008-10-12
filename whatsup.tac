import sys
sys.path.append("lib")

import yaml

from twisted.application import service
from twisted.words.protocols.jabber import jid
from wokkel.client import XMPPClient

from whatsup import EchoBotProtocol

application = service.Application("whatsup")

# Load the config
conf=yaml.load(open('whatsup.yml'))

xmppclient = XMPPClient(jid.internJID(conf['xmpp']['jid']), conf['xmpp']['pass'])
xmppclient.logTraffic = False
whatsup = EchoBotProtocol()
whatsup.setHandlerParent(xmppclient)
xmppclient.setServiceParent(application)
