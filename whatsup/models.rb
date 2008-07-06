require 'rubygems'
gem 'dm-core'
require 'dm-core'
require 'dm-aggregates'

class User
  include DataMapper::Resource
  property :id, Integer, :serial => true
  property :jid, String, :nullable => false, :length => 128
  property :active, Boolean, :nullable => false, :default => true
  property :status, String

  has n, :watches

  # Find or create a user and update the status
  def self.update_status(jid, status)
    u = first(:jid => jid) || create!(:jid => jid)
    u.status = status
    u.save
    u
  end
end

class Watch

  include DataMapper::Resource
  include DataMapper::Aggregates

  property :id, Integer, :serial => true
  property :url, String, :nullable => false, :length => 1024
  property :status, Integer
  property :active, Boolean, :nullable => false, :default => true
  property :last_update, DateTime

  belongs_to :user
  has n, :patterns

  before :destroy do |w|
    w.patterns.each {|p| p.destroy }
  end

  def self.todo(timeout=10)
    q=<<EOF
    select w.id
      from watches w join users on (users.id == w.user_id)
      where
        users.active is not null
        and users.active = ?
        and users.status not in ('dnd', 'offline', 'unavailable')
        and w.active = ?
        and ( w.last_update is null or w.last_update < ?)
      limit 50
EOF
    ids = repository(:default).adapter.query(q, true, true,
      DateTime.now - Rational(timeout, 1440))
    self.all(:conditions => {:id => ids})
  end
end

class Pattern
  include DataMapper::Resource

  property :id, Integer, :serial => true
  property :positive, Boolean, :nullable => false
  property :regex, String, :nullable => false, :length => 1024

  belongs_to :watch
end