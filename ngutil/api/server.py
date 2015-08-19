import json
from sys import exit, stderr
from SocketServer import TCPServer
from BaseHTTPServer import BaseHTTPRequestHandler

# ngutil
from .common import _NGUtilCommon

class _ServerBase(BaseHTTPRequestHandler):
    def __init__(self):
        
        # Set authentication parameters
        self.auth = self._set_auth()
    
    def die(self, msg, code=1):
        """
        Print on stderr and die.
        """
        stderr.write('{0}\n'.format(msg))
        exit(code)
    
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        """
        Handle incoming GET requests.
        """
        self._set_headers()
        self.wfile.write("<html><body><h1>hi!</h1></body></html>")

    def do_HEAD(self):
        """
        Handle incoming HEAD requests.
        """
        self._set_headers()
        
    def do_POST(self):
        """
        Handle incoming POST requests.
        """
        self._set_headers()
        self.wfile.write("<html><body><h1>POST!</h1></body></html>")
        
    def _set_auth(self):
        """
        Pull authentication attributes from user directory.
        """
        
        # Authentication attributes files
        try:
            with open('/root/.ngutil/auth', 'r') as file:
                auth_attrs = json.loads(file.read())
        except Exception as e:
            self.die('Failed to read authentication file: {0}'.format(str(e)))
        
        # Make sure authentication attributes have been set
        if not auth_attrs:
            self.die('Cannot start API server, missing authentication file')
        
        # Check for required keys
        for k in ['user', 'key']:
            if not auth_attrs.get(k, None):
                self.die('Cannot start API server, missing required key \'{0}\' in authentication file'.format(k))
                
        # Return authentication attributes
        return auth_attrs
       
class _NGUtilAPI(_NGUtilCommon):
    """
    Experimental class for running an embedded API server.
    """
    def __init__(self, ipaddr='0.0.0.0', port=10557):
        super(_NGUtilAPI, self).__init__()
        
        # API server attributes
        self.ipaddr = ipaddr
        self.port   = port
    
        # Start up the API server
        self._bootstrap()
    
    def _bootstrap(self):
        """
        Bootstrap the API server.
        """
        
        # Socket server
        api_socket = TCPServer((self.ipaddr, self.port), _ServerBase)
            
        # Keep the server running
        api_socket.serve_forever()
    
    