#!/bin/bash
# ------------------------------------------------------------------
# [Kelly Davis] ConnectBoxManage.sh
#               Script for configuring the ConnectBox
# ------------------------------------------------------------------

VERSION=0.1.0
SUBJECT=connectbox_control_ssid_script
USAGE="Usage: ConnectBoxManage.sh -dhv [get|set] [ssid|channel|hostname] <value>"
HOSTAPD_CONFIG="/etc/hostapd/hostapd.conf"
HOSTNAME_CONFIG="/etc/hostname"
HOSTS_CONFIG="/etc/hosts"
NGINX_CONFIG="/etc/nginx/sites-enabled/vhosts.conf"
PASSWORD_CONFIG="/usr/local/connectbox/etc/basicauth"
PASSWORD_SALT="CBOXFOO2016"
DEBUG=0
SUCCESS="SUCCESS"
FAILURE="Unexpected Error"

# --- Options processing -------------------------------------------

while getopts ":dvhg" optname
  do
    case "$optname" in
      "d")
        DEBUG=1
        ;;
      "v")
        echo "Version $VERSION"
        exit 0;
        ;;
      "h")
        echo $USAGE
        exit 0;
        ;;
      "?")
        echo "Unknown option $OPTARG"
        exit 0;
        ;;
      ":")
        echo "No argument value for option $OPTARG"
        exit 0;
        ;;
      *)
        echo "Unknown error while processing options"
        exit 0;
        ;;
    esac
  done

shift $((OPTIND - 1))

action=$1
module=$2
val=$3

# --- Locks -------------------------------------------------------
LOCK_FILE=/tmp/$SUBJECT.lock
if [ -f "$LOCK_FILE" ]; then
   echo "Script is already running"
   exit
fi

trap "rm -f $LOCK_FILE" EXIT
touch $LOCK_FILE

# --- Body --------------------------------------------------------

function usage () {
  echo $USAGE
  exit 1;
}

function backup_hostname_config () {
  # Backup the original configuration file
  if [ ! -e "$HOSTNAME_CONFIG.original" ]; then
    if [ $DEBUG == 1 ]; then
      echo "Backing up $HOSTNAME_CONFIG to $HOSTNAME_CONFIG.original"
    fi

    cp $HOSTNAME_CONFIG $HOSTNAME_CONFIG.original 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -ne 0 ]
    then
      failure
    fi
  fi
}

function restore_hostname_config () {
  # Restore the original configuration file
  if [ -e "$HOSTNAME_CONFIG.original" ]; then
    if [ $DEBUG == 1 ]; then
      echo "Restoring $HOSTNAME_CONFIG from $HOSTNAME_CONFIG.original"
    fi

    cp $HOSTNAME_CONFIG.original $HOSTNAME_CONFIG 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -ne 0 ]
    then
      failure
    else
      hostname `cat $HOSTNAME_CONFIG` 2>&1 | logger -t $(basename $0)

      if [ ${PIPESTATUS[0]} -ne 0 ]
      then
        failure
      fi
    fi
  fi
}

function backup_hosts_config () {
  # Backup the original configuration file
  if [ ! -e "$HOSTS_CONFIG.original" ]; then
    if [ $DEBUG == 1 ]; then
      echo "Backing up $HOSTS_CONFIG to $HOSTS_CONFIG.original"
    fi

    cp $HOSTS_CONFIG $HOSTS_CONFIG.original 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -ne 0 ]
    then
      failure
    fi
  fi
}

function restore_hosts_config () {
  # Restore the original configuration file
  if [ -e "$HOSTS_CONFIG.original" ]; then
    if [ $DEBUG == 1 ]; then
      echo "Restoring $HOSTS_CONFIG from $HOSTS_CONFIG.original"
    fi

    cp $HOSTS_CONFIG.original $HOSTS_CONFIG 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -ne 0 ]
    then
      failure
    fi
  fi
}

function backup_nginx_config () {
  config_file=`basename $NGINX_CONFIG`
  config_path=`dirname $NGINX_CONFIG`

  # Backup the original configuration file
  if [ ! -e "${config_path}/.${config_file}" ]; then
    if [ $DEBUG == 1 ]; then
      echo "Backing up $NGINX_CONFIG to ${config_path}/.${config_file}"
    fi

    cp $NGINX_CONFIG "${config_path}/.${config_file}" 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -ne 0 ]
    then
      failure
    fi
  fi
}

function restore_nginx_config () {
  config_file=`basename $NGINX_CONFIG`
  config_path=`dirname $NGINX_CONFIG`

  if [ -e "${config_path}/.${config_file}" ]; then
    if [ $DEBUG == 1 ]; then
      echo "Restoring $NGINX_CONFIG from ${config_path}/.${config_file}"
    fi

    cp "${config_path}/.${config_file}" $NGINX_CONFIG 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -ne 0 ]
    then
      failure
    fi
  fi
}

function backup_hostapd_config () {
  # Backup the original configuration file
  if [ ! -e "$HOSTAPD_CONFIG.original" ]; then
    if [ $DEBUG == 1 ]; then
      echo "Backing up $HOSTAPD_CONFIG to $HOSTAPD_CONFIG.original"
    fi

    cp $HOSTAPD_CONFIG $HOSTAPD_CONFIG.original 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -ne 0 ]
    then
      failure
    fi
  fi
}

function restore_hostapd_config () {
  # Restore the original configuration file
  if [ -e "$HOSTAPD_CONFIG.original" ]; then
    if [ $DEBUG == 1 ]; then
      echo "Restoring $HOSTAPD_CONFIG from $HOSTAPD_CONFIG.original"
    fi

    cp $HOSTAPD_CONFIG.original $HOSTAPD_CONFIG 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -ne 0 ]
    then
      failure
    fi
  fi
}

function backup_password_config () {
  # Backup the original configuration file
  if [ ! -e "$PASSWORD_CONFIG.original" ]; then
    if [ $DEBUG == 1 ]; then
      echo "Backing up $PASSWORD_CONFIG to $PASSWORD_CONFIG.original"
    fi

    cp $PASSWORD_CONFIG $PASSWORD_CONFIG.original 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -ne 0 ]
    then
      failure
    fi

    chmod 660 $PASSWORD_CONFIG.original 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -ne 0 ]
    then
      failure
    fi

    chown _connectbox:_connectbox $PASSWORD_CONFIG.original 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -ne 0 ]
    then
      failure
    fi
  fi
}

function restore_password_config () {
  # Backup the original configuration file
  if [ -e "$PASSWORD_CONFIG.original" ]; then
    if [ $DEBUG == 1 ]; then
      echo "Restoring $PASSWORD_CONFIG from $PASSWORD_CONFIG.original"
    fi

    cp $PASSWORD_CONFIG.original $PASSWORD_CONFIG 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -ne 0 ]
    then
      failure
    fi
  fi
}

function reset () {
  restore_password_config
  restore_hostapd_config
  restore_nginx_config
  restore_hostname_config
  restore_hosts_config
  reload_nginx
  restart_hostapd
  success
}

function success () {
  echo $SUCCESS
  exit 0;
}

function failure () {
  echo $FAILURE
  exit 1;
}

function reload_nginx () {
  # Restart the nginx service
  if [ $DEBUG == 1 ]; then
    echo "Reloading nginx configuration"
  fi

  # gunicorn gets connectbox hostname from an nginx response so restart
  #  gunicorn before we reload nginx
  systemctl restart gunicorn
  systemctl reload nginx

  if [ $? -ne 0 ]
  then
    failure
  fi
}

function unmountusb () {
  # Unmount usb
  if [ $DEBUG == 1 ]; then
    echo "Unmounting USB media"
  fi

  pumount /media/usb0 2>&1 | logger -t $(basename $0)

  if [ $? -eq 0 ]
  then
    success
  else
    failure
  fi
}

function doshutdown () {
  # Shutdown
  if [ $DEBUG == 1 ]; then
    echo "Shutting down"
  fi

  /sbin/shutdown now 2>&1 | logger -t $(basename $0)

  if [ ${PIPESTATUS[0]} -eq 0 ]
  then
    success
  else
    failure
  fi
}

function doreboot () {
  # Reboot
  if [ $DEBUG == 1 ]; then
    echo "Rebooting"
  fi

  /sbin/reboot 2>&1 | logger -t $(basename $0)

  if [ ${PIPESTATUS[0]} -eq 0 ]
  then
    success
  else
    failure
  fi
}

function restart_hostapd () {
  # Restart the hostapd service
  if [ $DEBUG == 1 ]; then
    echo "Restarting hostapd"
  fi

  ifdown wlan0  2>&1 | logger -t $(basename $0)
  if [ ${PIPESTATUS[0]} -ne 0 ]
  then
    failure
  fi

  sleep 1

  ifup wlan0  2>&1 | logger -t $(basename $0)

  if [ ${PIPESTATUS[0]} -ne 0 ]
  then
    failure
  fi
}

function set_password () {
  if [[ -z "${val// }" ]]; then
    echo "Missing password value"
    exit 1;
  fi

  backup_password_config

  # Update the password property in the basicauth configuration file
  if [ $DEBUG == 1 ]; then
    echo "Updating password to '$val'"
  fi

  local new_hash=`echo $val | openssl passwd -apr1 -salt $PASSWORD_SALT -stdin`
  echo "admin:$new_hash" > $PASSWORD_CONFIG 2>&1 | logger -t $(basename $0)

  if [ ${PIPESTATUS[0]} -eq 0 ]
  then
    reload_nginx
    success
  else
    failure
  fi
}

function get_staticsite () {
  symlink=`readlink /etc/nginx/sites-enabled/connectbox_interface.conf`
  if [[ "$symlink" == *connectbox_static-site.conf ]]; then
    echo "true"
  else
    echo "false"
  fi
}

function set_staticsite () {
  if [[ -z "${val// }" ]]; then
    echo "Missing staticsite value"
    exit 1;
  fi

  symlink="/etc/nginx/sites-enabled/connectbox_interface.conf"
  rm /etc/nginx/sites-enabled/connectbox_interface.conf 2>&1 | logger -t $(basename $0)
  if [ ${PIPESTATUS[0]} -eq 0 ]
  then
    conf="connectbox_icon-only.conf"
    if [[ "$val" == "true" ]]; then
      conf="connectbox_static-site.conf"
    fi
    ln -s "/etc/nginx/sites-available/${conf}" ${symlink} 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -eq 0 ]
    then
      reload_nginx
      success
    else
      failure
    fi
  else
    failure
  fi
}

function get_hostname () {
  local host_name=`hostname`
  echo $host_name;
}

function set_hostname () {
  if [[ -z "${val// }" ]]; then
    echo "Missing hostname value"
    exit 1;
  fi

  backup_hostname_config
  backup_hosts_config

  # Update the hostname in the hostname config
  if [ $DEBUG == 1 ]; then
    echo "Updating hostname to '$val'"
  fi

  host_name=`cat $HOSTNAME_CONFIG`

  # Update /etc/hostname
  sed -i "s/$host_name/$val/g" $HOSTNAME_CONFIG 2>&1 | logger -t $(basename $0)

  if [ ${PIPESTATUS[0]} -eq 0 ]
  then
    # Update /etc/hosts
    sed -i "s/$host_name/$val/g" $HOSTS_CONFIG 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -eq 0 ]
    then
      # Update hostname
      hostname $val 2>&1 | logger -t $(basename $0)

      if [ ${PIPESTATUS[0]} -eq 0 ]
      then
        reload_nginx
        success
      else
        failure
      fi
    else
      failure
    fi
  else
    failure
  fi
}

function get_channel () {
  local channel=`grep '^channel=' $HOSTAPD_CONFIG | cut -d"=" -f2`
  echo ${channel}
}

function set_channel () {
  if [[ -z "${val// }" ]]; then
    echo "Missing channel value"
    exit 1;
  fi

  backup_hostapd_config

  # Update the channel property in the hostapd configuration file
  if [ $DEBUG == 1 ]; then
    echo "Updating channel to '$val'"
  fi

  sed -i "s/^channel=.*/channel=$val/g" $HOSTAPD_CONFIG 2>&1 | logger -t $(basename $0)

  if [ ${PIPESTATUS[0]} -eq 0 ]
  then
    restart_hostapd
    success
  else
    failure
  fi
}

function get_ssid () {
  local ssid=`grep '^ssid=' $HOSTAPD_CONFIG | cut -d"=" -f2`
  echo ${ssid};
}

function set_ssid () {
  if [[ -z "${val// }" ]]; then
    echo "Missing ssid value"
    exit 1;
  fi

  local ssid_length=`printf "%s" "$val" | wc -c`

  if [[ $ssid_length -gt 32 ]]; then
    echo "SSID must be 32 octets or less"
    exit 1;
  fi

  backup_hostapd_config

  # Update the ssid property in the hostapd configuration file
  if [ $DEBUG == 1 ]; then
    echo "Updating ssid to '$val'"
  fi

  sed -i "s/^ssid=.*/ssid=$val/g" $HOSTAPD_CONFIG 2>&1 | logger -t $(basename $0)

  if [ ${PIPESTATUS[0]} -eq 0 ]
  then
    restart_hostapd
    success
  else
    failure
  fi
}

if [[ $# -lt 1 ]]; then
    usage
fi

if [ "$action" = "get" ]; then
  case "$module" in
    "ssid")
      get_ssid
      exit 0;
      ;;

    "channel")
      get_channel
      exit 0;
      ;;

    "hostname")
      get_hostname
      exit 0;
      ;;

    "staticsite")
      get_staticsite
      exit 0;
      ;;

    *)
      usage
      ;;

  esac
elif [ "$action" = "set" ]; then
  case "$module" in
    "ssid")
      set_ssid
      exit 0;
      ;;

    "channel")
      set_channel
      exit 0;
      ;;

    "hostname")
      set_hostname
      exit 0;
      ;;

    "staticsite")
      set_staticsite
      exit 0;
      ;;

    "password")
      set_password
      exit 0;
      ;;

    *)
      usage
      ;;

  esac
elif [ "$action" = "unmountusb" ]; then
  unmountusb
elif [ "$action" = "shutdown" ]; then
  doshutdown
elif [ "$action" = "reboot" ]; then
  doreboot
elif [ "$action" = "reset" ]; then
  reset
else
  usage
fi
