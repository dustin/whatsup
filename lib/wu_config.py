#!/usr/bin/env python
"""
Configuration for whatsup.

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import yaml

CONF=yaml.load(open('whatsup.yml'))
SCREEN_NAME = CONF['xmpp']['jid']
