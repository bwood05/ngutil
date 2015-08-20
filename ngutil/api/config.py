import json
from os import path
from string import ascii_uppercase, ascii_lowercase, digits
from random import SystemRandom

# ngutil
from ngutil.common import _NGUtilCommon

class _NGUtilAPIConfig(_NGUtilCommon):
    """
    Class used for configuring the API server.
    """
    def __init__(self):
        super(_NGUtilAPIConfig, self).__init__()
        
        # API configuration file
        self.config_file = '/root/.ngutil/api.json'
        
        # API configuration object
        self.api_config  = {}
        
    def _generate_key(self):
        """
        Generate an API key.
        """
        return ''.join(SystemRandom().choice(ascii_uppercase + ascii_lowercase + digits) for _ in range(48))
        
    def _write_config(self):
        """
        Write the configuration to the API authentication file
        """
        
        # Don't overwrite an existing config
        if path.isfile(self.config_file):
            self.die('Cannot overwrite existing API configuration: {0}'.format(self.config_file))
        
        try:
            with open(self.config_file, 'w') as file:
                file.write(json.dumps(self.api_config))
            self.feedback.success('Wrote out API configuration: {0}'.format(self.config_file))
        except Exception as e:
            self.die('Failed to write API configuration: {0}'.format(str(e)))
            
    def run(self):
        """
        Run the command line configuration wizard.
        """
        self.feedback.block([
            'NGUtil API Configuration',
            '-' * 60,
            'This utility will setup the parameters file for the embedded API',
            'server. This is still experimental and should not be used in your',
            'production environment.'
        ], 'CONFIG')
        
        # Prompt for username / IP address / port
        self.feedback.input('Please enter a username to connect to the embedded API server (ngadmin): ', key='username', default='ngadmin')
        self.feedback.input('Please enter the IP address to bind to (0.0.0.0): ', key='ipaddr', default='0.0.0.0')
        self.feedback.input('Please enter the port to bind to (10557): ', key='port', default=10557)
        self.feedback.input('Please enter the path to an optional SSL certificate: ', key='ssl_cert', default=False)
        
        # Store the API parameters
        self.api_config = {
            'user':     self.feedback.get_response('username'),
            'key':      self._generate_key(),
            'ipaddr':   self.feedback.get_response('ipaddr'),
            'port':     self.feedback.get_response('port'),
            'ssl_cert': self.feedback.get_response('ssl_cert')
        }
        
        # Write out the config
        self._write_config()
        
        # Display the configuration summary
        self.feedback.block([
            'API Configuration Complete!',
            '-' * 60,
            'You may use the following information to make API requests to the',
            'embedded HTTP server:\n',
            '> API User: {0}'.format(self.api_config['user']),
            '> API Key: {0}'.format(self.api_config['key']),
            '> API URL: http://{0}:{1}\n'.format(self.api_config['ipaddr'], str(self.api_config['port'])),
            'These values are stored in: {0}'.format(self.config_file)
        ], 'COMPLETE')