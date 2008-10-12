# Copyright (c) 2003-2008 Ralph Meijer
# See LICENSE for details.

"""
Tests for L{wokkel.component}
"""

from zope.interface.verify import verifyObject

from twisted.internet import defer
from twisted.python import failure
from twisted.trial import unittest
from twisted.words.protocols.jabber import ijabber, xmlstream
from twisted.words.protocols.jabber.jid import JID
from twisted.words.xish import domish

from wokkel import component
from wokkel.generic import XmlPipe

class InternalComponentTest(unittest.TestCase):
    """
    Tests for L{component.InternalComponent}.
    """

    def setUp(self):
        self.router = component.RouterService()
        self.component = component.InternalComponent(self.router, 'component')


    def test_interface(self):
        """
        L{component.InternalComponent} implements
        L{ijabber.IXMPPHandlerCollection}.
        """
        verifyObject(ijabber.IXMPPHandlerCollection, self.component)


    def test_startService(self):
        """
        Starting the service creates a new route and hooks up handlers.
        """

        events = []

        class TestHandler(xmlstream.XMPPHandler):

            def connectionInitialized(self):
                fn = lambda obj: events.append(obj)
                self.xmlstream.addObserver('//event/test', fn)

        TestHandler().setHandlerParent(self.component)

        self.assertFalse(self.component.running)

        self.component.startService()

        self.assertTrue(self.component.running)
        self.assertIn('component', self.router.routes)

        self.assertEquals([], events)
        self.component.xmlstream.dispatch(None, '//event/test')
        self.assertEquals([None], events)


    def test_stopService(self):
        """
        Stopping the service removes the route and disconnects handlers.
        """

        events = []

        class TestHandler(xmlstream.XMPPHandler):

            def connectionLost(self, reason):
                events.append(reason)

        TestHandler().setHandlerParent(self.component)

        self.component.startService()
        self.component.stopService()

        self.assertFalse(self.component.running)
        self.assertEquals(1, len(events))
        self.assertNotIn('component', self.router.routes)


    def test_addHandler(self):
        """
        Adding a handler connects it to the stream.
        """
        events = []

        class TestHandler(xmlstream.XMPPHandler):

            def connectionInitialized(self):
                fn = lambda obj: events.append(obj)
                self.xmlstream.addObserver('//event/test', fn)

        self.component.startService()
        self.component.xmlstream.dispatch(None, '//event/test')
        self.assertEquals([], events)

        TestHandler().setHandlerParent(self.component)
        self.component.xmlstream.dispatch(None, '//event/test')
        self.assertEquals([None], events)


    def test_send(self):
        """
        A message sent from the component ends up at the router.
        """
        events = []
        fn = lambda obj: events.append(obj)
        message = domish.Element((None, 'message'))

        self.component.startService()
        self.router.routes['component'].addObserver('/message', fn)
        self.component.send(message)

        self.assertEquals([message], events)



class RouterServiceTest(unittest.TestCase):
    """
    Tests for L{component.RouterService}.
    """

    def test_addRoute(self):
        """
        Test route registration and routing on incoming stanzas.
        """
        router = component.RouterService()
        routed = []
        router.route = lambda element: routed.append(element)

        pipe = XmlPipe()
        router.addRoute('example.org', pipe.sink)
        self.assertEquals(1, len(router.routes))
        self.assertEquals(pipe.sink, router.routes['example.org'])

        element = domish.Element(('testns', 'test'))
        pipe.source.send(element)
        self.assertEquals([element], routed)


    def test_route(self):
        """
        Test routing of a message.
        """
        component1 = XmlPipe()
        component2 = XmlPipe()
        router = component.RouterService()
        router.addRoute('component1.example.org', component1.sink)
        router.addRoute('component2.example.org', component2.sink)

        outgoing = []
        component2.source.addObserver('/*',
                                      lambda element: outgoing.append(element))
        stanza = domish.Element((None, 'route'))
        stanza['from'] = 'component1.example.org'
        stanza['to'] = 'component2.example.org'
        stanza.addElement('presence')
        component1.source.send(stanza)
        self.assertEquals([stanza], outgoing)


    def test_routeDefault(self):
        """
        Test routing of a message using the default route.

        The default route is the one with C{None} as its key in the
        routing table. It is taken when there is no more specific route
        in the routing table that matches the stanza's destination.
        """
        component1 = XmlPipe()
        s2s = XmlPipe()
        router = component.RouterService()
        router.addRoute('component1.example.org', component1.sink)
        router.addRoute(None, s2s.sink)

        outgoing = []
        s2s.source.addObserver('/*', lambda element: outgoing.append(element))
        stanza = domish.Element((None, 'route'))
        stanza['from'] = 'component1.example.org'
        stanza['to'] = 'example.com'
        stanza.addElement('presence')
        component1.source.send(stanza)
        self.assertEquals([stanza], outgoing)



class ListenComponentAuthenticatorTest(unittest.TestCase):
    """
    Tests for L{component.ListenComponentAuthenticator}.
    """

    def setUp(self):
        self.output = []
        authenticator = component.ListenComponentAuthenticator('secret')
        self.xmlstream = xmlstream.XmlStream(authenticator)
        self.xmlstream.send = self.output.append


    def loseConnection(self):
        """
        Stub loseConnection because we are a transport.
        """
        self.xmlstream.connectionLost("no reason")


    def test_streamStarted(self):
        observers = []

        def addOnetimeObserver(event, observerfn):
            observers.append((event, observerfn))

        xs = self.xmlstream
        xs.addOnetimeObserver = addOnetimeObserver

        xs.makeConnection(self)
        self.assertIdentical(None, xs.sid)
        self.assertFalse(xs._headerSent)

        xs.dataReceived("<stream:stream xmlns='jabber:component:accept' "
                         "xmlns:stream='http://etherx.jabber.org/streams' "
                         "to='component.example.org'>")
        self.assertEqual((0, 0), xs.version)
        self.assertNotIdentical(None, xs.sid)
        self.assertTrue(xs._headerSent)
        self.assertEquals(('/*', xs.authenticator.onElement), observers[-1])


    def test_streamStartedWrongNamespace(self):
        """
        The received stream header should have a correct namespace.
        """
        streamErrors = []

        xs = self.xmlstream
        xs.sendStreamError = streamErrors.append
        xs.makeConnection(self)
        xs.dataReceived("<stream:stream xmlns='jabber:client' "
                         "xmlns:stream='http://etherx.jabber.org/streams' "
                         "to='component.example.org'>")
        self.assertEquals(1, len(streamErrors))
        self.assertEquals('invalid-namespace', streamErrors[-1].condition)


    def test_streamStartedNoTo(self):
        streamErrors = []

        xs = self.xmlstream
        xs.sendStreamError = streamErrors.append
        xs.makeConnection(self)
        xs.dataReceived("<stream:stream xmlns='jabber:component:accept' "
                         "xmlns:stream='http://etherx.jabber.org/streams'>")
        self.assertEquals(1, len(streamErrors))
        self.assertEquals('improper-addressing', streamErrors[-1].condition)


    def test_onElement(self):
        """
        We expect a handshake element with a hash.
        """
        handshakes = []

        xs = self.xmlstream
        xs.authenticator.onHandshake = handshakes.append

        handshake = domish.Element(('jabber:component:accept', 'handshake'))
        handshake.addContent('1234')
        xs.authenticator.onElement(handshake)
        self.assertEqual('1234', handshakes[-1])

    def test_onHandshake(self):
        xs = self.xmlstream
        xs.sid = '1234'
        theHash = '32532c0f7dbf1253c095b18b18e36d38d94c1256'
        xs.authenticator.onHandshake(theHash)
        self.assertEqual('<handshake/>', self.output[-1])


    def test_onHandshakeWrongHash(self):
        streamErrors = []
        authd = []

        def authenticated(self, xs):
            authd.append(xs)

        xs = self.xmlstream
        xs.addOnetimeObserver(xmlstream.STREAM_AUTHD_EVENT, authenticated)
        xs.sendStreamError = streamErrors.append

        xs.sid = '1234'
        theHash = '1234'
        xs.authenticator.onHandshake(theHash)
        self.assertEquals('not-authorized', streamErrors[-1].condition)
        self.assertEquals(0, len(authd))



class ComponentServerTest(unittest.TestCase):
    """
    Tests for L{component.ComponentServer}.
    """

    def setUp(self):
        self.router = component.RouterService()
        self.server = component.ComponentServer(self.router)
        self.xmlstream = self.server.factory.buildProtocol(None)
        self.xmlstream.thisEntity = JID('component.example.org')


    def test_makeConnection(self):
        """
        A new connection increases the stream serial count. No logs by default.
        """
        self.xmlstream.dispatch(self.xmlstream,
                                xmlstream.STREAM_CONNECTED_EVENT)
        self.assertEqual(0, self.xmlstream.serial)
        self.assertEqual(1, self.server.serial)
        self.assertIdentical(None, self.xmlstream.rawDataInFn)
        self.assertIdentical(None, self.xmlstream.rawDataOutFn)


    def test_makeConnectionLogTraffic(self):
        """
        Setting logTraffic should set up raw data loggers.
        """
        self.server.logTraffic = True
        self.xmlstream.dispatch(self.xmlstream,
                                xmlstream.STREAM_CONNECTED_EVENT)
        self.assertNotIdentical(None, self.xmlstream.rawDataInFn)
        self.assertNotIdentical(None, self.xmlstream.rawDataOutFn)


    def test_onError(self):
        """
        An observer for stream errors should trigger onError to log it.
        """
        self.xmlstream.dispatch(self.xmlstream,
                                xmlstream.STREAM_CONNECTED_EVENT)

        class TestError(Exception):
            pass

        reason = failure.Failure(TestError())
        self.xmlstream.dispatch(reason, xmlstream.STREAM_ERROR_EVENT)
        self.assertEqual(1, len(self.flushLoggedErrors(TestError)))


    def test_connectionInitialized(self):
        """
        Make sure a new stream is added to the routing table.
        """
        self.xmlstream.dispatch(self.xmlstream, xmlstream.STREAM_AUTHD_EVENT)
        self.assertIn('component.example.org', self.router.routes)
        self.assertIdentical(self.xmlstream,
                             self.router.routes['component.example.org'])


    def test_connectionLost(self):
        """
        Make sure a stream is removed from the routing table on disconnect.
        """
        self.xmlstream.dispatch(self.xmlstream, xmlstream.STREAM_AUTHD_EVENT)
        self.xmlstream.dispatch(None, xmlstream.STREAM_END_EVENT)
        self.assertNotIn('component.example.org', self.router.routes)
