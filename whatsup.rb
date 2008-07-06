#!/usr/bin/env ruby

require 'rubygems'
require 'sqlite3'
require 'date'
require 'xmpp4r-simple'

require 'whatsup/config'
require 'whatsup/models'
require 'whatsup/commands'

class GlobalStats
  include Singleton
  attr_accessor :watch_count
end

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

def process_watches(server)
  Watch.todo(Whatsup::Config::CONF['general'].fetch('watch_freq', 10)).each do |watch|
    puts "Fetching #{watch.url} at #{Time.now.to_s}"
    $stdout.flush
    watch.update_attributes(:last_update => DateTime.now)
    Whatsup::Urlcheck.fetch(watch.url) do |res|
      if res.status.to_i != 200
        server.deliver watch.user.jid, "Error on #{watch.url}.  Status=#{res.status} (#{res.message})"
      elsif watch.status != nil && res.status.to_i != watch.status.to_i
        server.deliver watch.user.jid, "Status of #{watch.url}.  Changed from #{watch.status} to #{res.status} (#{res.message})"
      elsif watch.status.nil?
        server.deliver watch.user.jid, "Starting to track #{watch.url}.  Current status is #{res.status} (#{res.message})"
      end
      watch.update_attributes(:status => res.status)
    end
  end
end

def update_status(server)
  watching = Watch.count(:active => true)
  if watching != GlobalStats.instance.watch_count
    puts "Updating status -- now watching #{watching} URLs"
    $stdout.flush
    GlobalStats.instance.watch_count = watching
    status = "Watching around #{Watch.count(:active => true)} URLs"
    server.send!(Jabber::Presence.new(nil, status,
      Whatsup::Config::CONF['xmpp'].fetch('priority', 1).to_i))
  end
end

def run_loop(server)
  process_xmpp_incoming server
  update_status server
  process_watches server
  sleep Whatsup::Config::LOOP_SLEEP
rescue StandardError, Interrupt
  puts "Got exception:  #{$!.inspect}\n#{$!.backtrace.join("\n\t")}"
  $stdout.flush
  sleep 5
end

def inner_loop(server)
  loop do
    run_loop server
  end
end

Whatsup::Config::CONF['general'].fetch('nthreads', 1).to_i.times do |t|
  puts "Starting thread #{t}"
  Whatsup::Threading.start_worker
end

loop do
  puts "Connecting..."
  $stdout.flush
  server = Jabber::Simple.new(
    Whatsup::Config::CONF['xmpp']['jid'],
    Whatsup::Config::CONF['xmpp']['pass'])
  update_status(server)

  puts "Set up with #{server.inspect}"
  $stdout.flush
  inner_loop server
end
