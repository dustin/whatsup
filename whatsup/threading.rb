require 'thread'

module Whatsup
  module Threading
    IN_QUEUE = Queue.new
    OUT_QUEUE = Queue.new

    def self.start_worker
      Thread.new do
        loop do
          msg = IN_QUEUE.pop
          msg.call
        end
      end
    end

  end
end