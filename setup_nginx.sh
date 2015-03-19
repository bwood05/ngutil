#!/bin/bash
#Install and configure NGINX

install_nginx()
{
	if [ ! -f /etc/yum.repos.d/nginx.repo ]; then
	echo "[nginx]
	name=nginx repo
	baseurl=http://nginx.org/packages/centos/$releasever/$basearch/
	gpgcheck=0
	enabled=1" > /etc/yum.repos.d/nginx.repo
	fi
	if [ ! -f "/etc/init.d/nginx" ]; then
		yum install nginx -y
		if [ $? -ne 0 ]; then
			return 1
		fi
	fi
	if [ ! -f /urs/sbin/semanage ]; then
		yum install policycoreutils-python -y
	fi
	chkconfig nginx on
	chkconfig php-fpm on
	iptables -A INPUT -p tcp --dport 80 -m state --state NEW -j ACCEPT
	service iptables save
	service iptables restart
}

create_dir()
{
	if [ ! -d /etc/nginx/sites-available ]; then
		mkdir /etc/nginx/sites-available
	fi
	if [ ! -d /etc/nginx/sites-enabled ]; then
		mkdir /etc/nginx/sites-enabled
	fi
	sed -i 's~include /etc/nginx/conf.d/\*\.conf;~include /etc/nginx/sites-enabled/\*\.conf;~g' /etc/nginx/nginx.conf
	if [ ! -d /srv/www ]; then
		mkdir -p /srv/www
	fi
}

install_php()
{
	if [ ! -f /etc/yum.repos.d/epel.repo ]; then
		wget http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
		rpm -Uvh epel-release-6*.rpm
	fi
	if [ ! -f /etc/yum.repos.d/ius.repo ]; then
		wget http://dl.iuscommunity.org/pub/ius/stable/CentOS/6/x86_64/ius-release-1.0-13.ius.centos6.noarch.rpm
		rpm -Uvh ius-release*centos6*.rpm
	fi
	yum install php56u -y
}

generate_nginx_config()
{
	WORKERPROCESSES=$(grep processor /proc/cpuinfo | wc -l)
	WORKERCONNECTION=$(ulimit -n)
	echo "user  nginx;
worker_processes  $WORKERPROCESSES;

error_log  /var/log/nginx/error.log warn;
pid        /var/run/nginx.pid;


events {
    worker_connections  $WORKERCONNECTION;
}


http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format  main  '\$remote_addr - \$remote_user [\$time_local] \"\$request\" '
                      '$status $body_bytes_sent \"\$http_referer\" '
                      '\"\$http_user_agent\" \"\$http_x_forwarded_for\"';

    access_log  /var/log/nginx/access.log  main;

    keepalive_timeout   65;
    server_tokens       off;

    ###############
    # GZIP Config #
    ###############
    gzip                on;
    gzip_comp_level     2;
    gzip_min_length     10240;
    gzip_proxied        expired no-cache no-store private auth;
    gzip_types          text/plain text/xml text/css text/javascript application/x-javascript application/xml;
    gzip_diable 		\"MSIE [1-6]\\.\";

    ####################
    # Security Headers #
    ####################
    add_header          X-Frame-Options SAMEORIGIN;
    add_header          X-Content-Type-Options  nosniff;
    add_header          X-XSS-Protection \"1; mode=block\";

    ##################################
    # Include sites in sites-enabled #
    ##################################
    include             /etc/nginx/sites-enabled/*.conf;
}" > ~/nginx.conf
}

setup_phpfpm()
{
	mkdir /etc/php-fpm.d/disabled
	mv /etc/php-fpm.d/www.conf /etc/php-fpm.d/disabled
}
