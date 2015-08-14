import os
import re
import sys
import argparse
from platform import linux_distribution

# Package version / root
__version__ = '0.1-1'
__root__    = os.path.abspath(os.path.dirname(__file__))

# NGUtil Libraries
from .site import _NGUtilSite
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
        
        # Check effective user
        self._check_user()
        
        # Application / site manager
        self.app    = _NGUtilApp()
        self.site   = _NGUtilSite()
        
        # Create the argument handler
        self.args   = _NGUtilArgs(**kwargs)
    
    def _check_support(self):
        """
        Check if the current distribution/version is supported.
        """
        
        # Supported distributions / versions
        supported = {
            'centos': ['6']    
        }
        
        # Get the current distro / major version
        this_distro  = linux_distribution()[0].lower()
        this_version = re.compile(r'(^[0-9]+)\..*$').sub(r'\g<1>', linux_distribution[1])
    
        # Make sure the distribution is supported
        if not this_distro in supported:
            self.die('Current distribution \'{0}\' not supported...'.format(this_distro))
    
        # Make sure the version is supported
        if not this_version in supported[this_distro]:
            self.die('Current version \'{0}\' not supported for this distribution...'.format(this_version))
    
    def _check_user(self):
        """
        Make sure the module is being run as root.
        """
        if not os.geteuid() == 0:
            self.die('ngutil must be run as root user...')
    
    def create_site(self):
        """
        Create a new NGINX site.
        """
        self.feedback.info('Preparing to setup NGINX site')
        
        # Define a new NGINX site
        self.site.define(self.args)
        
        # Create the site
        self.site.create()
        
    def setup(self):
        """
        Setup the NGINX server.
        """
        self.feedback.info('Preparing to setup NGINX...')
        
        # Install required software
        self.app.install()
        
        # Setup the firewall
        self.app.config_firewall([
            {
                'chain': 'INPUT',
                'params': {
                    '-p': 'tcp',
                    '--dport': '80',
                    '-m state --state': 'NEW',
                    '-j': 'ACCEPT'
                }
            },
            {
                'chain': 'INPUT',
                'params': {
                    '-p': 'tcp',
                    '--dport': '443',
                    '-m state --state': 'NEW',
                    '-j': 'ACCEPT'
                }
            }
        ])
    
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
        
        # Make sure the action is valid
        if not action in mapper:
            self.die('\'action\' argument must be one of: {0}'.format(mapper.keys()))
            
        # Run the action method
        mapper[action]()
        
def cli():
    """
    Entry point for running NGUtil from the command line.
    """
    _ngutil = NGUtil()
    _ngutil.run()