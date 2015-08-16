import json
import shutil
from os import symlink, path, unlink

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
                
            # Restart services
            self.run_command('service nginx reload', shell=True)
            self.feedback.success('Reloaded service \'nginx\'')
            self.run_command('service php-fpm reload', shell=True)
            self.feedback.success('Reloaded service \'php-fpm\'')
              
    def disable(self, params):
        """
        Disable an existing site.
        """
        
        # Target site
        target_site = params.get('fqdn', None)
        
        # Site configurations
        site_config = {
            'available': '/etc/nginx/sites-available/{0}.conf'.format(target_site),
            'enabled': '/etc/nginx/sites-enabled/{0}.conf'.format(target_site)
        }
        
        # If no site selected
        if not target_site:
            self.die('Cannot disable a site without specifying the --fqdn parameter...')
            
        # If the site isn't enabled
        if not path.isfile(site_config['enabled']):
            self.feedback.info('Site already disabled...')
            return True
    
        # Disable the site
        else:
            unlink(site_config['enabled'])
            self.feedback.success('Disabled site \'{0}\''.format(params['fqdn']))
    
            # Restart services
            self.run_command('service nginx reload', shell=True)
            self.feedback.success('Reloaded service \'nginx\'')
            self.run_command('service php-fpm reload', shell=True)
            self.feedback.success('Reloaded service \'php-fpm\'')
                
    def enable(self, params):
        """
        Enable an existing site.
        """
        
        # Target site
        target_site = params.get('fqdn', None)
        
        # Site configurations
        site_config = {
            'available': '/etc/nginx/sites-available/{0}.conf'.format(target_site),
            'enabled': '/etc/nginx/sites-enabled/{0}.conf'.format(target_site)
        }
        
        # If no site selected
        if not target_site:
            self.die('Cannot enable a site without specifying the --fqdn parameter...')
            
        # If the site doesn't exist
        if not path.isfile(site_config['available']):
            self.die('Cannot enable site, NGINX configuration not found. Please use \'create_site\' instead...')
    
        # If the site is already active
        if path.isfile(site_config['enabled']):
            self.feedback.info('Site \'{0}\' already enabled -> {1}'.format(target_site, site_config['enabled']))
            return True
            
        # Activate the site
        symlink(site_config['available'], site_config['enabled'])
        self.feedback.success('Enabled site -> {0}'.format(site_config['enabled']))
    
        # Restart services
        self.run_command('service nginx reload', shell=True)
        self.feedback.success('Reloaded service \'nginx\'')
        self.run_command('service php-fpm reload', shell=True)
        self.feedback.success('Reloaded service \'php-fpm\'')
    
    def _generate_nginx_config(self):
        """
        Generate NGINX config files for the new site.
        """
        
        # Setup the template
        self.template.setup(('NG_HTTPS' if self.ssl['enable'] else 'NG_HTTP'), self.site_config['available'])

        # Update placeholder variables
        self.template.setvars({
            'SITENAME': self.properties['fqdn'],
            'DEFAULTDOC': 'index.php' if not self.properties['default_doc'] else self.properties['default_doc']
        })
    
        # Deploy the configuration
        self.template.deploy(overwrite=True)
        
    def _set_metadata(self):
        """
        Create metadata entry for site.
        """
                
        # Site metadata location
        metadata_dir  = '/root/.ngutil/metadata'
        metadata_site = '{0}/{1}.json'.format(metadata_dir, self.properties['fqdn'])
        
        # Make sure the metadata directory exists
        self.mkdir(self.metadata['dir'])
        
        # Define the site metadata
        metadata_json = {
            'fqdn': self.properties['fqdn'],
            'ssl': self.ssl
        }
        
        # Write the site metadata
        self.mkfile(metadata_site, contents=json.dumps(metadata_json))
        self.feedback.success('Created site metadata -> {0}'.format(metadata_site))
        
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

        # Make sure the site isn't already defined
        if path.isfile(self.site_config['available']):
            self.die('Site \'{0}\' already defined in \'{1}\''.format(params['fqdn'], self.site_config['available']))

        # Merge with site properties
        self.properties = params

    def create(self):
        """
        Create the site definition.
        """
        self._create_dirs()
        self._setup_ssl_certs()
        self._generate_nginx_config()
        self._activate_site()
        self._set_metadata()
        
        # Site created
        self.feedback.block([
            'SITE CREATED:  {0}://{1}'.format('https' if self.ssl['enable'] else 'http', self.properties['fqdn']),
            '> Web Root:    /srv/www/{0}'.format(self.properties['fqdn']),
            '> Default Doc: /srv/www/{0}/{1}'.format(self.properties['fqdn'], 'index.php' if not self.properties['default_doc'] else self.properties['default_doc']),
            '> Logs:        /srv/www/{0}/logs\n'.format(self.properties['fqdn']),
            '> Active:      {0}'.format('Yes -> {0}'.format('/etc/nginx/sites-enabled/{0}.conf'.format(self.properties['fqdn'])) if self.properties['activate'] else 'No'),
            'You can activate the site using: ngutil activate_site --fqdn "{0}"'.format(self.properties['fqdn'])
        ], 'COMPLETE')
