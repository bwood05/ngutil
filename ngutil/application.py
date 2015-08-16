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
from .common import _NGUtilCommon, _NGUtilSELinux
from .template import _NGUtilTemplates
from .iptables import _NGUtilIPTables

class _NGUtilApp(_NGUtilCommon):
    """
    Class object for handling setting up the NGINX application.
    """
    
    # Additional repositories
    REPOS = {
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
    
    def __init__(self):
        super(_NGUtilApp, self).__init__()
     
        # Deployment marker
        self.marker   = '{0}/setup'.format(self._DATA)
        
        # Template manager
        self.template = _NGUtilTemplates()
        
        # SELinux manager
        self.selinux  = _NGUtilSELinux()
        
        # Installed packages
        self.packages = ['nginx', 'policycoreutils-python', 'php56u', 'php56u-fpm']
        
    def _chkconfig(self, service, state='on'):
        """
        Enable the service in chkconfig.
        """
        self.run_command('chkconfig {0} {1}'.format(service, state))
        self.feedback.success('Enabled service {0} -> {1}'.format(service, state))
        
    def _iptables_save(self, restart=True):
        """
        Save and optionally restart iptables.
        """
        
        # Save the iptables config
        self.run_command('service iptables save')
        self.feedback.success('Saved iptables rules...')
            
        # If restarting
        if restart:
            self.run_command('service iptables restart')
            self.feedback.success('Restarted iptables service...')
        
    def config_firewall(self, rules):
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
        self.selinux.add_port(9000, 'tcp', 'http_port_t')
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
        
    def preflight(self):
        """
        Preflight check before running setup.
        """
        if path.isfile(self.marker):
            self.die('Setup has already been run, use the \'-f\' flag to force a re-run...')
        
        # Preflight checks complete
        self.feedback.info('Preparing to setup NGINX...')
        
    def install(self):
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
        for repo, attrs in self.REPOS.iteritems():
            
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
        self._chkconfig('nginx')
        self._chkconfig('php-fpm')
        
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
        self.run_command('service php-fpm start', shell=True)
        self.feedback.success('Started \'php-fpm\' service')
        
        # Create the setup marker
        mh = open(self.MARKER, 'w')
        mh.write('1')
        mh.close()