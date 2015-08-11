import os
import sys
import argparse

# Package version / root
__version__ = '0.1-1'
__root__    = os.path.abspath(os.path.dirname(__file__))

# NGUtil Libraries
from .common import _NGUtilCommon
from .application import _NGUtilApp

class _NGUtilArgs(_NGUtilCommon):
    """
    Class object for handling command line arguments.
    """
    def __init__(self, **kwargs):
        super(_NGUtilArgs, self).__init__()

        # Arguments parser / object
        self.parser  = None
        self._args   = None
        
        # Construct arguments
        self._construct()
        
    def list(self):
        """
        Return a list of argument keys.
        """
        return self._args.keys()
        
    def _return_help(self):
         return ("NGUtil\n\n"
                 "Scripts to help install and configure sites with nginx and php-fpm.\n")
        
    def _construct(self):
        """
        Construct the argument parser.
        """
        
        # Create a new argument parsing object and populate the arguments
        self.parser = argparse.ArgumentParser(description=self._return_help(), formatter_class=argparse.RawTextHelpFormatter)
        self.parser.add_argument('action', help='Create a site [create_site] or setup NGINX [setup]')
        self.parser.add_argument('-n', '--fqdn', help='FQDN of the site to be created', action='append')
        self.parser.add_argument('-d', '--default-doc', help='The default index document for the site', action='append')
        self.parser.add_argument('-a', '--activate', help='Actives the site by creating a symlink', action='store_true')
        self.parser.add_argument('-s', '--ssl', help='Configure the site to use SSL', action='store_true')
        self.parser.add_argument('-C', '--ssl-cert', help='Location of the SSL certificate for the site', action='append')
        self.parser.add_argument('-K', '--ssl-key', help='Location of the SSL key for the site', action='append')
      
        # Parse CLI arguments
        sys.argv.pop(0)
        self._args = vars(self.parser.parse_args(sys.argv))
        
    def set(self, k, v):
        """
        Set a new argument or change the value.
        """
        self._args[k] = v
        
    def get(self, k, default=None, use_json=False):
        """
        Retrieve an argument passed via the command line.
        """
        
        # Get the value from argparse
        _raw = self._args.get(k, default)
        _val = _raw if not isinstance(_raw, list) else _raw[0]
        
        # Return the value
        return _val if not use_json else json.dumps(_val)

class NGUtil(_NGUtilCommon):
    """
    Public class used when invoking 'ngutil'.
    """
    def __init__(self, **kwargs):
        super(NGUtil, self).__init__()
        
        # Application manager
        self.app    = _NGUtilApp()
        
        # Create the argument handler
        self.args   = _NGUtilArgs(**kwargs)
    
        # SSL attributes
        self.ssl  = {
            'enable': False,
            'cert': None,
            'key': None
        }
    
    def create_site(self):
        """
        Create a new NGINX site.
        """
        
        # Required arguments
        required = ['fqdn']
        optional = ['default_doc', 'activate', 'ssl', 'ssl_cert', 'ssl_key']
        
        # Make sure all required arguments are set
        for k in required:
            if not self.args.get(k):
                self._die('ERROR: Missing required argument \'{}\''.format(k))
        
        # If using SSL
        if self.args.get('ssl'):
            self.ssl['enable'] = True
            
            # Make sure the certificate and key are set
            for k in ['ssl_cert', 'ssl_key']:
                if not self.args.get(k):
                    self._die('ERROR: Missing required argument \'{}\', must supply to enable SSL'.format(k))
                
                # Make sure the file exists
                ssl_file = self.args.get(k)
                if not os.path.isfile(ssl_file):
                    self._die('ERROR: Could not locate \'{}\' file \'{}\''.format(k, ssl_file))
            
            # Set the SSL key and certificate
            self.ssl['key'] = self.args.get('ssl_key')
            self.ssl['cert'] = self.args.get('ssl_cert')
        
    def setup(self):
        """
        Setup the NGINX server.
        """
        return 
    
    def _action_mapper(self):
        """
        Map an action keyword to a method.
        """
        return {
            'create_site': self.create_site,
            'setup': self.setup
        }
        
    def run(self):
        """
        Run from the command line.
        """
        
        # Target action / action mapper
        action = self.args.get('action')
        mapper = self._action_mapper()
        
        print self.args.list()
        
        # Make sure the action is valid
        if not action in mapper:
            self._die('ERROR: \'action\' argument must be one of: {}'.format(mapper.keys()))
            
        # Run the action method
        mapper[action]()
        
def cli():
    """
    Entry point for running NGUtil from the command line.
    """
    _ngutil = NGUtil()
    _ngutil.run()