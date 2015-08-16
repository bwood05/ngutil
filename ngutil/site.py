import shutil
from os import symlink

# ngutil
from .template import _NGUtilTemplates
from .common import _NGUtilCommon, _NGUtilSELinux

class _NGUtilSite(_NGUtilCommon):
    """
    Class object for managing NGINX site definitions.
    """
    def __init__(self):
        super(_NGUtilSite, self).__init__()

        # Template manager
        self.template = _NGUtilTemplates()

        # SSL attributes
        self.ssl  = {
            'enable': False,
            'cert': None,
            'key': None
        }

        # Site properties
        self.properties = {}

        # Required / optional params
        self.params = {
            'required': ['fqdn'],
            'optional': ['default_doc', 'activate', 'ssl', 'ssl_cert', 'ssl_key']
        }

    def _setup_ssl_certs(self):
        """
        Setup SSL certificates if enabled.
        """
        if self.ssl['enable']:
            _sitename = self.properties['fqdn']
            _cert_dst = '/srv/www/{0}/ssl/{1}.crt'.format(_sitename)
            _key_dst  = '/srv/www/{0}/ssl/{1}.key'.format(_sitename)

            # Deploy the SSL certificate
            shutil.copy(self.properties['ssl_cert'], _cert_dst)
            self.feedback.success('Deployed SSL certificate -> {0}'.format(_cert_dst))

            # Deploy the SSL key
            shutil.copy(self.properties['ssl_key'], _key_dst)
            self.feedback.success('Deployed SSL key -> {0}'.format(_key_dst))

    def _create_dirs(self):
        """
        Create any required site directories.
        """

        # Site base directory
        site_base = '/srv/www/{0}'.format(self.properties['fqdn'])

        for dir in [
            '{0}/logs/php-fpm',
            '{0}/public',
            '{0}/session'
        ]:
            self.mkdir(dir.format(site_base))

        # If using SSL
        if self.ssl['enable']:
            self.mkdir('{0}/ssl'.format(site_base))

        # Setup directory permissions
        self.run_command('chown -R root:nginx {0}'.format(site_base))
        self.run_command('chmod -R 750 {0}'.format(site_base))

        # Set SELinux context
        self.selinux.chcon(site_base, 'unconfined_u:object_r:httpd_sys_content_t:s0', recursive=True)
    
    def _activate_site(self):
        """
        Optionally activate the site.
        """
        if self.properties['activate']:
            if not path.isfile(self.site_config['enabled']):
                symlink(self.site_config['available'], self.site_config['enabled'])
                self.feedback.success('Activated site -> {0}'.format(self.site_config['enabled']))
            else:
                self.feedback.info('Site already activated -> {0}'.format(self.site_config['enabled']))
    
    def _generate_nginx_config(self):
        """
        Generate NGINX config files for the new site.
        """
        
        # Setup the template
        self.template.setup(('NG_HTTPS' if self.ssl['enable'] else 'NG_HTTP'), self.site_config['available'])

        # Update placeholder variables
        self.template.setvars({
            'SITENAME': self.properties['fqdn'],
            'DEFAULTDOC': self.properties.get('default_doc', 'index.php')
        })
    
        # Deploy the configuration
        self.template.deploy(overwrite=True)
        
    def define(self, params):
        """
        Define attributes for creating a new site definition.
        """

        # SELinux manager
        self.selinux  = _NGUtilSELinux()

        # Make sure all required arguments are set
        for k in self.params['required']:
            if not params.get(k):
                self.die('Missing required argument \'{0}\''.format(k))

        # If using SSL
        if params.get('ssl'):
            self.ssl['enable'] = True

            # Make sure the certificate and key are set
            for k in ['ssl_cert', 'ssl_key']:
                if not params.get(k):
                    self.die('Missing required argument \'{0}\', must supply to enable SSL'.format(k))

                # Make sure the file exists
                ssl_file = params.get(k)
                if not os.path.isfile(ssl_file):
                    self.die('Could not locate \'{0}\' file \'{1}\''.format(k, ssl_file))

            # Set the SSL key and certificate
            self.ssl['key'] = params.get('ssl_key')
            self.ssl['cert'] = params.args.get('ssl_cert')
            self.feedback.info('Using SSL for site \'{0}\': cert={1}, key={2}'.format(params['fqdn'], params['ssl_cert'], param['ssl_key']))
        else:
            self.feedback.info('Not using SSL for site \'{0}\''.format(params['fqdn']))
            
        # Site configuration
        self.site_config = {
            'available': '/etc/nginx/sites-available/{0}.conf'.format(params['fqdn']),
            'enabled': '/etc/nginx/sites-enabled/{0}.conf'.format(params['fqdn'])
        }

        # Merge with site properties
        self.properties = params

    def create(self):
        """
        Create the site definition.
        """
        self._create_dirs()
        self._setup_ssl_certs()
        self._generate_nginx_config()
        
        # Site created
        self.feedback.block([
            '\'{0}\' configuration complete!'.format(self.properties['fqdn']),
            'You will need to restart NGINX/PHP-FPM to make the site available:',
            '> service nginx restart',
            '> service php-fpm restart'
        ], 'COMPLETE')
