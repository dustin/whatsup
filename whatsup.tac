import sys
sys.path.append("lib")

from twisted.application import service
from twisted.internet import task, reactor
from twisted.words.protocols.jabber import jid
from wokkel.client import XMPPClient
from wokkel.generic import VersionHandler

from whatsup import config
from whatsup import protocol
from whatsup import scheduling

application = service.Application("whatsup")

xmppclient = XMPPClient(jid.internJID(config.SCREEN_NAME),
    config.CONF.get('xmpp', 'pass'))
xmppclient.logTraffic = False
whatsup=protocol.WhatsupProtocol()
whatsup.setHandlerParent(xmppclient)
VersionHandler('Whatsup', config.VERSION).setHandlerParent(xmppclient)
protocol.KeepAlive().setHandlerParent(xmppclient)
xmppclient.setServiceParent(application)

site_checker = scheduling.CheckSites(whatsup)
# Run this once in a few seconds...
reactor.callLater(5, site_checker)

# And do it periodically
site_checker_loop = task.LoopingCall(site_checker)
site_checker_loop.start(int(config.CONF.get('general', 'loop_sleep')), False)
