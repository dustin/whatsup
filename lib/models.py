from sqlalchemy import *
from sqlalchemy.orm import sessionmaker, mapper, relation, backref

_engine = create_engine('sqlite:///whatsup.sqlite3')

_metadata = MetaData()

class User(object):
    pass

class Watch(object):
    pass

_users_table = Table('users', _metadata,
    Column('id', Integer, primary_key=True),
    Column('jid', String(128)),
    Column('active', Boolean),
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

mapper(User, _users_table, properties={
    'watches': relation(Watch)
    })
mapper(Watch, _watches_table, properties={
    'user': relation(User)
    })

Session = sessionmaker()
Session.configure(bind=_engine)