import iptc
import wget
import shutil
from os import path
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
        
    def _chkconfig(self, service, state='on'):
        """
        Enable the service in chkconfig.
        """
        self.run_command('chkconfig {} {}'.format(service, state))
        
    def _iptables_save(self, restart=True):
        """
        Save and optionally restart iptables.
        """
        
        # Save the iptables config
        self.run_command('service iptables save')
            
        # If restarting
        if restart:
            self.run_command('service iptables restart')
        
    def config_firewall(self, rules):
        """
        Setup the firewall for HTTP/HTTPS access
        """
        
        # Configure each rule
        for new_rule in rules:
            
            # Target chain / config flag
            chain  = iptc.Chain(iptc.Table(iptc.Table.FILTER), new_rule.get('chain', 'INPUT'))  
            config = True
            
            # Look at existing rules
            for rule in chain.rules:
                for match in rule.matches:
                    
                    # Port already configured
                    if int(match.dport) == new_rule.dport:
                        config = False
                        
            # If configuring the new rule
            if config:
                
                # Setup the firewall rule
                rule          = iptc.Rule()
                rule.protocol = new_rule.get('proto')
                rule.target   = iptc.Target(rule, new_rule.get('target'))
                
                # Define rule match parameters
                match         = iptc.Match(rule, "state")
                match.state   = new_rule.get('state')
                match.dport   = str(new_rule.get('dport'))
                
                # Add match parameters and append to chain
                rule.add_match(match)
                chain.insert_rule(rule)
                
        # Save the iptables config
        self._iptables_save()
        
    def _config_phpfpm(self):
        """
        Configuration steps for PHP-FPM.
        """
        self.mkdir('/etc/php-fpm.d/disabled')
        shutil.move('/etc/php-fpm.d/www.conf', '/etc/php-fpm.d/disabled/www.conf')
        
    def _config_nginx(self):
        """
        Generate the main NGINX configuration file.
        """
        
        # Get the number of processers
        exit_code, stdout, stderr = self.run_command('grep processor /proc/cpuinfo')
        _WORKERPROCESSES = len(stdout.readlines())
        
        # Get system ulimit
        exit_code, stdout, stderr = self.run_command('ulimit -n', shell=True)
        _WORKERCONNECTION = stdout.readlines()[0].rstrip()
        
        # Setup the template
        self.template.setup('NG_CONFIG', '/etc/nginx/nginx.conf')
        self.template.setvars(
            WORKERPROCESSES =  _WORKERPROCESSES,
            WORKERCONNECTION = _WORKERCONNECTION
        )
        self.template.deploy()
        
    def install(self):
        """
        Make sure NGINX is installed.
        """
        
        # Add the NGINX repository
        nginx_repo = '/etc/yum.repos.d/nginx.repo'
        if not path.isfile(nginx_repo):
            repo = self.template.setup('NG_REPO', nginx_repo)
            repo.deploy()
        
        # Download / install each repo
        for repo, attrs in {
            'epel': {
                'config': '/etc/yum.repos.d/epel.repo',
                'local': '/tmp/epel.rpm',
                'upstream': 'http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm'
            },
            'ius': {
                'config': '/etc/yum.repos.d/ius.repo'
                'local': '/tmp/ius.rpm',
                'upstream': 'http://dl.iuscommunity.org/pub/ius/stable/CentOS/6/x86_64/ius-release-1.0-13.ius.centos6.noarch.rpm'
            }
        }.iteritems():
            
            # Only install if the repo configuration hasn't been created
            if not path.isfile(attrs['config']):
                wget.download(attrs['upstream'], out=attrs['local'])
            
                # Install the repository RPM
                self.run_command('rpm -Uvh {}'.format(attrs['local']))
        
        # Search list / package name
        searchlist = ['name']
        arg        = ['nginx', 'policycoreutils-python', 'php56u']
        
        # Look for the package
        for (package, matched_value) in self.yum.searchGenerator(searchlist, arg):
            self.yum.install(package)
                
        # Complete the installation
        self.yum.buildTransaction()
        self.yum.processTransaction()
            
        # Enable the services
        self.chkconfig('nginx')
        self.chkconfig('php-fpm')
        
        # Make any required directories
        for dir in [
            '/etc/nginx/sites-available',
            '/etc/nginx/sites-enabled',
            '/srv/www'
        ]:
            self.mkdir(dir)