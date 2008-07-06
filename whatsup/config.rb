require 'rubygems'
gem 'dm-core'
require 'dm-core'

module Whatsup
  module Config
    CONF = ::YAML.load_file 'whatsup.yml'
    LOOP_SLEEP = CONF['general'].fetch('loop_sleep', 1).to_i
    SCREEN_NAME = CONF['xmpp']['jid']

    DataMapper.setup(:default, CONF['general']['db'])
  end
end