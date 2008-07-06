require 'rubygems'
gem 'dm-core'
require 'dm-core'

module Whatsup
  module Config
    CONF = ::YAML.load_file 'whatsup.yml'
    TIMEOUT = CONF['general']['timeout'].to_i

    DataMapper.setup(:default, CONF['general']['db'])
  end
end