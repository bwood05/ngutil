import os
import re
import sys
import argparse
from platform import linux_distribution

# Package version / root
__version__ = '0.1-2'
__root__    = os.path.abspath(os.path.dirname(__file__))

# NGUtil Libraries
from ngutil.site import _NGUtilSite
from ngutil.application import _NGUtilApp
from ngutil.api.config import _NGUtilAPIConfig
from ngutil.common import _NGUtilCommon, R_OBJECT, R_FATAL

class _NGUtilArgs(_NGUtilCommon):
    """
    Class object for handling command line arguments.
    """
    def __init__(self, **kwargs):
        super(_NGUtilArgs, self).__init__()

        # Arguments parser / object
        self.parser  = None
        self._args   = None
        
        # Construct command line arguments
        if not kwargs:
            self._construct_cli()
        
        # Construct module level arguments
        else:
            self._args = kwargs
        
    def list(self):
        """
        Return a list of argument keys.
        """
        return self._args.keys()
        
    def _return_help(self):
         return ("NGUtil\n\n"
                 "Scripts to help install and configure sites with nginx and php-fpm.\n")
        
    def _actions_help(self):
        """
        Return a formatted string of supported actions.
        """
        return(
            'setup:        Setup  NGINX and PHP-FPM\n'
            'create_site:  Create a new NGINX site definition\n'
            'enable_site:  Link an available site in "/etc/nginx/sites-enabled"\n'
            'disable_site: Remove a site from "/etc/nginx/sites-enabled"\n'
            'list_sites:   List all managed sites\n'
            'config_api:   Run the embedded API server configuration'
        )
        
    def _construct_cli(self):
        """
        Construct the command line argument parser.
        """
        
        # Create a new argument parsing object and populate the arguments
        self.parser = argparse.ArgumentParser(description=self._return_help(), formatter_class=argparse.RawTextHelpFormatter)
        self.parser.add_argument('action', help=self._actions_help())
        self.parser.add_argument('-n', '--fqdn', help='FQDN of the site to be created', action='append')
        self.parser.add_argument('-d', '--default-doc', help='The default index document for the site', action='append')
        self.parser.add_argument('-a', '--activate', help='Actives the site by creating a symlink', action='store_true')
        self.parser.add_argument('-s', '--ssl', help='Configure the site to use SSL', action='store_true')
        self.parser.add_argument('-C', '--ssl-cert', help='Location of the SSL certificate for the site', action='append')
        self.parser.add_argument('-K', '--ssl-key', help='Location of the SSL key for the site', action='append')
        self.parser.add_argument('-f', '--force', help='Force a re-run of the initial setup utility', action='store_true')
        self.parser.add_argument('-S', '--source', help='Specify a local or remote location to retrieve the site code base', action='append')
      
        # Parse CLI arguments
        sys.argv.pop(0)
        self._args = vars(self.parser.parse_args(sys.argv))
        
    def set(self, k, v):
        """
        Set a new argument or change the value.
        """
        self._args[k] = v
        
    def get(self, k=None, default=None, use_json=False):
        """
        Retrieve an argument passed via the command line.
        """
        
        # Return all arguments
        if not k:
            _all_args = {}
            for k,v in self._args.iteritems():
                _all_args[k] = v if not isinstance(v, list) else v[0]
            return _all_args
        
        # Get the value from argparse
        _raw = self._args.get(k, default)
        _val = _raw if not isinstance(_raw, list) else _raw[0]
        
        # Return the value
        return _val if not use_json else json.dumps(_val)

class NGUtil(_NGUtilCommon):
    """
    Public class used when invoking 'ngutil'.
    """
    def __init__(self, is_cli=True, **kwargs):
        super(NGUtil, self).__init__()
        
        # Running from the command line or not
        self.is_cli = is_cli
        
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
        this_version = re.compile(r'(^[0-9]+)\..*$').sub(r'\g<1>', linux_distribution()[1])
    
        # Make sure the distribution is supported
        if not this_distro in supported:
            return R_FATAL(
                msg  = 'Current distribution \'{0}\' not supported...'.format(this_distro),
                code = 501
            )
    
        # Make sure the version is supported
        if not this_version in supported[this_distro]:
            return R_FATAL(
                msg  = 'Current version \'{0}\' not supported for this distribution...'.format(this_version),
                code = 501
            )
            
        # Return a response object
        return R_OBJECT(msg='OK', code=200)
    
    def _check_user(self):
        """
        Make sure the module is being run as root.
        """
        if not os.geteuid() == 0:
            return R_FATAL(
                msg  = 'ngutil must be run as root user...',
                code = 501
            )
            
        # Return a response object
        return R_OBJECT(msg='OK', code=200)
    
    def create_site(self):
        """
        Create a new NGINX site.
        """
        return self.site.create(self.args.get())
        
    def list_sites(self):
        """
        List all managed NGINX sites.
        """
        return self.site.list_all()
        
    def disable_site(self):
        """
        Disable an NGINX site.
        """
        return self.site.disable(self.args.get())
        
    def enable_site(self):
        """
        Enable an NGINX site.
        """
        return self.site.enable(self.args.get())
        
    def config_api(self):
        """
        Configure the embedded API server.
        """
        
        # Configuration object
        api_config = _NGUtilAPIConfig()
        api_config.run()
        
    def setup(self):
        """
        Setup the NGINX server.
        """
        return self.app.setup(self.args.get())
    
    def _action_mapper(self):
        """
        Map an action keyword to a method.
        """
        return {
            'create_site': self.create_site,
            'enable_site': self.enable_site,
            'disable_site': self.disable_site,
            'list_sites': self.list_sites,
            'config_api': self.config_api,
            'setup': self.setup
        }
        
    def run(self):
        """
        Run from the command line.
        """
        
        # Check effective user / supported OS
        for check in [self._check_user, self._check_support]:
            check_rsp = check()
            
            # If any of the checks failed
            if check_rsp.fatal:
                
                # Run from the command line
                if self.is_cli:
                    self.die(check_rsp.body)
                    
                # Run from module import
                else:
                    return check_rsp
        
        # Target action / action mapper
        action = self.args.get('action')
        mapper = self._action_mapper()
        
        # Make sure the action is valid
        if not action in mapper:
            action_rsp = R_FATAL(
                msg  = '\'action\' argument must be one of: {0}'.format(mapper.keys()),
                code = 404
            )
            
            # Run from the command line
            if self.is_cli:
                self.die(action_rsp.body)
                
            # Run from module import
            else:
                return action_rsp
            
        # Run the action method
        mapper_rsp = mapper[action]()
        
        # If the response is fatal
        if mapper_rsp.fatal and self.is_cli:
            self.die(mapper_rsp.body)
                
        # Return the response
        return mapper_rsp
        
def cli():
    """
    Entry point for running NGUtil from the command line.
    """
    _ngutil = NGUtil()
    _ngutil.run()