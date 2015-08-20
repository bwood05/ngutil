from ngutil import NGUtil

class _NGUtilAPIRouter(object):
    """
    Route requests to internal methods.
    """
    def __init__(self):
        
        # Request path / method / parameters / action
        self.path   = None
        self.method = None
        self.params = None
        self.action = None
    
    def _call_module(self):
        """
        Call the internal NGUtil module for handling incoming API requests.
        """
        
        # Construct parameters
        self.params['action'] = self.action
        
        # Setup the request
        request = NGUtil(is_cli=False, **self.params)
        
        # Run and return the response
        return request.run()
    
    def route(self, method=None, path=None, params=None):
        """
        Route an incoming API request.
        """
        self.path   = path[1:]
        self.method = method
        self.params = params
        
        # Possible request methods/paths and mapped actions
        requests    = [
            ('GET',  'site',         'list_sites'),
            ('POST', 'site',         'create_site'),
            ('PUT',  'site/enable',  'enable_site'),
            ('PUT',  'site/disable', 'disable_site')
        ]
        
        # Route the incoming request to a method
        found    = False
        response = {}
        for r in requests:
            if r[0] == self.method and r[1] == self.path:
                found       = True
                self.action = r[2]
                break
        
        # If not a valid request path/method
        if not found:
            return {
                'code': 404,
                'body': 'Invalid request'
            }
            
        # Return the response
        else:
            response = self._call_module()
            return {
                'code': response.code,
                'body': response.body
            }