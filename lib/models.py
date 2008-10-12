import datetime

from sqlalchemy import *
from sqlalchemy.orm import sessionmaker, mapper, relation, backref, exc

_engine = create_engine('sqlite:///whatsup.sqlite3')

_metadata = MetaData()

Session = sessionmaker()
Session.configure(bind=_engine)

class User(object):

    @staticmethod
    def by_jid(jid, session=None):
        if not session:
            session=Session()
        return session.query(User).filter_by(jid=jid).one()

    @staticmethod
    def update_status(jid, status):
        """Find or create a user by jid and set the user's status"""
        session = Session()
        u = None
        try:
            u=User.by_jid(jid, session)
        except exc.NoResultFound, e:
            u=User()
            u.jid=jid

        u.status=status
        session.add(u)
        session.commit()
        return u

class Watch(object):
    def is_quiet(self):
        """Is this thing quiet?"""
        rv=False
        if self.quiet_until:
            rv = self.quiet_until > datetime.datetime.now()
        return rv

class Pattern(object):
    pass

_users_table = Table('users', _metadata,
    Column('id', Integer, primary_key=True),
    Column('jid', String(128)),
    Column('active', Boolean, default=True),
    Column('status', String(50)),
    Column('quiet_until', DateTime))

_watches_table = Table('watches', _metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('url', String(1024)),
    Column('status', Integer),
    Column('active', Boolean),
    Column('quiet_until', DateTime),
    Column('last_update', DateTime)
)

_patterns_table = Table('patterns', _metadata,
    Column('id', Integer, primary_key=True),
    Column('watch_id', Integer, ForeignKey('watches.id')),
    Column('positive', Boolean),
    Column('regex', String(1024))
)

mapper(User, _users_table, properties={
    'watches': relation(Watch)
    })
mapper(Watch, _watches_table, properties={
    'user': relation(User),
    'patterns': relation(Pattern)
    })
mapper(Pattern, _patterns_table, properties={
    'watch': relation(Watch)
    })
