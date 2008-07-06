#!/usr/bin/env ruby

require 'rubygems'
require 'sqlite3'
require 'date'
require 'xmpp4r-simple'

require 'whatsup/config'
require 'whatsup/models'
require 'whatsup/commands'

def process_xmpp_incoming(server)
  server.presence_updates do |user, status, message|
    User.update_status user, status
  end
  server.received_messages do |msg|
    cmd, args = msg.body.split(' ', 2)
    cp = Whatsup::Commands::CommandProcessor.new server
    cp.dispatch cmd, User.first(:jid => msg.from.bare.to_s), args
  end
  server.new_subscriptions do |from, presence|
    puts "Subscribed by #{from}"
  end
  server.subscription_requests do |from, presence|
    puts "Sub req from #{from}"
  end
end

def run_loop(server)
  puts "Processing at #{Time.now.to_s}"
  $stdout.flush
  process_xmpp_incoming server
  sleep Whatsup::Config::TIMEOUT
rescue StandardError, Interrupt
  puts "Got exception:  #{$!.inspect}"
  sleep 5
end

def inner_loop(server)
  loop do
    run_loop server
  end
end

loop do
  server = Jabber::Simple.new(
    Whatsup::Config::CONF['xmpp']['jid'],
    Whatsup::Config::CONF['xmpp']['pass'])
  server.send!(Jabber::Presence.new(nil,
    Whatsup::Config::CONF['xmpp']['status'] || 'In service',
    (Whatsup::Config::CONF['xmpp']['priority'] || 1).to_i))

  puts "Set up with #{server.inspect}"
  $stdout.flush
  inner_loop server
end
