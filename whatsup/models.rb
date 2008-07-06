require 'rubygems'
gem 'dm-core'
require 'dm-core'

class User
  include DataMapper::Resource
  property :id, Integer, :serial => true
  property :jid, String, :nullable => false, :length => 128
  property :status, String

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
  property :id, Integer, :serial => true
  property :url, String, :nullable => false, :length => 1024
  property :status, Integer
  belongs_to :user
  property :last_update, DateTime

  def self.todo(timeout=10)
    q=<<EOF
    select w.id
      from watches w join users on (users.id == w.user_id)
      where
        users.status is not null
        and users.status not in ('dnd', 'offline', 'unavailable')
        and ( w.last_update is null or w.last_update < ?)
      limit 50
EOF
    ids = repository(:default).adapter.query(q,
      DateTime.now - Rational(timeout, 1440))
    self.all(:conditions => {:id => ids})
  end
end
