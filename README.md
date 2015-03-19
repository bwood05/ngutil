# ngutil
Scripts to help install and configure sites with nginx and php-fpm.

These scripts were written on and for CentOS 6.6. They make a lot of assumptions so use at your own risk.

#create_site.sh options
 -n (required)
 
 FQDN of the site to be created e.g. subdomain.domain.tld.

 -a (optional)
 
 Actives the site by creating a symlink from sites-available to sites-enabled.

 -d (optional)
 
 Sets the decault document for the site.

 -s (optional)
 
 configures the site to use SSL -K and -C are required with this option.

 -C (required if -s is specified)
 
 location of the SSL certificate for the site.

 -K (required if -s is specified)
 
 location of the SSL key for the site.

Examples

```sh create_site.sh -n subdomain.domain.tld```
Creates the nginx and php-fpm config files for subdomain.domain.tld, but leaves it inactive.

```sh create_site.sh -n subdomain.domain.tld -d index.php```
Creates the nginx and php-fpm config files for subdomain.domain.tld, leaves it inactive, and sets the default document to index.php.

```sh create_site.sh -n subdomain.domain.tld -a```
Creates the nginx and php-fpm config files for subdomain.domain.tld and activates it.

```sh create_site.sh -n subdomain.domain.tld -s -C ~\cert.crt -K ~\key.key```
Creates the nginx and php-fpm config files for subdomain.domain.tld
