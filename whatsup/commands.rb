require 'net/http'
require 'whatsup/urlcheck'
require 'whatsup/search'

module Whatsup
  module Commands

    class Help
      attr_accessor :short_help, :full_help

      def initialize(short_help)
        @short_help = @full_help = short_help
      end

      def to_s
        @short_help
      end
    end

    module CommandDefiner

      def all_cmds
        @@all_cmds ||= {}
      end

      def cmd(name, help=nil, &block)
        unless help.nil?
          all_cmds()[name.to_s] = Whatsup::Commands::Help.new help
        end
        define_method(name, &block)
      end

      def help_text(name, text)
        all_cmds()[name.to_s].full_help = text
      end

    end

    class CommandProcessor

      extend CommandDefiner

      def initialize(conn)
        @jabber = conn
      end

      def typing_notification(user)
        @jabber.client.send("<message
            from='#{Config::SCREEN_NAME}'
            to='#{user.jid}'>
            <x xmlns='jabber:x:event'>
              <composing/>
            </x></message>")
      end

      def dispatch(cmd, user, arg)
        typing_notification user
        if self.respond_to? cmd
          self.send cmd.to_sym, user, arg
        else
          send_msg user, "I don't understand #{cmd}.  Send `help' for what I do know."
        end
      end

      def send_msg(user, text)
        @jabber.deliver user.jid, text
      end

      cmd :help, "Get help for commands." do |user, arg|
        cmds = self.class.all_cmds()
        if arg.blank?
          out = ["Available commands:"]
          out << "Type `help somecmd' for more help on `somecmd'"
          out << ""
          out << cmds.keys.sort.map{|k| "#{k}\t#{cmds[k]}"}
          send_msg user, out.join("\n")
        else
          h = cmds[arg]
          if h
            out = ["Help for `#{arg}'"]
            out << h.full_help
            send_msg user, out.join("\n")
          else
            send_msg user, "Topic #{arg} is unknown.  Type `help' for known commands."
          end
        end
      end

      cmd :status, "Show your status." do |user, arg|
        out = ["Jid:  #{user.jid}"]
        out << "Jabber Status:  #{user.status}"
        out << "whatsup Status:  #{user.active ? 'Active' : 'Inactive'}"
        if user.quiet?
          out << "Quiet Until:  #{user.quiet_until.to_s}"
        end
        out << "You are currently watching #{user.watches.size} URLs."
        send_msg user, out.join("\n")
      end

      cmd :get, "Get a URL" do |user, url|
        validate_url user, url or return
        Whatsup::Urlcheck.fetch(url) do |res|
          send_msg user, "#{res.status.to_i == 200 ? ':)' : ':('} Got a #{res.status} from #{url} in #{res.time}s (#{res.body.size} bytes)"
        end
      end

      cmd :watch, "Watch a URL" do |user, url|
        validate_url user, url or return
        begin
          Watch.create! :user => user, :url => url
          send_msg user, "Scheduled a watch for #{url}."
        rescue
          puts "Failed to create a watch for #{url} for #{user.jid}:  #{$!}"
          $stdout.flush
          send_msg user, "Unable to set up this watch for you (#{$!})."
        end
      end
      help_text :watch, <<-EOF
Periodically validate the URL at the given location.

You can use match and negmatch to add content validation.
EOF

      cmd :on, "Activate monitoring" do |user, nothing|
        user.update_attributes(:active => true)
        send_msg user, "Marked you active."
      end

      cmd :off, "Deactivate monitoring" do |user, nothing|
        user.update_attributes(:active => false)
        send_msg user, "Marked you inactive."
      end

      cmd :quiet, "Be quiet for a bit (1m, 2h, 3d, etc..)" do |user, args|
        m = {'m' => 1, 'h' => 60, 'd' => 1440}
        time, url = args.split(/\s+/, 2)
        match = /(\d+)([hmd])/.match(time)
        if match
          t = match[1].to_i * m[match[2]]
          u = DateTime.now + Rational(t, 1440)
          if url
            with_my_watch user, url do |watch|
              watch.update_attributes(:quiet_until => u)
              send_msg user, "You won't hear from me again for for #{watch.url} for another #{time} (until #{u.to_s})"
            end
          else
            user.update_attributes(:quiet_until => u)
            send_msg user, "You won't hear from me again for another #{time} (until #{u.to_s})"
          end
        else
          send_msg user, "Didn't understand how long you wanted me to be quit.  Try 5m"
        end
      end
      help_text :quiet, <<-EOF
Quiet alerts for a period of time.

Available time units:  m, h, d

You can either quiet an individual URL like this:

  quiet 5m http://broken.example.com/

or from everything:

  quiet 1h
EOF

      cmd :watching, "List all current watches" do |user, nothing|
        watches = user.watches.sort{|a,b| a.url <=> b.url}.map do |watch|
          face = watch.status == 200 ? ':)' : ':('
          "#{face} #{watch.url} (#{watch.active ? 'enabled' : 'disabled'} -- last=#{watch.status.nil? ? 'unknown' : watch.status})"
        end
        send_msg user, "Watching #{watches.size} URLs\n" + watches.sort.join("\n")
      end

      cmd :enable, "Enable a watch that was specifically disabled" do |user, url|
        with_my_watch user, url do |watch|
          watch.update_attributes :active => true
          send_msg user, "Enabled watching of #{url}"
        end
      end
      help_text :watching, <<-EOF
Enable checking of a URL that was previously disabled.

Usage:  enable http://working.example.com/
EOF

      cmd :disable, "Disable a watch for a specific URL" do |user, url|
        with_my_watch user, url do |watch|
          watch.update_attributes :active => false
          send_msg user, "Disabled watching of #{url}"
        end
      end
      help_text :disable, <<-EOF
Disable checking of a URL.

Usage: disable http://broken.example.com/
EOF

      cmd :unwatch, "Stop watching a URL" do |user, url|
        with_my_watch user, url do |watch|
          watch.destroy
          send_msg user, "Stopped watching #{url}"
        end
      end

      cmd :search, "Do a web search." do |user, term|
        if term.blank?
          send_msg user, "Need a search term."
        end
        Whatsup::Threading::IN_QUEUE << Proc.new do
          begin
            google = Whatsup::Search::Google.new
            out = ["Search results:"]
            google.search(term).resultElements.each_with_index do |e, i|
              out << "#{i+1}: #{e.title.strip_tags}"
              out << e.snippet.strip_tags
              out << e.uRL
              out << ""
            end
            send_msg user, out.join("\n")
          rescue StandardError, Interrupt
            puts "Could not perform search:  #{$!}" + $!.backtrace.join("\n\t")
            send_msg user, "Could not peform your search."
          end
        end
      end
      help_text :search, "This really doesn't belong here."

      cmd :match, "Ensure a pattern matches for a URL" do |user, args|
        add_pattern_match user, args, true
      end
      help_text :match, <<-EOF
Add a positive regex match for a URL.

Usage:  match http://www.example.com/ working
EOF

      cmd :negmatch, "Ensure a pattern does not match for a URL" do |user, args|
        add_pattern_match user, args, false
      end
      help_text :negmatch, <<-EOF
Add a negative regex match for a URL.

Usage: negmatch http://www.example.com/ hac?[kx]ed.by
EOF

      cmd :inspect, "Inspect matches for a given URL" do |user, url|
        rv=[]
        with_my_watch user, url do |watch|
          rv << "Status for #{url} (#{watch.active ? 'enabled' : 'disabled'})"
          if watch.quiet?
            rv << "Alerts for this URL are suspended until #{watch.quiet_until}"
          end
          rv << "Last status: #{watch.status} (as of #{watch.last_update.to_s})"
          if watch.patterns.empty?
            rv << "No match patterns configured"
          else
            rv << "Patterns:"
            watch.patterns.each do |p|
              rv << "\t#{p.positive ? '+' : '-'}: /#{p.regex}/"
            end
          end
        end
        send_msg user, rv.join("\n")
      end

      cmd :clear_matches, "Clear all matches for a url" do |user, url|
        with_my_watch user, url do |watch|
          watch.patterns.each {|p| p.destroy}
          send_msg user, "Removed all patterns for #{url}"
        end
      end

      private

      def validate_url(user, url)
        u = URI.parse url
        if u.scheme != 'http'
          send_msg user, "Only http URLs are supported at this time."
          return false
        end
        if u.host.nil?
          send_msg user, "The URL must include host"
          return false
        end
        if u.path.nil? || u.path == ''
          send_msg user, "The URL must include a path."
          return false
        end
        true
      rescue URI::InvalidURIError
        send_msg user, "#{$!}"
        false
      end

      def add_pattern_match(user, args, positive)
        url, pattern = args.split(' ', 2)
        with_my_watch user, url do |watch|
          begin
            re = Regexp.new pattern
            watch.patterns.create :positive => positive, :regex => pattern
            send_msg user, "Configured a #{positive ? 'positive' : 'negative'} match pattern for #{url}"
          rescue RegexpError
            send_msg user, "Your regex seems broken."
          end
        end
      end

      def with_my_watch(user, url, &block)
        if url.nil? || url.strip == ''
          send_msg user, "URL argument required."
          return
        end
        watch = user.watches.first(:url => url.strip)
        if watch
          yield watch
        else
          send_msg user, "Cannot find watch for #{url}"
        end
      end

    end # CommandProcessor

  end
end
