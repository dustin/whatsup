#!/usr/bin/env python
"""
Configuration for whatsup.

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import ConfigParser
import commands

CONF=ConfigParser.ConfigParser()
CONF.read('whatsup.conf')
SCREEN_NAME = CONF.get('xmpp', 'jid')
VERSION=commands.getoutput("git describe").strip()

BATCH_CONCURRENCY=CONF.getint('general', 'batch_concurrency')
WATCH_FREQ=CONF.getint('general', 'watch_freq')