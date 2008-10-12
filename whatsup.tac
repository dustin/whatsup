import sys
sys.path.append("lib")

from twisted.application import service
from twisted.words.protocols.jabber import jid
from wokkel.client import XMPPClient

import wu_protocol
import wu_config

application = service.Application("whatsup")

xmppclient = XMPPClient(jid.internJID(wu_config.SCREEN_NAME),
    wu_config.CONF['xmpp']['pass'])
xmppclient.logTraffic = False
wu_protocol.WhatsupProtocol().setHandlerParent(xmppclient)
xmppclient.setServiceParent(application)
