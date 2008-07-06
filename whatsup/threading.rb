require 'thread'

module Whatsup
  module Threading
    IN_QUEUE = Queue.new
    OUT_QUEUE = Queue.new

    def self.start_worker
      Thread.new do
        loop do
          begin
            msg = IN_QUEUE.pop
            msg.call
          rescue StandardError, Interrupt
            puts "ERROR!  #{$!}\n#{$!.backtrace.join("\t\n")}"
          rescue
            puts "ERROR!  #{$!}\n#{$!.backtrace.join("\t\n")}"
          end
        end
      end
    end

  end
end