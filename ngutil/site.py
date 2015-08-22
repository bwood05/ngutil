from __future__ import print_function
import json
import shutil
from os import symlink, path, unlink, listdir

# ngutil
from ngutil.service import _NGUtilService
from ngutil.template import _NGUtilTemplates
from ngutil.common import _NGUtilCommon, _NGUtilSELinux, R_OBJECT, R_FATAL

class _NGUtilSite(_NGUtilCommon):
    """
    Class object for managing NGINX site definitions.
    """
    def __init__(self):
        super(_NGUtilSite, self).__init__()

        # Template manager
        self.template = _NGUtilTemplates()

        # Store arguments
        self._args    = None

        # SSL attributes
        self.ssl  = {
            'enable': False,
            'cert': None,
            'key': None
        }

        # Site properties / metadata
        self.properties = {}
        self.metadata   = None

        # Required / optional params
        self.params = {
            'required': ['fqdn'],
            'optional': ['default_doc', 'activate', 'ssl', 'ssl_cert', 'ssl_key']
        }
        
        # Service handlers
        self.service = {
            'nginx':   _NGUtilService('nginx')
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

        # Return a response object
        return R_OBJECT(msg='OK', code=200)

    def _get_source(self):
        """
        Retrieve source code to put in the document root.
        """
        if self.properties['source']:

            # Remote protocols
            remote_proto = ['http', 'https', 'ftp']

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
    
        # Return a response object
        return R_OBJECT(msg='OK', code=200)
    
    def _activate_site(self):
        """
        Optionally activate the site.
        """
        if self.properties.get('activate'):
            if not path.isfile(self.site_config['enabled']):
                symlink(self.site_config['available'], self.site_config['enabled'])
                self.feedback.success('Activated site -> {0}'.format(self.site_config['enabled']))
            else:
                self.feedback.info('Site already activated -> {0}'.format(self.site_config['enabled']))
                
            # Restart services
            self.service['nginx'].restart()
        
        # Return a response object
        return R_OBJECT(msg='OK', code=200)
             
    def list_all(self):
        """
        List all managed sites with metdata.
        """
        
        # Metadata directory
        metadata_dir = '/root/.ngutil/metadata'
        
        # If no metadata exists
        if not path.isdir(metadata_dir) or listdir(metadata_dir) == []:
            return R_FATAL(
                msg  = 'No site metadata defined...',
                code = 404
            )
        
        # Response JSON data
        response_json = []
        
        # Process each metadata file
        for file in listdir(metadata_dir):
            print('')
            if file.endswith('.json'):
                fh = open('{0}/{1}'.format(metadata_dir, file), 'r')
                metadata = json.loads(fh.read())
                fh.close()
                
                # Append to response JSON object
                response_json.append(metadata)
                
                # Site status
                if path.isfile(metadata['config']['enabled']):
                    site_status = 'Yes -> {0}'.format(metadata['config']['enabled'])
                else:
                    site_status = 'No'
                
                # Display the metadata
                print('SITE: {0}'.format(metadata['fqdn']))
                print('> DocRoot: /srv/www/{0}'.format(metadata['fqdn']))
                print('> Config: {0}'.format(metadata['config']['available']))
                print('> Enabled: {0}'.format(site_status))
                print('> SSL Enabled: {0}'.format('Yes' if metadata['ssl']['enable'] else 'No'))
                
                # SSL information
                if metadata['ssl']['enable']:
                    print('> SSL Certificate: {0}'.format(metadata['ssl']['cert']))
                    print('> SSL Key: {0}'.format(metadata['ssl']['key']))
                    
                print('')
                
        # Return a response object
        return R_OBJECT(
            msg  = response_json,
            code = 200
        )
              
    def disable(self, params):
        """
        Disable an existing site.
        """
        self._args = params
        
        # Target site
        target_site = params.get('fqdn', None)
        
        # Site configurations
        site_config = {
            'available': '/etc/nginx/sites-available/{0}.conf'.format(target_site),
            'enabled': '/etc/nginx/sites-enabled/{0}.conf'.format(target_site)
        }
        
        # If no site selected
        if not target_site:
            return R_FATAL(
                msg  = 'Cannot disable a site without specifying the --fqdn parameter...',
                code = 400
            )
            
        # If the site isn't enabled
        if not path.isfile(site_config['enabled']):
            return R_OBJECT(msg = self.feedback.info('Site already disabled...'))
    
        # Disable the site
        else:
            unlink(site_config['enabled'])
    
            # Restart services
            self.service['nginx'].restart()
            
            # Update the site metadata
            self._update_metadata({'active': False})
            
            # Return a response object
            return R_OBJECT(msg = self.feedback.success('Disabled site \'{0}\''.format(params['fqdn'])))
                
    def enable(self, params):
        """
        Enable an existing site.
        """
        self._args = params
        
        # Target site
        target_site = params.get('fqdn', None)
        
        # Site configurations
        site_config = {
            'available': '/etc/nginx/sites-available/{0}.conf'.format(target_site),
            'enabled': '/etc/nginx/sites-enabled/{0}.conf'.format(target_site)
        }
        
        # If no site selected
        if not target_site:
            return R_FATAL(
                msg  = 'Cannot enable a site without specifying the --fqdn parameter...',
                code = 400
            )
            
        # If the site doesn't exist
        if not path.isfile(site_config['available']):
            return R_FATAL(
                msg  = 'Cannot enable site, NGINX configuration not found. Please use \'create_site\' instead...',
                code = 400
            )
    
        # If the site is already active
        if path.isfile(site_config['enabled']):
            return R_OBJECT(msg = self.feedback.info('Site \'{0}\' already enabled -> {1}'.format(target_site, site_config['enabled'])))
            
        # Activate the site
        symlink(site_config['available'], site_config['enabled'])
    
        # Restart services
        self.service['nginx'].restart()
        
        # Update the site metadata
        self._update_metadata({'active': True})
        
        # Return a response object
        return R_OBJECT(msg = self.feedback.success('Enabled site -> {0}'.format(site_config['enabled'])))
    
    def _generate_nginx_config(self):
        """
        Generate NGINX config files for the new site.
        """
        
        # Setup the template
        self.template.setup(('NG_HTTPS' if self.ssl['enable'] else 'NG_HTTP'), self.site_config['available'])

        # Update placeholder variables
        self.template.setvars({
            'SITENAME': self.properties['fqdn'],
            'DEFAULTDOC': 'index.php' if not (self.properties.get('default_doc')) else self.properties['default_doc']
        })
    
        # Deploy the configuration
        self.template.deploy(overwrite=True)
        
        # Return a response object
        return R_OBJECT()
        
    def _update_metadata(self, values):
        """
        Update a site's metadata.
        """
        
         # Site metadata location
        metadata_dir  = '/root/.ngutil/metadata'
        metadata_site = '{0}/{1}.json'.format(metadata_dir, self._args['fqdn'])
        
        # Open and read the metadata
        metadata_json = None
        with open(metadata_site, 'r') as file:
            metadata_json = json.loads(file.read())
        
        # Update any metadata
        for k,v in values.iteritems():
            metadata_json[k] = v
            self.feedback.success('Updated site \'{0}\' metadata: key={1}, value={2}'.format(self._args['fqdn'], k, str(v)))
            
        # Write out the updated metadata
        with open(metadata_site, 'w') as file:
            file.write(json.dumps(metadata_json))
        
    def _set_metadata(self):
        """
        Create metadata entry for site.
        """
                
        # Site metadata location
        metadata_dir  = '/root/.ngutil/metadata'
        metadata_site = '{0}/{1}.json'.format(metadata_dir, self.properties['fqdn'])
        
        # Make sure the metadata directory exists
        self.mkdir(metadata_dir)
        
        # Define the site metadata
        metadata_json = {
            'fqdn': self.properties['fqdn'],
            'config': {
                'available': '/etc/nginx/sites-available/{0}.conf'.format(self.properties['fqdn']),
                'enabled': '/etc/nginx/sites-enabled/{0}.conf'.format(self.properties['fqdn'])           
            },
            'active': self.properties.get('activate', False),
            'ssl': self.ssl,
            'doc_root': '/srv/www/{0}'.format(self.properties['fqdn']),
            'default_doc': 'index.php' if not (self.properties.get('default_doc')) else self.properties['default_doc']
        }
        
        # Write the site metadata
        self.mkfile(metadata_site, contents=json.dumps(metadata_json))
        self.feedback.success('Created site metadata -> {0}'.format(metadata_site))
        
        # Store the site metadata
        self.metadata = metadata_json
        
        # Return a response object
        return R_OBJECT()
        
    def _define(self):
        """
        Define attributes for creating a new site definition.
        """

        # SELinux manager
        self.selinux  = _NGUtilSELinux()

        # Make sure all required arguments are set
        for k in self.params['required']:
            if not self._args.get(k):
                return R_FATAL(
                    msg  = 'Missing required argument \'{0}\''.format(k),
                    code = 400
                )

        # If using SSL
        if self._args.get('ssl'):
            self.ssl['enable'] = True

            # Make sure the certificate and key are set
            for k in ['ssl_cert', 'ssl_key']:
                if not self._args.get(k):
                    return R_FATAL(
                        msg  = 'Missing required argument \'{0}\', must supply to enable SSL'.format(k),
                        code = 400
                    )

                # Make sure the file exists
                ssl_file = self._args.get(k)
                if not os.path.isfile(ssl_file):
                    return R_FATAL(
                        msg  = 'Could not locate \'{0}\' file \'{1}\''.format(k, ssl_file),
                        code = 400
                    )

            # Set the SSL key and certificate
            self.ssl['key'] = self._args.get('ssl_key')
            self.ssl['cert'] = self._args.get('ssl_cert')
            self.feedback.info('Using SSL for site \'{0}\': cert={1}, key={2}'.format(self._args['fqdn'], self._args['ssl_cert'], self._args['ssl_key']))
        else:
            self.feedback.info('Not using SSL for site \'{0}\''.format(self._args['fqdn']))
            
        # Site configuration
        self.site_config = {
            'available': '/etc/nginx/sites-available/{0}.conf'.format(self._args['fqdn']),
            'enabled': '/etc/nginx/sites-enabled/{0}.conf'.format(self._args['fqdn'])
        }

        # Make sure the site isn't already defined
        if path.isfile(self.site_config['available']):
            return R_FATAL(
                msg  = 'Site \'{0}\' already defined in \'{1}\''.format(self._args['fqdn'], self.site_config['available']),
                code = 400
            )

        # Merge with site properties
        self.properties = self._args
        
        # Return a response object
        return R_OBJECT()

    def create(self, args):
        """
        Create the site definition.
        """
        self.feedback.info('Preparing to setup NGINX site')
        
        # Store arguments
        self._args = args
        
        # Run internal methods
        for im in [
            self._define,
            self._create_dirs,
            self._setup_ssl_certs,
            self._generate_nginx_config,
            self._activate_site,
            self._set_metadata
        ]:
        
            # Get the response for internal method
            im_rsp = im()
            
            # Look for a fatal response
            if im_rsp.fatal:
                return im_rsp
        
        # Site created
        self.feedback.block([
            'SITE CREATED:  {0}://{1}'.format('https' if self.ssl['enable'] else 'http', self.properties['fqdn']),
            '> Web Root:    /srv/www/{0}'.format(self.properties['fqdn']),
            '> Default Doc: /srv/www/{0}/{1}'.format(self.properties['fqdn'], 'index.php' if not self.properties.get('default_doc') else self.properties['default_doc']),
            '> Logs:        /srv/www/{0}/logs'.format(self.properties['fqdn']),
            '> Active:      {0}\n'.format('Yes -> {0}'.format('/etc/nginx/sites-enabled/{0}.conf'.format(self.properties['fqdn'])) if self.properties.get('activate') else 'No'),
            'You can activate the site using: ngutil enable_site --fqdn "{0}"'.format(self.properties['fqdn'])
        ], 'COMPLETE')

        # Return a response object
        return R_OBJECT(msg = self.metadata)