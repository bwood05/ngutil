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

### Basic Usage
```sh

# Setup NGINX
$ ngutil setup

# Force reconfiguration of NGINX
$ ngutil setup -f

# Create a plain HTTP site
$ ngutil create_site -n "some.site.com"

# Create an HTTPS with a custom default document and activate
$ ngutil create_site -n "some.site.com" -d "index.html" \
> -s -a -K "/path/to/ssl.key" -C "/path/to/ssl.crt"

# List all managed sites
$ ngutil list_sites

# Activate a managed site. This creates a symlink to '/etc/nginx/sites-enabled'
$ ngutil enable_site -n "some.site.com"

# Deactivate a managed site. This removes the symlink in '/etc/nginx/sites-enabled'
$ ngutil disable_site -n "some.site.com"

```