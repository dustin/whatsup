require 'whatsup/threading'
require 'net/http'

module Whatsup
  module Urlcheck

    class Response
      attr_reader :status, :message, :time, :body

      def initialize(status, message, time, body)
        @status = status
        @message = message
        @time = time
        @body = body
      end
    end

    def self.fetch(url, &block)
      cmd = Proc.new do
        begin
          u=URI.parse url
          $stdout.flush
          startt = Time.now
          res = Net::HTTP.start(u.host, u.port) do |http|
            http.get(u.path, {'Connection' => 'close', 'User-Agent' => 'Whatsup'})
          end
          body = res.body
          endt = Time.now
          block.call Response.new(res.code, res.message, (endt - startt), body)
        rescue Interrupt, Timeout
          puts "#{$!}"
          block.call Response.new(-1, $!.to_s, (Time.now - startt), '')
        rescue
          puts "#{$!}"
          block.call Response.new(-1, $!.to_s, (Time.now - startt), '')
        end
      end
      Whatsup::Threading::IN_QUEUE << cmd
    end

  end
end