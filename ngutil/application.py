import sys
import iptc
import wget
import shutil
from os import path, unlink

# NGUtil Libraries
from .common import _NGUtilCommon
from .template import _NGUtilTemplates

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
        
        # Template manager
        self.template = _NGUtilTemplates()
        
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
                self.feedback.success('Appended rule to chain \'{0}\': proto={1}, state={2}, dport={3}, target={4}'.format(
                    new_rule.get('chain'),
                    new_rule.get('proto'),
                    new_rule.get('state'),
                    str(new_rule.get('dport')),
                    new_rule.get('target')
                ))
            else:
                self.feedback.info('Firewall rule matching port {0} exists, skipping...'.format(str(new_rule.get('dport'))))
                
        # Save the iptables config
        self._iptables_save()
        
    def _config_phpfpm(self):
        """
        Configuration steps for PHP-FPM.
        """
        self.mkdir('/etc/php-fpm.d/disabled')
        shutil.move('/etc/php-fpm.d/www.conf', '/etc/php-fpm.d/disabled/www.conf')
        self.feedback.success('Configured PHP-FPM')
        
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
        
        # Packages to install
        packages = ['nginx', 'policycoreutils-python', 'php56u']
        self.feedback.info('Preparing to install packages: {0}'.format(' '.join(packages)))
        
        # Install the packages
        self.run_command('yum install {0} -y'.format(' '.join(packages)), stdout=sys.stdout, stderr=sys.stderr)
        self.feedback.success('Installed all packages!')
            
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