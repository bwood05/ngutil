#!/bin/bash

#Options
# -n (required)
# FQDN of the site to be created e.g. subdomain.domain.tld
#
# -a (optional)
# Actives the site by creating a symlink from sites-available to sites-enabled
#
# -d (optional)
# Sets the decault document for the site
#
# -s (optional)
# configures the site to use SSL -K and -C are required with this option
#
# -C (required if -s is specified)
# location of the SSL certificate for the site
#
# -K (required if -s is specified)
# location of the SSL key for the site

. /etc/init.d/functions

#Default settings
SSL=false
ACTIVATE=false
DEFAULTDOC="index.php"
ERROR=""

while getopts "an:sC:K:d:" opt; do
	case $opt in
	  	a)
			ACTIVATE=true
			;;
	    n) 
			SITENAME="$OPTARG"
	    	;;
	    s) 
			SSL=true
			;;
		C)
			CERTPATH="$OPTARG"
			;;
		K)
			KEYPATH="$OPTARG"
			;;
		d)
			DEFAULTDOC="$OPTARG"
			;;
	    \?) 
			echo "Invalid option -$OPTARG" >&2
			exit 1
	    	;;
	    :)
			echo "Option -$OPTARG requires an argument." >&2
			exit 1
			;;
	esac
done

check_options() {
	if [ "$SITENAME" = "" ]; then
		ERROR="ERROR: Must define sitename. e.g. subdomain.domain.tld"
		return 1
		#exit 1
	fi
	if [ "$SSL" = true -a "$CERTPATH" = "" ]; then
		ERROR="ERROR: -C option required with -s option"
		return 1
		#exit 1
	fi
	if [ "$SSL" = true -a "$KEYPATH" = "" ]; then
		ERROR="ERROR: -K option required with -s option"
		return 1
		#exit 1
	fi
	return 0
}

generate_nginx_config() {
	if [ "$SSL" = true ]; then
		SITECONFIG="
server {
	listen          80;
	server_name     $SITENAME;
	return			301 https://\$server_name\$request_uri;
}
server {
    listen			443 ssl spdy;
    server_name		$SITENAME;
    add_header 		Strict-Transport-Security \"max-age=31536000; includeSubdomains\";
    access_log      /srv/www/$SITENAME/logs/access.log;
    error_log       /srv/www/$SITENAME/logs/error.log;
    root            /srv/www/$SITENAME/public;

    ssl_certificate            /srv/www/$SITENAME/ssl/$SITENAME.crt;
    ssl_certificate_key        /srv/www/$SITENAME/ssl/$SITENAME.key;
    ssl_ciphers 'AES128+EECDH:AES128+EDH:!aNULL';
    ssl_protocols              TLSv1 TLSv1.1 TLSv1.2;
    ssl_session_cache          shared:SSLCACHE:50m;
    ssl_prefer_server_ciphers  on;
    
    keepalive_timeout          70;
    ssl_session_timeout        5m;

    location ~* \.(jpg|jpeg|gif|png|js|ico|xml|css)$ {
    	server_tokens 	off;
        access_log      off;
        log_not_found   off;
        expires         360d;
    }

    location / {
    	server_tokens 	off;
        index 			$DEFAULTDOC;
    }

    location ~ \.php$ {
    	server_tokens 	off;
        include        /etc/nginx/fastcgi_params;
        fastcgi_pass   127.0.0.1:$PORT;
        fastcgi_index  index.php;
        fastcgi_param  SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
    }
}"
	else
		SITECONFIG="server {
	listen          80;
	server_name     $SITENAME;
	access_log      /srv/www/$SITENAME/logs/access.log;
	error_log       /srv/www/$SITENAME/logs/error.log;
	root            /srv/www/$SITENAME/public_html;

	location ~* \.(jpg|jpeg|gif|png|js|ico|xml|css)$ {
		server_tokens 	off;
	    access_log      off;
	    log_not_found   off;
	    expires         360d;
	}

	location / {
		server_tokens 	off;
	    index 			$DEFAULTDOC;
	}

	location ~ \.php$ {
		server_tokens 	off;
	    include         /etc/nginx/fastcgi_params;
	    fastcgi_pass    127.0.0.1:$PORT;
	    fastcgi_index	index.php;
	    fastcgi_param   SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
	}

	location ~ /\. {
		server_tokens 	off;
	    access_log      off;
	    log_not_found   off;
	    deny            all;
	}
}"
	fi
	return 0
}

configure_for_ssl() {
	if [ "$SSL" = true ]; then
		if [ ! -d /srv/www/$SITENAME/ssl ]; then
			mkdir /srv/www/$SITENAME/ssl
			if [ $? -ne 0 ]; then
				return 1
			fi
		fi
		cp $CERTPATH "/srv/www/$SITENAME/ssl/$SITENAME.crt"
		if [ $? -ne 0 ]; then
			return 1
		fi
		cp $KEYPATH "/srv/www/$SITENAME/ssl/$SITENAME.key"
		if [ $? -ne 0 ]; then
			return 1
		fi
	fi
	return 0
}

write_config() {
	echo "$SITECONFIG" > /etc/nginx/sites-available/$SITENAME.conf
	if [ $? -ne 0 ]; then
		return 1
	fi
	return 0
}

find_free_tcp_port()
{
	semanage port -l > /tmp/seports
	SEARCHING=true
	PORT=9000
	MAXTRIES=20
	counter=1
	while $SEARCHING
	do
		if grep --quiet "$port" /tmp/seports; then
			 PORT=$(($PORT + 1))
		else
			SEARCHING=false
		fi
		if [ $counter -eq MAXTRIES ]; then
			ERROR="Could not find a free port after $MAXTRIES tries."
			return 1
		fi
	done
}

create_new_php_fpm_config()
{
	echo "
	; Start a new pool named '$SITENAME'
	[$SITENAME]
	listen = 127.0.0.1:$PORT
	listen.allowed_clients = 127.0.0.1
	user = nginx
	group = nginx
	pm = ondemand
	pm.max_children = 15
	pm.process_idle_timeout = 10s
	pm.max_requests = 200
	pm.start_servers = 3
	pm.max_spare_servers = 2
	slowlog = /srv/www/$SITENAME/logs/php-fpm/slow.log
	php_admin_value[error_log] = /srv/www/$SITENAME/logs/php-fpm/error.log
	php_admin_flag[log_errors] = on
	php_value[session.save_handler] = files
	php_value[session.save_path]    = /srv/www/$SITENAME/session
	php_value[soap.wsdl_cache_dir]  = /var/lib/php/wsdlcache" > /etc/php-fpm.d/$SITENAME.conf
	semanage port -a -t http_port_t -p tcp $PORT
}

activate_site() {
	if [ "$ACTIVATE" = true -a ! -f /etc/nginx/sites-enabled/$SITENAME.conf ]; then
		ln -s /etc/nginx/sites-enabled/$SITENAME.conf /etc/nginx/sites-available/$SITENAME.conf
		if [ $? -ne 0 ]; then
			return 1
		fi
	fi
	return 0
}

finished() {
	if [ "$SSL" = true ]; then
			iptables -A INPUT -p tcp --dport 80 -m state --state NEW -j ACCEPT
			service iptables save
			service iptables restart
	fi
	CYAN='\033[0;36m'
	NC='\033[0m'
	if [ "$ACTIVATE" =  false ]; then
		echo "$SITENAME has been configured. To activate run the following command, then restart NGINX:"
		echo  -e "${CYAN}ln -s /etc/nginx/sites-enabled/$SITENAME.conf /etc/nginx/sites-available/$SITENAME.conf${NC}"
	else
		echo "$SITENAME has been configured and activated."
		echo "You will need to re/start NGINX and PHP_FPM"
		echo  -e "${CYAN}servie nginx restart${NC}"
		echo  -e "${CYAN}servie php-fpm restart${NC}"
	fi
}

######################################
# Here is where everything is called #
######################################

action "Setting up" check_options
if [ $? -ne 0 ]; then
	echo "$ERROR"
	exit 1
fi
action "Creating site directories" create_site_dir
action "Setting permissions and selinux context"  set_dir_permissions
action "Finding Free port for PHP-FPM (this may take a minute)" find_free_tcp_port
if [ $? -ne 0 ]; then
	echo "$ERROR"
	exit 1
fi
action "Generating NGINX Config" generate_nginx_config
if [ "$SSL" = true ]; then
	action "Configuring site for SSL" configure_for_ssl
fi
action "Writing Config to NGINX" write_config
if [ "$ACTIVATE" = true ]; then
	action "Enabling site" activate_site
fi
finished
