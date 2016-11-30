#!/bin/bash
# ------------------------------------------------------------------
# [Kelly Davis] ssid.sh
#               Script for configuring the ssid in hostapd
# ------------------------------------------------------------------

VERSION=0.1.0
SUBJECT=biblebox_control_ssid_script
USAGE="Usage: BBoxManage.sh -dhv [get|set] [ssid|channel|hostname] <value>"
NGINX_CONFIG="/etc/nginx/sites-enabled/vhosts.conf"
HOSTAPD_CONFIG="/etc/hostapd/hostapd.conf"
PASSWORD_CONFIG="/usr/local/biblebox/etc/basicauth"
PASSWORD_SALT="BBOXFOO2016"
DEBUG=0
SUCCESS="SUCCESS"
FAILURE="FAILURE"

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

shift $(($OPTIND - 1))

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

function backup_nginx_config () {
  config_file=".$(basename $NGINX_CONFIG)"
  config_path="${NGINX_CONFIG:0:${#NGINX_CONFIG}-${#config_file}}"

  # Backup the original configuration file
  if [ ! -e "${config_path}/${config_file}" ]; then
    if [ $DEBUG == 1 ]; then
      echo 'Backing up $NGINX_CONFIG to ${config_path}/${config_file}'
    fi

    cp $NGINX_CONFIG "${config_path}/${config_file}" 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -ne 0 ]
    then
      failure
    fi
  fi
}

function restore_nginx_config () {
  config_file=".$(basename $NGINX_CONFIG)"
  config_path="${NGINX_CONFIG:0:${#NGINX_CONFIG}-${#config_file}}"

  if [ -e "${config_path}/${config_file}" ]; then
    if [ $DEBUG == 1 ]; then
      echo 'Restoring $NGINX_CONFIG from ${config_path}/${config_file}'
    fi

    cp "${config_path}/${config_file}" $NGINX_CONFIG 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -ne 0 ]
    then
      failure
    else
      reload_nginx
    fi
  fi
}

function backup_hostapd_config () {
  # Backup the original configuration file
  if [ ! -e "$HOSTAPD_CONFIG.original" ]; then
    if [ $DEBUG == 1 ]; then
      echo 'Backing up $HOSTAPD_CONFIG to $HOSTAPD_CONFIG.original'
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
      echo 'Restoring $HOSTAPD_CONFIG from $HOSTAPD_CONFIG.original'
    fi

    cp $HOSTAPD_CONFIG.original $HOSTAPD_CONFIG 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -ne 0 ]
    then
      failure
    else
      restart_hostapd
    fi
  fi
}

function backup_password_config () {
  # Backup the original configuration file
  if [ ! -e "$PASSWORD_CONFIG.original" ]; then
    if [ $DEBUG == 1 ]; then
      echo 'Backing up $PASSWORD_CONFIG to $PASSWORD_CONFIG.original'
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

    chown biblebox:biblebox $PASSWORD_CONFIG.original 2>&1 | logger -t $(basename $0)

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
      echo 'Restoring $PASSWORD_CONFIG from $PASSWORD_CONFIG.original'
    fi

    cp $PASSWORD_CONFIG.original $PASSWORD_CONFIG 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -ne 0 ]
    then
      failure
    else
      reload_nginx
    fi
  fi
}

function reset () {
  restore_password_config
  restore_hostapd_config
  restore_nginx_config
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

  /etc/init.d/nginx reload

  if [ $? -eq 0 ]
  then
    success
  else
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

  /etc/init.d/hostapd restart

  if [ $? -eq 0 ]
  then
    success
  else
    failure
  fi
}

function set_password () {
  if [[ -z "${val// }" ]]; then
    echo 'Missing password value'
    exit 1;
  fi

  backup_password_config

  # Update the password property in the basicauth configuration file
  if [ $DEBUG == 1 ]; then
    echo "Updating password to '$val'"
  fi

  local new_hash=`echo $val | openssl passwd -apr1 -salt $PASSWORD_SALT -stdin`
  echo "biblebox:$new_hash" > $PASSWORD_CONFIG 2>&1 | logger -t $(basename $0)

  if [ ${PIPESTATUS[0]} -eq 0 ]
  then
    reload_nginx
  else
    failure
  fi
}

function get_hostname () {
  local hostname=`grep 'bbox_server_name=' $NGINX_CONFIG`
  local idx=`expr index "$hostname" =`

  web_hostname="${hostname:$idx:${#hostname}-$idx}"

  echo $web_hostname;
}

function set_hostname () {
  if [[ -z "${val// }" ]]; then
    echo 'Missing hostname value'
    exit 1;
  fi

  backup_nginx_config

  # Update the hostname in the nginx config
  if [ $DEBUG == 1 ]; then
    echo "Updating hostname to '$val'"
  fi

  get_hostname > /dev/null #suppress output

  sed -i "s/$web_hostname/$val/g" $NGINX_CONFIG 2>&1 | logger -t $(basename $0)

  if [ ${PIPESTATUS[0]} -eq 0 ]
  then
    reload_nginx
  else
    failure
  fi
}

function get_channel () {
  local channel=`grep '^channel=' $HOSTAPD_CONFIG`
  if [[ $channel == channel=\"* ]]; then
    echo ${channel:9:${#channel}-10};
  else
    echo ${channel:8:${#channel}-8};
  fi
}

function set_channel () {
  if [[ -z "${val// }" ]]; then
    echo 'Missing channel value'
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
  else
    failure
  fi
}

function get_ssid () {
  local ssid=`grep '^ssid=' $HOSTAPD_CONFIG`
  if [[ $ssid == ssid=\"* ]]; then
    echo ${ssid:6:${#ssid}-7};
  else
    echo ${ssid:5:${#ssid}-5};
  fi
}

function set_ssid () {
  if [[ -z "${val// }" ]]; then
    echo 'Missing ssid value'
    exit 1;
  fi

  backup_hostapd_config

  # Update the ssid property in the hostapd configuration file
  if [ $DEBUG == 1 ]; then
    echo "Updating ssid to '$val'"
  fi

  sed -i "s/^ssid=.*/ssid=\"$val\"/g" $HOSTAPD_CONFIG 2>&1 | logger -t $(basename $0)

  if [ ${PIPESTATUS[0]} -eq 0 ]
  then
    restart_hostapd
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
