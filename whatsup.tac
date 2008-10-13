import sys
sys.path.append("lib")

from twisted.application import service
from twisted.internet import task, reactor
from twisted.words.protocols.jabber import jid
from wokkel.client import XMPPClient
from wokkel.generic import VersionHandler

import wu_config
import wu_protocol
import wu_scheduling


application = service.Application("whatsup")

xmppclient = XMPPClient(jid.internJID(wu_config.SCREEN_NAME),
    wu_config.CONF.get('xmpp', 'pass'))
xmppclient.logTraffic = False
whatsup=wu_protocol.WhatsupProtocol()
whatsup.setHandlerParent(xmppclient)
VersionHandler('Whatsup', wu_config.VERSION).setHandlerParent(xmppclient)
xmppclient.setServiceParent(application)

site_checker = wu_scheduling.CheckSites(whatsup)
# Run this once in a few seconds...
reactor.callLater(5, site_checker)

# And do it periodically
site_checker_loop = task.LoopingCall(site_checker)
site_checker_loop.start(int(wu_config.CONF.get('general', 'loop_sleep')))
