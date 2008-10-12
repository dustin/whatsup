# -*- test-case-name: wokkel.test.test_component -*-
#
# Copyright (c) 2003-2008 Ralph Meijer
# See LICENSE for details.

"""
XMPP External Component utilities
"""

from twisted.application import service
from twisted.internet import reactor
from twisted.python import log
from twisted.words.protocols.jabber.jid import internJID as JID
from twisted.words.protocols.jabber import component, error, xmlstream
from twisted.words.xish import domish

from wokkel.generic import XmlPipe
from wokkel.subprotocols import StreamManager

NS_COMPONENT_ACCEPT = 'jabber:component:accept'

class Component(StreamManager, service.Service):
    def __init__(self, host, port, jid, password):
        self.host = host
        self.port = port

        factory = component.componentFactory(jid, password)

        StreamManager.__init__(self, factory)

    def _authd(self, xs):
        old_send = xs.send

        def send(obj):
            if domish.IElement.providedBy(obj) and \
                    not obj.getAttribute('from'):
                obj['from'] = self.xmlstream.thisEntity.full()
            old_send(obj)

        xs.send = send
        StreamManager._authd(self, xs)

    def initializationFailed(self, reason):
        """
        Called when stream initialization has failed.

        Stop the service (thereby disconnecting the current stream) and
        raise the exception.
        """
        self.stopService()
        reason.raiseException()

    def startService(self):
        service.Service.startService(self)

        self.factory.stopTrying()
        self._connection = self._getConnection()

    def stopService(self):
        service.Service.stopService(self)

        self._connection.disconnect()

    def _getConnection(self):
        return reactor.connectTCP(self.host, self.port, self.factory)



class InternalComponent(xmlstream.XMPPHandlerCollection, service.Service):
    """
    Component service that connects directly to a router.

    Instead of opening a socket to connect to a router, like L{Component},
    components of this type connect to a router in the same process. This
    allows for one-process XMPP servers.
    """

    def __init__(self, router, domain):
        xmlstream.XMPPHandlerCollection.__init__(self)
        self.router = router
        self.domain = domain

        self.xmlstream = None

    def startService(self):
        """
        Create a XML pipe, connect to the router and setup handlers.
        """
        service.Service.startService(self)

        self.pipe = XmlPipe()
        self.xmlstream = self.pipe.source
        self.router.addRoute(self.domain, self.pipe.sink)

        for e in self:
            e.makeConnection(self.xmlstream)
            e.connectionInitialized()


    def stopService(self):
        """
        Disconnect from the router and handlers.
        """
        service.Service.stopService(self)

        self.router.removeRoute(self.domain, self.pipe.sink)
        self.pipe = None
        self.xmlstream = None

        for e in self:
            e.connectionLost(None)


    def addHandler(self, handler):
        """
        Add a new handler and connect it to the stream.
        """
        xmlstream.XMPPHandlerCollection.addHandler(self, handler)

        if self.xmlstream:
            handler.makeConnection(self.xmlstream)
            handler.connectionInitialized()


    def send(self, obj):
        """
        Send data to the XML stream, so it ends up at the router.
        """
        self.xmlstream.send(obj)



class ListenComponentAuthenticator(xmlstream.ListenAuthenticator):
    """
    Authenticator for accepting components.
    """
    namespace = NS_COMPONENT_ACCEPT

    def __init__(self, secret):
        self.secret = secret
        xmlstream.ListenAuthenticator.__init__(self)


    def associateWithStream(self, xs):
        xs.version = (0, 0)
        xmlstream.ListenAuthenticator.associateWithStream(self, xs)


    def streamStarted(self, rootElement):
        xmlstream.ListenAuthenticator.streamStarted(self, rootElement)

        if rootElement.defaultUri != self.namespace:
            exc = error.StreamError('invalid-namespace')
            self.xmlstream.sendStreamError(exc)
            return

        # self.xmlstream.thisEntity is set to the address the component
        # wants to assume. This should probably be checked.
        if not self.xmlstream.thisEntity:
            exc = error.StreamError('improper-addressing')
            self.xmlstream.sendStreamError(exc)
            return

        self.xmlstream.sid = 'random' # FIXME

        self.xmlstream.sendHeader()
        self.xmlstream.addOnetimeObserver('/*', self.onElement)


    def onElement(self, element):
        if (element.uri, element.name) == (self.namespace, 'handshake'):
            self.onHandshake(unicode(element))
        else:
            exc = error.streamError('not-authorized')
            self.xmlstream.sendStreamError(exc)


    def onHandshake(self, handshake):
        calculatedHash = xmlstream.hashPassword(self.xmlstream.sid, self.secret)
        if handshake != calculatedHash:
            exc = error.StreamError('not-authorized', text='Invalid hash')
            self.xmlstream.sendStreamError(exc)
        else:
            self.xmlstream.send('<handshake/>')
            self.xmlstream.dispatch(self.xmlstream,
                                    xmlstream.STREAM_AUTHD_EVENT)



class RouterService(service.Service):
    """
    XMPP Server's Router Service.

    This service connects the different components of the XMPP service and
    routes messages between them based on the given routing table.

    Connected components are trusted to have correct addressing in the
    stanzas they offer for routing.

    A route destination of C{None} adds a default route. Traffic for which no
    specific route exists, will be routed to this default route.

    @ivar routes: Routes based on the host part of JIDs. Maps host names to the
                  L{EventDispatcher<utility.EventDispatcher>}s that should
                  receive the traffic. A key of C{None} means the default
                  route.
    @type routes: C{dict}
    """

    def __init__(self):
        self.routes = {}


    def addRoute(self, destination, xs):
        """
        Add a new route.

        The passed XML Stream C{xs} will have an observer for all stanzas
        added to route its outgoing traffic. In turn, traffic for
        C{destination} will be passed to this stream.

        @param destination: Destination of the route to be added as a host name
                            or C{None} for the default route.
        @type destination: C{str} or C{NoneType}.
        @param xs: XML Stream to register the route for.
        @type xs: L{EventDispatcher<utility.EventDispatcher>}.
        """
        self.routes[destination] = xs
        xs.addObserver('/*', self.route)


    def removeRoute(self, destination, xs):
        """
        Remove a route.

        @param destination: Destination of the route that should be removed.
        @type destination: C{str}.
        @param xs: XML Stream to remove the route for.
        @type xs: L{EventDispatcher<utility.EventDispatcher>}.
        """
        xs.removeObserver('/*', self.route)
        if (xs == self.routes[destination]):
            del self.routes[destination]


    def route(self, stanza):
        """
        Route a stanza.

        @param stanza: The stanza to be routed.
        @type stanza: L{domish.Element}.
        """
        if not list(stanza.elements()):
            return

        destination = JID(stanza['to'])

        log.msg("Routing to %s: %r" % (destination.full(), stanza.toXml()))

        if destination.host in self.routes:
            self.routes[destination.host].send(stanza)
        else:
            self.routes[None].send(stanza)



class ComponentServer(service.Service):
    """
    XMPP Component Server service.

    This service accepts XMPP external component connections and makes
    the router service route traffic for a component's bound domain
    to that component.
    """

    logTraffic = False

    def __init__(self, router, port=5347, secret='secret'):
        self.router = router
        self.port = port
        self.secret = secret

        def authenticatorFactory():
            return ListenComponentAuthenticator(self.secret)

        self.factory = xmlstream.XmlStreamServerFactory(authenticatorFactory)
        self.factory.addBootstrap(xmlstream.STREAM_CONNECTED_EVENT,
                                  self.makeConnection)
        self.factory.addBootstrap(xmlstream.STREAM_AUTHD_EVENT,
                                  self.connectionInitialized)

        self.serial = 0


    def startService(self):
        service.Service.startService(self)
        reactor.listenTCP(self.port, self.factory)


    def makeConnection(self, xs):
        """
        Called when a component connection was made.

        This enables traffic debugging on incoming streams.
        """
        xs.serial = self.serial
        self.serial += 1

        def logDataIn(buf):
            log.msg("RECV (%d): %r" % (xs.serial, buf))

        def logDataOut(buf):
            log.msg("SEND (%d): %r" % (xs.serial, buf))

        if self.logTraffic:
            xs.rawDataInFn = logDataIn
            xs.rawDataOutFn = logDataOut

        xs.addObserver(xmlstream.STREAM_ERROR_EVENT, self.onError)


    def connectionInitialized(self, xs):
        """
        Called when a component has succesfully authenticated.

        Add the component to the routing table and establish a handler
        for a closed connection.
        """
        destination = xs.thisEntity.host

        self.router.addRoute(destination, xs)
        xs.addObserver(xmlstream.STREAM_END_EVENT, self.connectionLost, 0,
                                                   destination, xs)


    def onError(self, reason):
        log.err(reason, "Stream Error")


    def connectionLost(self, destination, xs, reason):
        self.router.removeRoute(destination, xs)
