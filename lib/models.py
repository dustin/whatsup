import datetime

from sqlalchemy import *
from sqlalchemy.orm import sessionmaker, mapper, relation, backref, exc

import wu_config

_engine = create_engine(wu_config.CONF['general']['db'])

_metadata = MetaData()

Session = sessionmaker()
Session.configure(bind=_engine)

class Quietable(object):
    def is_quiet(self):
        """Is this user quiet?"""
        rv=False
        if self.quiet_until:
            rv = self.quiet_until > datetime.datetime.now()
        return rv

class User(Quietable):

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

class Watch(Quietable):

    @staticmethod
    def todo(session, timeout=10):
        """Get the items to do."""
        ID_QUERY="""select w.*
          from watches w join users on (users.id == w.user_id)
          where
            users.active is not null
            and users.active = :uactive
            and users.status not in ('dnd', 'offline', 'unavailable')
            and w.active = :wactive
            and ( w.last_update is null or w.last_update < :last_update)
          limit 50
          """
        then=datetime.datetime.now() - datetime.timedelta(minutes=timeout)
        return session.query(Watch).from_statement(ID_QUERY).params(
            uactive=True, wactive=True, last_update=then)

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