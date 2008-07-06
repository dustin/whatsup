require 'whatsup/threading'
require 'net/http'

module Whatsup
  module Urlcheck

    class Response
      attr_reader :status, :time, :body

      def initialize(status, time, body)
        @status = status
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
          res = Net::HTTP.get_response u
          body = res.body
          endt = Time.now
          block.call Response.new(res.code, (endt - startt), body)
        rescue
          puts "#{$!}"
          "Something went wrong.  Probably your fault."
        end
      end
      Whatsup::Threading::IN_QUEUE << cmd
    end

  end
end