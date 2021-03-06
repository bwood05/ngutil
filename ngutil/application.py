import sys
import wget
import shutil
from os import path, unlink

# RPM module
try: 
    import rpm
except: 
    pass

# NGUtil Libraries
from .service import _NGUtilService
from .common import _NGUtilCommon, _NGUtilSELinux
from .template import _NGUtilTemplates
from .iptables import _NGUtilIPTables

class _NGUtilApp(_NGUtilCommon):
    """
    Class object for handling setting up the NGINX application.
    """
    def __init__(self):
        super(_NGUtilApp, self).__init__()
     
        # Passed arguments
        self.args     = None
     
        # Deployment marker / template manager
        self.marker   = '/root/.ngutil/setup'
        self.template = _NGUtilTemplates()
        
        # Installed packages / additional repositories
        self.packages = ['nginx', 'policycoreutils-python', 'php56u', 'php56u-fpm']
        self.repos    = {
            'epel': {
                'config': '/etc/yum.repos.d/epel.repo',
                'local': '/tmp/epel.rpm',
                'upstream': 'http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm'
            },
            'ius': {
                'config': '/etc/yum.repos.d/ius.repo',
                'local': '/tmp/ius.rpm',
                'upstream': 'https://dl.iuscommunity.org/pub/ius/stable/CentOS/6/x86_64/ius-release-1.0-14.ius.centos6.noarch.rpm'
            }
        }
        
        # Controlled services
        self.service  = {
            'nginx':    _NGUtilService('nginx'),
            'php-fpm':  _NGUtilService('php-fpm')
        }
        
    def _config_firewall(self, rules):
        """
        Setup the firewall for HTTP/HTTPS access
        """
        
        # Create the iptables manager
        iptables = _NGUtilIPTables()
        iptables.select_table('filter')
        
        # Configure each rule
        for rule in rules:
            iptables.select_chain(rule.get('chain', 'INPUT'))
            iptables.add_rule(rule.get('params'))
            
        # Save the iptables config
        iptables.save(restart=True)
        
    def _config_phpfpm(self):
        """
        Configuration steps for PHP-FPM.
        """
        self.mkdir('/etc/php-fpm.d/disabled')
        if path.isfile('/etc/php-fpm.d/www.conf'):
            shutil.move('/etc/php-fpm.d/www.conf', '/etc/php-fpm.d/disabled/www.conf')
        
        # Deploy the default pool configuration
        self.template.setup('FPM', '/etc/php-fpm.d/pool.conf')
        self.template.deploy(overwrite=True)
        
        # Create pool log / session paths
        for dir in ['/srv/www/pool/logs/php-fpm', '/srv/www/pool/session']:
            self.mkdir(dir)
            
        # Enable the port for SELinux
        # self.selinux.add_port(9000, 'tcp', 'http_port_t')
        self.feedback.success('Configured PHP-FPM')
        
    def _config_nginx(self):
        """
        Generate the main NGINX configuration file.
        """
        
        # Get the number of processers
        exit_code, stdout, stderr = self.run_command('grep processor /proc/cpuinfo')
        _WORKERPROCESSES = len(stdout.split('\n'))
        
        # Get system ulimit
        exit_code, stdout, stderr = self.run_command('ulimit -n', shell=True)
        _WORKERCONNECTION = stdout.rstrip()
        
        # Make sure worker connections is a number
        try:
            _WORKERCONNECTION = str(int(_WORKERCONNECTION))
        except:
            _WORKERCONNECTION = '1024'
        
        # Setup the template
        self.template.setup('NG_CONF', '/etc/nginx/nginx.conf')
        self.template.setvars({
            'WORKERPROCESSES':  _WORKERPROCESSES,
            'WORKERCONNECTION': _WORKERCONNECTION
        })
        self.template.deploy(overwrite=True)
        
    def _convert_https(self, config):
        """
        WORKAROUND METHOD
        Convert 'https' to 'http' in repo config
        """
        
        # Read the config
        fh = open(config, 'r')
        _config = fh.read()
        fh.close()
        
        # Change to http
        _fixed = _config.replace('https', 'http')
        
        # Write and close
        fh = open(config, 'w')
        fh.write(_fixed)
        fh.close()
        
    def _bar_none(self, current, total, width=80):
        """
        Supress wget output.
        """
        return False
        
    def _preflight(self):
        """
        Preflight check before running setup.
        """
        
        # SELinux manager
        self.selinux  = _NGUtilSELinux()
        
        # Check if already setup
        if path.isfile(self.marker) and not self.args.get('force', False):
            self.die('Setup has already been run, use the \'-f\' flag to force a re-run...')
        
        # Preflight checks complete
        self.feedback.info('Preparing to setup NGINX...')
        
    def _install(self):
        """
        Make sure NGINX is installed.
        """
        
        # Add the NGINX repository
        nginx_repo = '/etc/yum.repos.d/nginx.repo'
        if not path.isfile(nginx_repo):
            self.feedback.info('Preparing to configure NGINX repository \'{0}\''.format(nginx_repo))
            self.template.setup('NG_REPO', nginx_repo)
            self.template.deploy()
        else:
            self.feedback.info('NGINX repository \'{0}\' already exists, skipping...'.format(nginx_repo))
        
        # Download / install each repo
        for repo, attrs in self.repos.iteritems():
            
            # Only install if the repo configuration hasn't been created
            if not path.isfile(attrs['config']):
                wget.download(attrs['upstream'], out=attrs['local'], bar=self._bar_none)
                self.feedback.success('Fetched repository package: {0} -> {1}'.format(attrs['upstream'], attrs['local']))
            
                # Install the repository RPM
                self.run_command('rpm -Uvh {0}'.format(attrs['local']))
                self.feedback.success('Installed repository package: {0}'.format(attrs['local']))
        
                # WORKAROUND
                # Can't access 'https' mirrors, so convert to 'http'
                self._convert_https(attrs['config'])
        
                # Clean up the tmp package
                unlink(attrs['local'])
            else:
                self.feedback.info('Repo provided by \'{0}\' already installed...'.format(attrs['upstream']))
    
        # Compile packages that need to be installed  
        ts        = rpm.TransactionSet()
        _packages = []
        for pkg in self.packages:
            pkg_obj = ts.dbMatch('name', pkg)
            if pkg_obj.count() == 0:
                _packages.append(pkg)
                self.feedback.info('Marking package \'{0}\' for installation...'.format(pkg))
            else:
                self.feedback.info('Package \'{0}\' already installed, skipping...'.format(pkg))
        
        # If installing any packages
        if _packages:
            self.feedback.info('Preparing to install packages: {0}'.format(' '.join(_packages)))
            
            # Install the packages
            self.run_command('yum install {0} -y'.format(' '.join(_packages)), stdout=sys.stdout, stderr=sys.stderr)
            self.feedback.success('Installed all packages!')
        else:
            self.feedback.info('All packages already installed...')
            
        # Enable the services
        self.service['nginx'].enable()
        self.service['php-fpm'].enable()
        
        # Make any required directories
        for dir in [
            '/etc/nginx/sites-available',
            '/etc/nginx/sites-enabled',
            '/srv/www'
        ]:
            self.mkdir(dir)
            
        # Configure NGINX and PHP-FPM
        self._config_nginx()
        self._config_phpfpm()
        
        # Start the services
        self.service['php-fpm'].restart()
        self.service['nginx'].restart()
        
        # Create the setup marker
        self.mkfile(self.marker, contents='1', overwrite=True)
        
    def setup(self, args):
        """
        Launch the setup wizard for NGINX/PHP-FPM
        """
        
        # Store arguments
        self.args = args
        
        # Preflight checks
        self._preflight()
        
        # Setup the firewall
        self._config_firewall([
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
        
        # Install required software
        self._install()