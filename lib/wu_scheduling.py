import re
import models

import datetime
from twisted.web import client

class CheckSites(object):

    def __init__(self, client):
        self.client = client

    def __call__(self):
        session = models.Session()
        try:
            todo = models.Watch.todo(session)
            for watch in todo:
                client.getPage(str(watch.url), timeout=10).addCallbacks(
                    callback=self.__mkCallback(watch.id, self.onSuccess),
                    errback=self.__mkCallback(watch.id, self.onError))
        finally:
            session.close()

    def __mkCallback(self, id, f):
        return lambda v: f(id, v)

    def __updateDb(self, watch, status, session):
        watch.status=status
        watch.last_update = datetime.datetime.now()
        session.commit()

    def _check_patterns(self, body, watch):
        rv=200
        failed_pattern=None
        for p in watch.patterns:
            r=re.compile(p.regex)
            if r.search(body):
                if not p.positive:
                    rv = -1
                    failed_pattern=p.regex
            else:
                if p.positive:
                    rv = -1
                    failed_pattern=p.regex
        return rv, failed_pattern

    def onSuccess(self, watch_id, page):
        print "Success fetching %d: %d bytes" % (watch_id, len(page))
        session = models.Session()
        try:
            watch=session.query(models.Watch).filter_by(id=watch_id).one()
            status, pattern = self._check_patterns(page, watch)
            print "Pattern status of %s: %d" % (watch.url, status)
            if status == 200:
                if status != watch.status:
                    self.client.send_plain(watch.user.jid,
                        ":) Status of %s changed from %s to %d"
                        % (watch.url, `watch.status`, status))
            else:
                self._reportError(watch, status, "Pattern failed: %s" % pattern)
            self.__updateDb(watch, status, session)
        finally:
            session.close()

    def _reportError(self, watch, status, err_msg):
        self.client.send_plain(watch.user.jid, ":( Error in %s: %d - %s"
            % (watch.url, status, err_msg))

    def onError(self, watch_id, error):
        print "Error fetching %d: %s" % (watch_id, error)
        session = models.Session()
        try:
            watch=session.query(models.Watch).filter_by(id=watch_id).one()
            try:
                status=int(error.getErrorMessage()[0:3])
            except:
                status=-1
            self._reportError(watch, status, error.getErrorMessage())
            self.__updateDb(watch, status, session)
        finally:
            session.close()
