import models

import datetime
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

    def __updateDb(self, watch, status, session):
        watch.status=status
        watch.last_update = datetime.datetime.now()
        session.commit()

    def onSuccess(self, watch_id, page):
        print "Success fetching %d: %d bytes" % (watch_id, len(page))
        session = models.Session()
        watch=session.query(models.Watch).filter_by(id=watch_id).one()
        if 200 != watch.status:
            self.client.send_plain(watch.user.jid,
                ":) Status of %s changed from %s to %d"
                % (watch.url, `watch.status`, 200))
        self.__updateDb(watch, 200, session)

    def onError(self, watch_id, error):
        print "Error fetching %d: %s" % (watch_id, error)
        session = models.Session()
        watch=session.query(models.Watch).filter_by(id=watch_id).one()
        try:
            status=int(error.getErrorMessage()[0:3])
        except:
            status=-1
        self.client.send_plain(watch.user.jid, ":( Error in %s: %d - %s"
            % (watch.url, status, error.getErrorMessage()))
        self.__updateDb(watch, status, session)
