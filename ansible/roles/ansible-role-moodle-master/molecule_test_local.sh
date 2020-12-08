#!/bin/bash
# Disable apparmor for mysqld as it creates issue at install (https://github.com/moby/moby/issues/7276#issuecomment-68827244)
if [[ "$distro" =~ ^(ubuntu1[6-8]04|debian9)$ ]]  && [ -f /etc/lsb-release ] &&  [ /etc/apparmor.d/usr.sbin.mysqld ]; then
    source /etc/lsb-release
    if [ $DISTRIB_ID = 'Ubuntu' ]; then
        printf "Disabling apparmor for mysql"
        [ -f /etc/apparmor.d/disable/usr.sbin.mysqld ] || sudo ln -s /etc/apparmor.d/usr.sbin.mysqld /etc/apparmor.d/disable/
        sudo apparmor_parser -R /etc/apparmor.d/usr.sbin.mysqld || true
        sudo aa-status
    fi
fi

molecule check

if [[ "$distro" =~ ^(ubuntu1[6-8]04|debian9)$ ]]  && [ -f /etc/lsb-release ] &&  [ /etc/apparmor.d/usr.sbin.mysqld ]; then
    if [ $DISTRIB_ID = 'Ubuntu' ]; then
        printf "Enabling apparmor for mysql again"
        sudo rm /etc/apparmor.d/disable/usr.sbin.mysqld || true
        sudo apparmor_parser -r /etc/apparmor.d/usr.sbin.mysqld || true
        sudo aa-status
    fi
fi
