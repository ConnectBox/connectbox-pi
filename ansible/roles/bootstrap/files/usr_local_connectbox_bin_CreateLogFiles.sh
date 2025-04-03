#!/bin/bash
#
# The directories /var/log/connectbox and /var/log/nginx are being
#  deleted ate every reboot of the ConnectBox (reason unknown)
#  This script will run at reboot and rebuild those files, then
#  restart the nginx service.

if [ ! -d "/var/log/connectbox" ]
then
    mkdir /var/log/connectbox
fi

if [ ! -d "/var/log/nginx" ]
then
    mkdir /var/log/nginx
fi

touch /var/log/connectbox/captive_portal-access.log
touch /var/log/connectbox/captive_portal-error.log
touch /var/log/connectbox/connectbox-access.log
touch /var/log/connectbox/connectbox-error.log
touch /var/log/nginx/access.log
touch /var/log/nginx/error.log

systemctl restart nginx

