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