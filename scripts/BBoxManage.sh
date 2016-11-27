#!/bin/bash
# ------------------------------------------------------------------
# [Kelly Davis] ssid.sh
#               Script for configuring the ssid in hostapd
# ------------------------------------------------------------------

VERSION=0.1.0
SUBJECT=biblebox_control_ssid_script
USAGE="Usage: BBoxManage.sh -ihv [get|set] [ssid|channel] <value>"
HOSTAPD_CONFIG=/etc/hostapd/hostapd.conf
PASSWORD_CONFIG=/usr/local/biblebox/etc/basicauth
PASSWORD_SALT=BBOXFOO2016
DEBUG=0
SUCCESS="SUCCESS"
FAILURE="FAILURE"

# --- Options processing -------------------------------------------

while getopts ":i:dvhg" optname
  do
    case "$optname" in
      "d")
        DEBUG=1
        ;;
      "v")
        echo "Version $VERSION"
        exit 0;
        ;;
      "i")
        echo "-i argument: $OPTARG"
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

function get_channel () {
  local channel=`grep '^channel=' $CONFIG_FILE`
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

  sed -i "s/^channel=.*/channel=$val/g" $CONFIG_FILE 2>&1 | logger -t $(basename $0)

  if [ ${PIPESTATUS[0]} -eq 0 ]
  then
    restart_hostapd
  else
    failure
  fi
}

function get_ssid () {
  local ssid=`grep '^ssid=' $CONFIG_FILE`
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

  sed -i "s/^ssid=.*/ssid=\"$val\"/g" $CONFIG_FILE 2>&1 | logger -t $(basename $0)

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
else
  usage
fi
