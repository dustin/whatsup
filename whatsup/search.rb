require 'rubygems'
require 'soap/wsdlDriver'

module Whatsup

  $KCODE = 'UTF8'
  KEY = Whatsup::Config::CONF['general']['googlekey']
  WSDL = 'http://api.google.com/GoogleSearch.wsdl'

  module Search

    class Google
      def search(term, max=5)
        driver = SOAP::WSDLDriverFactory.new(WSDL).create_rpc_driver
        driver.doGoogleSearch(KEY, term, 0, max, true, "", true, 'lang_en',
          '', '')
      end
    end

  end

end
