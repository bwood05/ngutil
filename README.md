# Nginx Configuration Utility
A Python module/command line utility to assist in setting up Nginx and configuring sites. Currently this utility is only supported on CentOS 6.x. Use at your own risk.

### Installation
Installation requires an appropriate version of 'python-setuptools' and 'python-pip' for processing dependencies.
```sh
$ sudo yum install python-pip python-setuptools
$ git clone -b python-dev https://github.com/bwood05/ngutil
$ cd ngutil
$ python setup.py install
```

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
