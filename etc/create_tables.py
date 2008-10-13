#!/usr/bin/env python
"""

Copyright (c) 2007  Dustin Sallings <dustin@spy.net>
"""

import sys
sys.path.append('lib')
sys.path.append('../lib')

import models

models._metadata.create_all(models._engine)
