#!/usr/bin/env ruby

require 'whatsup/config'
require 'whatsup/models'

puts "Migrating..."
DataMapper.auto_migrate!