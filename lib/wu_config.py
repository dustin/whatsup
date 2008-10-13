#!/usr/bin/env python
"""
Configuration for whatsup.

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import ConfigParser

CONF=ConfigParser.ConfigParser()
CONF.read('whatsup.conf')
SCREEN_NAME = CONF.get('xmpp', 'jid')
