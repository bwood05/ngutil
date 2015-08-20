from __future__ import print_function
import re
import ssl
import json
from os import path
from urlparse import parse_qsl
from SocketServer import TCPServer
from sys import exit, stderr
from traceback import format_exc
from cgi import parse_header, parse_multipart
from BaseHTTPServer import BaseHTTPRequestHandler
from base64 import b64decode

# ngutil
from ngutil.common import _NGUtilCommon
from ngutil.api.router import _NGUtilAPIRouter

def get_api_config():
    """
    Get and return the API configuration object.
    """
    
    # API attributes files
    try:
        with open('/root/.ngutil/api.json', 'r') as file:
            auth_attrs = json.loads(file.read())
    except Exception as e:
        self.die('Failed to read API configuration file: {0}'.format(str(e)))
    
    # Make sure authentication attributes have been set
    if not auth_attrs:
        self.die('Cannot start API server, missing configuration file')
    
    # Check for required keys
    for k in ['user', 'key']:
        if not auth_attrs.get(k, None):
            self.die('Cannot start API server, missing required key \'{0}\' in configuration file'.format(k))
            
    # Return authentication attributes
    return auth_attrs

class _ServerBase(BaseHTTPRequestHandler):
    """
    Main class for authenticating and handling incoming requests.
    """
    def authenticate(self):
        """
        Authenticate against header information.
        """
        
        # API configuration / incoming headers
        api_config  = get_api_config()
        api_headers = self.headers.dict
        
        # Make sure the authorization header is set
        if not 'authorization' in api_headers:
            self.send_response(401)
            self.send_header('Content-type', 'text/plain')
            self.send_header('WWW-Authenticate', 'Basic')
            self.end_headers()
            return False
        
        # Extract username/key
        auth_decoded = b64decode(re.compile(r'^Basic (.*$)').sub(r'\g<1>', api_headers['authorization']))
        auth_user    = re.compile(r'(^[^:]+):.*$').sub(r'\g<1>', auth_decoded).rstrip()
        auth_key     = re.compile(r'^[^:]+:(.*$)').sub(r'\g<1>', auth_decoded).rstrip()
        
        # Validate authentication parameters
        if not api_config['user'] == auth_user or not api_config['key'] == auth_key:
            self.send_response(401)
            self.send_header('Content-type', 'text/plain')
            self.send_header('WWW-Authenticate', 'Basic')
            self.end_headers()
            return False
        
        # Authentication success
        return True
    
    def _get_params(self):
        """
        Parse parameters from either the URL string (GET) or from the request
        body (POST/PUT)
        """
    
        # GET parameters
        if self.command == 'GET':
            if '?' in self.path:
                self.path, qs = self.path.split('?', 1)
                return dict(parse_qsl(qs))
            else:
                return {}
            
        # PUT / POST / DELETE parameters
        else:
            clen = int(self.headers.get('content-length', 0))
            try:
                return json.loads(self.rfile.read(clen))
            except:
                return {}
    
    def _route_request(self):
        """
        Route the incoming request.
        """
        try:
            
            # Parse params from either URL or request body
            params = self._get_params()
            
            # Load the request router
            response = _NGUtilAPIRouter().route(method=self.command, path=self.path, params=params)
            
            # Try to send a JSON response
            try:
                json_str = json.dumps(response['body'])
                self._set_headers(code=response['code'], ctype='application/json')
                self.wfile.write(json_str)
            
            # Plain text response
            except:
                self._set_headers(code=response['code'], ctype='text/plain')
                self.wfile.write(response['body'])
        
        # Internal error when routing the request
        except Exception as e:
            print(format_exc())
            self._set_headers(code=500)
            self.wfile.write(str(e))
    
    def _set_headers(self, code=200, ctype='text/html'):
        self.send_response(code)
        self.send_header('Content-type', ctype)
        self.end_headers()

    def do_HEAD(self):
        """
        Handle incoming HEAD requests.
        """
        self._set_headers()
        
    def do_GET(self):
        """
        Handle incoming GET requests.
        """
        if self.authenticate():
            self._route_request()
            
    def do_DELETE(self):
        """
        Handle incoming DELETE requests.
        """
        if self.authenticate():
            self._route_request()
    
    def do_PUT(self):
        """
        Handle incoming PUT requests.
        """
        if self.authenticate():
            self._route_request()
        
    def do_POST(self):
        """
        Handle incoming POST requests.
        """
        if self.authenticate():
            self._route_request()
       
class _NGUtilAPIServer(_NGUtilCommon):
    """
    Experimental class for running an embedded API server.
    """
    def __init__(self):
        super(_NGUtilAPIServer, self).__init__()
    
        # Start up the API server
        self._bootstrap()
    
    def _bootstrap(self):
        """
        Bootstrap the API server.
        """
        
        # API configuration
        api_config = get_api_config()
        
        # Socket server
        api_socket = TCPServer((api_config['ipaddr'], api_config['port']), _ServerBase)
        
        # Check for SSL support
        if api_config.get('ssl_cert'):
            if path.isfile(api_config['ssl_cert']):
                api_socket.socket = ssl.wrap_socket(api_socket.socket, certfile=api_config['ssl_cert'], server_side=True)
            else:
                self.feedback.warn('Starting in insecure (HTTP) mode, could not locate SSL certificate: {0}'.format(api_config['ssl_cert']))
            
        # Keep the server running
        api_socket.serve_forever()
    
    