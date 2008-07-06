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
  attr_accessor :watch_count, :user_count, :watching_users
end

class Timer

  def initialize(interval)
    @interval = interval
    @last_run = 0
  end

  def ready?
    @last_run + @interval > Time.now.to_i
  end

  def ran
    @last_run = Time.now.to_i
  end

end

TODO_TIMER = Timer.new 60
STATUS_TIMER = Timer.new 60

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

def check_matches(server, watch, res)
  watch.patterns.map do |pattern|
    re = Regexp.new pattern.regex
    [pattern, !! re.match(res.body) == pattern.positive]
  end.reject{|p,m| m}
end

def report_status(server, watch, res, match_status, default)
  if match_status.empty?
    server.deliver watch.user.jid, default
    res.status.to_i
  else
    p = match_status.first.first
    server.deliver watch.user.jid, "#{watch.url} failed to match #{p.positive ? 'positive' : 'negative'} pattern /#{p.regex}/"
    -1
  end
end

def check_result(server, watch, res)
  if res.status.to_i != 200
    server.deliver watch.user.jid, "Error on #{watch.url}.  Status=#{res.status} (#{res.message})"
    res.status.to_i
  elsif watch.status != nil && res.status.to_i != watch.status.to_i
    report_status server, watch, res, check_matches(server, watch, res),
      "Status of #{watch.url} changed from #{watch.status} to #{res.status} (#{res.message})"
  elsif watch.status.nil?
    report_status server, watch, res, check_matches(server, watch, res),
      "Started watching #{watch.url} -- status is #{res.status} (#{res.message})"
  else
    res.status.to_i
  end
end

def process_watches(server)
  Watch.todo(Whatsup::Config::CONF['general'].fetch('watch_freq', 10)).each do |watch|
    puts "Fetching #{watch.url} at #{Time.now.to_s}"
    $stdout.flush
    watch.update_attributes(:last_update => DateTime.now)
    Whatsup::Urlcheck.fetch(watch.url) do |res|
      status = check_result server, watch, res
      watch.update_attributes(:status => status)
    end
  end
  TODO_TIMER.ran
end

def update_status(server)
  watching = Watch.count(:active => true)
  users = User.count
  wusers = repository(:default).adapter.query('select count(distinct(user_id)) from watches').first
  stats = GlobalStats.instance
  if watching != stats.watch_count || users != stats.user_count || wusers != stats.watching_users
    puts "Updating status -- now watching #{watching} with #{users} users (#{wusers} watching)"
    $stdout.flush
    stats.watch_count = watching
    stats.user_count = users
    stats.watching_users = wusers
    status = "Watching around #{watching} URLs for #{wusers} users (#{users} users known)"
    server.send!(Jabber::Presence.new(nil, status,
      Whatsup::Config::CONF['xmpp'].fetch('priority', 1).to_i))
  end
  STATUS_TIMER.ran
end

def run_loop(server)
  process_xmpp_incoming server
  update_status server if STATUS_TIMER.ready?
  process_watches server if TODO_TIMER.ready?
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
