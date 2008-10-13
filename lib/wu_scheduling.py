import models

from twisted.web import client

class CheckSites(object):

    def __init__(self, client):
        self.client = client

    def __call__(self):
        session = models.Session()
        todo = models.Watch.todo(session)
        for watch in todo:
            client.getPage(str(watch.url), timeout=10).addCallbacks(
                callback=self.__mkCallback(watch.id, self.onSuccess),
                errback=self.__mkCallback(watch.id, self.onError))
        session.close()

    def __mkCallback(self, id, f):
        return lambda v: f(id, v)

    def onSuccess(self, watch_id, page):
        print "Success fetching %d: %d bytes" % (watch_id, len(page))

    def onError(self, watch_id, error):
        print "Error fetching %d: %s" % (watch_id, error)
