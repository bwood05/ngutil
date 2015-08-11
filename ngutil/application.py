import iptc
import wget
import shutil
from os import path
from yum import YumBase
from subprocess import Popen, PIPE

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
        
    def _chkconfig(self, service, state='on')
        """
        Enable the service in chkconfig.
        """
        proc = Popen(['chkconfig', service, state], stdout=PIPE, stderr=PIPE)
        proc.communicate()
        
    def _mkdir(self, dir):
        """
        Make directory if it doesn't exist.
        """
        if not path.isdir(dir):
            makedirs(dir)
        
    def config_firewall(self, ports=(80, 443)):
        """
        Setup the firewall for HTTP/HTTPS access
        """
        
        # Load the firewall table and select the INPUT chain
        table = iptc.Table(iptc.Table.FILTER)
        chain = iptc.Chain(table, "INPUT")
        
        # Check if the rule already exists
        for rule in chain.rules:
            print rule
        
    def _config_phpfpm(self):
        """
        Configuration steps for PHP-FPM.
        """
        self._mkdir('/etc/php-fpm.d/disabled')
        shutil.move('/etc/php-fpm.d/www.conf', '/etc/php-fpm.d/disabled/www.conf')
        
    def _config_nginx(self):
        """
        Generate the main NGINX configuration file.
        """
        
        # Get the number of processers
        wp_proc = Popen(['grep', 'processor', '/proc/cpuinfo'], stdout=PIPE)
        wp_proc.communicate()
        _WORKERPROCESSES = len(wp_proc.stdout.readlines())
        
        # Get system ulimit
        wc_proc = Popen('ulimit', '-n', shell=True, stdout=PIPE)
        wc_proc.communicate()
        _WORKERCONNECTION = wc_proc.stdout.readlines()[0].rstrip()
        
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
                proc = Popen(['rpm', '-Uvh', attrs['local']], stdout=PIPE, stderr=PIPE)
                
                # Make sure installation was successfull
                if proc.return_code != 0:
                    self.die('Failed to install \'{}\' repository: {}'.format(repo, proc.stderr.readlines()))
        
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
            self._mkdir(dir)