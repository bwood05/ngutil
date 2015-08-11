import iptc
from yum import YumBase

# NGUtil Libraries
from .common import _NGUtilCommon
from .template import _NGUtilTemplates

class _NGUtilApp(_NGUtilCommon):
    """
    Class object for handling setting up the NGINX application.
    """
    def __init__(self):
        super(_NGUtilApp, self).__init__()
        
        # Template manager
        self.template = _NGUtilTemplates()
        
        # YUM package manager
        self.yum = YumBase()
        
    def firewall(self, port=80):
        """
        Setup the firewall for HTTP/HTTPS access
        """
        
        # Load the firewall table and select the INPUT chain
        table = iptc.Table(iptc.Table.FILTER)
        chain = iptc.Chain(table, "INPUT")
        
        # Check if the rule already exists
        for rule in chain.rules:
            print rule
        
    def install(self):
        """
        Make sure NGINX is installed.
        """
        
        # Search list / package name
        searchlist = ['name']
        arg        = ['nginx', 'policycoreutils-python']
        
        # Look for the package
        for (package, matched_value) in self.yum.searchGenerator(searchlist, arg):
            self.yum.install(package)
                
            # Complete the installation
            self.yum.buildTransaction()
            self.yum.processTransaction()