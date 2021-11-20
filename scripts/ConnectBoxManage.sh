#!/bin/bash
# ------------------------------------------------------------------
# [Kelly Davis] ConnectBoxManage.sh
#               Script for configuring the ConnectBox
# ------------------------------------------------------------------

VERSION=0.1.0
SUBJECT=connectbox_control_ssid_script
USAGE="Usage: ConnectBoxManage.sh -dhv [get|set|check] [ssid|channel|wpa-passphrase|hostname|staticsite|password|ui-config|client-ssid|client-wifipassword|course-download|course-usb|openwell-download|openwell-usb|brand] <value>"
HOSTAPD_CONFIG="/etc/hostapd/hostapd.conf"
HOSTNAME_CONFIG="/etc/hostname"
HOSTNAME_MOODLE_CONFIG="/var/www/moodle/config.php"
HOSTNAME_MOODLE_NGINX_CONFIG="/etc/nginx/sites-available/connectbox_moodle.conf"
HOSTS_CONFIG="/etc/hosts"
BRAND_CONFIG="/usr/local/connectbox/brand.txt"
NGINX_CONFIG="/etc/nginx/sites-enabled/vhosts.conf"
PASSWORD_CONFIG="/usr/local/connectbox/etc/basicauth"
WIFI_CONFIGURATOR="/usr/local/connectbox/wifi_configurator_venv/bin/wifi_configurator"
CLIENTWIFI_CONFIG="/etc/network/interfaces"
PASSWORD_SALT="CBOX2018"
UI_CONFIG="/var/www/connectbox/connectbox_default/config/default.json"
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
extended=$4  # Used only from brand

logger -t $(basename $0) "$action $module $val"

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

function backup_ui_config () {
  # Backup the original configuration file
  if [ ! -e "$UI_CONFIG.original" ]; then
    if [ $DEBUG == 1 ]; then
      echo "Backing up $UI_CONFIG to $UI_CONFIG.original"
    fi

    cp $UI_CONFIG $UI_CONFIG.original 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -ne 0 ]
    then
      failure
    fi
  fi
}

function restore_ui_config () {
  # Restore the original configuration file
  if [ -e "$UI_CONFIG.original" ]; then
    if [ $DEBUG == 1 ]; then
      echo "Restoring $UI_CONFIG from $UI_CONFIG.original"
    fi

    cp $UI_CONFIG.original $UI_CONFIG 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -ne 0 ]
    then
      failure
    fi
  fi
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
  restore_ui_config
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

  systemctl reload nginx 2>&1 | logger -t $(basename $0)

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

  ifdown wlan1  2>&1 | logger -t $(basename $0)
  if [ ${PIPESTATUS[0]} -ne 0 ]
  then
    failure
  fi

  sleep 1

  ifup wlan1  2>&1 | logger -t $(basename $0)

  if [ ${PIPESTATUS[0]} -ne 0 ]
  then
    failure
  fi
}

function check_password () {
  if [[ -z "${val// }" ]]; then
    echo "Missing password value"
    exit 1;
  fi

  local new_hash=`echo $val | openssl passwd -apr1 -salt $PASSWORD_SALT -stdin`
  local password=`cat $PASSWORD_CONFIG`

  if [ "admin:$new_hash" = "$password" ]; then
    success
  else
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
      if [ ! -f /media/usb0/index.html ]; then
        indexfile='<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
        <html lang="en">
        <head>
          <meta http-equiv="content-type" content="text/html; charset=utf-8">
          <title>Created Index.html File</title>
        </head>
        <body>
            <h1>Welcome to your ConnectBox!</h1>
            <p>Your ConnectBox is configured for running static webpages but you do not have an index.html page 
            on your storage device so we created this one for you. You can edit this page to make one.</p>
        </body>
        </html>'
        echo "$indexfile" > /media/usb0/index.html
      fi    
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

function get_ui_config () {
  local ui_config=`cat $UI_CONFIG`
  echo $ui_config;
}

function set_ui_config () {
  if [[ -z "${val// }" ]]; then
    echo "Missing ui config value"
    exit 1;
  fi

  backup_ui_config

  # Update the ui config
  if [ $DEBUG == 1 ]; then
    echo "Updating ui config to '$val'"
  fi

  echo $val > $UI_CONFIG 2>&1 | logger -t $(basename $0)

  if [ ${PIPESTATUS[0]} -eq 0 ]
  then
    success
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

  # Set current hostname
  hostname $val 2>&1

  if [ ${PIPESTATUS[0]} -eq 0 ]
  then
    # Update /etc/hosts
    sed -i "s/$host_name/$val/g" $HOSTS_CONFIG 2>&1 | logger -t $(basename $0)

    if [ ${PIPESTATUS[0]} -eq 0 ]
    then
      # Update brand.txt
      sed -i 's/\"$host_name\"/\"$val\"/g' $BRAND_CONFIG 2>&1 | logger -t $(basename $0)

      if [ ${PIPESTATUS[0]} -eq 0 ]
      then
      	sed -i "s/$host_name/$val/g" $HOSTNAME_MOODLE_CONFIG 2>&1 | logger -t $(basename $0)
  		sed -i "s/$host_name/$val/g" $HOSTNAME_MOODLE_NGINX_CONFIG 2>&1 | logger -t $(basename $0)
        reload_nginx
        systemctl restart avahi-daemon
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

##############################
# Added by Derek Maxson 20210616
function set_hostname_moodle_nginx () {
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

  # Update HOSTNAME_MOODLE_NGINX_CONFIG

  if [ ${PIPESTATUS[0]} -eq 0 ]
    then
	  success
    else
	  failure
  fi
}

##############################
# Added by Derek Maxson 20210616
function set_hostname_moodle_config_php () {
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

  # Update HOSTNAME_MOODLE_CONFIG
  sed -i "s/$host_name/$val/g" $HOSTNAME_MOODLE_CONFIG 2>&1 | logger -t $(basename $0)

  if [ ${PIPESTATUS[0]} -eq 0 ]
    then
	  success
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

  ${WIFI_CONFIGURATOR} --channel "${val}" | logger -t $(basename $0)

  if [ ${PIPESTATUS[0]} -eq 0 ]
  then
    restart_hostapd
    success
  else
    failure
  fi
}

function get_wpa_passphrase () {
  local channel=`grep '^wpa_passphrase=' $HOSTAPD_CONFIG | cut -d"=" -f2`
  echo ${channel}
}

function set_wpa_passphrase () {
  # No need to check for empty value, as empty is legit (it's how we clear
  #  the passphrase)

  backup_hostapd_config

  # Update the wpa_passphrase property in the hostapd configuration file
  if [ $DEBUG == 1 ]; then
    echo "Updating wpa_passphrase to '$val'"
  fi

  ${WIFI_CONFIGURATOR} --wpa-passphrase "${val}" | logger -t $(basename $0)

  if [ ${PIPESTATUS[0]} -eq 0 ]
  then
    restart_hostapd
    success
  else
    failure
  fi
}

# Added by Derek Maxson 20211102
function get_client_ssid () {
  local channel=`grep 'wpa-ssid' $CLIENTWIFI_CONFIG | cut -d"\"" -f2`
  echo ${channel}
}

function set_client_ssid () {
  sudo sed -i -e "/ssid=/ s/=.*/=${val}/" /etc/wpa_supplicant/wpa_supplicant.conf
  sudo sed -i -e "/wpa-ssid=/ s/=.*/=${val}/" /etc/network/interfaces
  ifdown wlan0 2>&1 
  ifup wlan0  2>&1 
  success
}

function get_client_wifipassword () {
  local channel=`grep 'wpa-psk' $CLIENTWIFI_CONFIG | cut -d"\"" -f2`
  echo ${channel}
}

function set_client_wifipassword () {
  sudo sed -i -e "/psk=/ s/=.*/=${val}/" /etc/wpa_supplicant/wpa_supplicant.conf
  sudo sed -i -e "/wpa-psk=/ s/=.*/=${val}/" /etc/network/interfaces
  ifdown wlan0 2>&1 
  ifup wlan0  2>&1 
  success
}

# Added by Derek Maxson 20210616
function set_course_download () {
  local channel=`sudo -u www-data wget -O /tmp/download.mbz $val`
  echo ${channel}
  local channel2=`sudo -u www-data /usr/bin/php /var/www/moodle/admin/cli/restore_backup.php --file=/tmp/download.mbz --categoryid=1`
  echo ${channel2}
  SUCCESS
}

# Added by Derek Maxson 20211108
function set_course_usb () {
  local channel2=`sudo -u www-data /usr/bin/php /var/www/moodle/admin/cli/restore_courses_directory.php /media/usb0/`
  echo ${channel2}
  SUCCESS
}

# Added by Derek Maxson 20211104
function set_openwell_download () {
  sudo -u www-data wget -O /tmp/openwell.zip $val >/dev/null
  sudo -u www-data rm -rf /var/www/enhanced/content/www/assets/content >/dev/null 
  sudo -u www-data unzip -o /tmp/openwell.zip -d /var/www/enhanced/content/www/assets/ | logger -t $(basename $0)

  if [ ${PIPESTATUS[0]} -eq 0 ]
  then
    sudo rm /tmp/openwell.zip
    success
  else
    failure
  fi
}

# Added by Derek Maxson 20211108
function set_openwell_usb () {
  sudo -u cp /media/usb0/openwell.zip /tmp/openwell.zip $val >/dev/null
  sudo -u www-data rm -rf /var/www/enhanced/content/www/assets/content >/dev/null 
  sudo -u www-data unzip -o /tmp/openwell.zip -d /var/www/enhanced/content/www/assets/ | logger -t $(basename $0)

  if [ ${PIPESTATUS[0]} -eq 0 ]
  then
    sudo rm /tmp/openwell.zip
    success
  else
    failure
  fi
}

# Added by Derek Maxson 20210629
function wipeSDCard () {
  # Schedule a shutdown then wipe the card
  local channel=`sudo "/sbin/shutdown -r 5 && rm -rf *"`
  echo ${channel}
}

# Added by Derek Maxson 20211102
# This supports all root level elements of /usr/local/connectbox/brand.txt 
function get_brand () {
  IFS='=' read -r -a array <<< "$val"
  local jqString="jq '.[\"${array[0]}\"]' $BRAND_CONFIG"
  local editme=$(eval "$jqString")
  echo ${editme}
}

# Added by Derek Maxson 20211102
# This supports all root level elements of /usr/local/connectbox/brand.txt 
function setBrand () {
  IFS='=' read -r -a array <<< "$val"
  if [ ${array[0]} == 'Screen_Enable' ]; then
    jqString="jq '.[\"${array[0]}\"]=${array[1]}' $BRAND_CONFIG"  
  else 
    jqString="jq '.[\"${array[0]}\"]=\"${array[1]}\"' $BRAND_CONFIG"
  fi
  local editme=$(eval "$jqString")
  echo ${editme} >$BRAND_CONFIG  # Write the resulting file
  success
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

  # XXX: Move this check into the wifi configurator
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

  ${WIFI_CONFIGURATOR} --ssid "${val}" | logger -t $(basename $0)

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

    "ui-config")
      get_ui_config
      exit 0;
      ;;

    "wpa-passphrase")
      get_wpa_passphrase
      exit 0;
      ;;

    "client-ssid")
      get_client_ssid
      exit 0;
      ;;

    "client-wifipassword")
      get_client_wifipassword
      exit 0;
      ;;

    "brand")
      get_brand
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

    "ui-config")
      set_ui_config
      exit 0;
      ;;

    "wpa-passphrase")
      set_wpa_passphrase
      exit 0;
      ;;

    "client-ssid")
      set_client_ssid
      exit 0;
      ;;

    "client-wifipassword")
      set_client_wifipassword
      exit 0;
      ;;

    "course-download")
      # Added by Derek Maxson 20210616
      set_course_download
      exit 0;
      ;;

    "course-usb")
      # Added by Derek Maxson 20211108
      set_course_usb
      exit 0;
      ;;

    "openwell-download")
      # Added by Derek Maxson 20211104
      set_openwell_download
      exit 0;
      ;;

    "openwell-usb-zip")
      # Added by Derek Maxson 20211108
      set_openwell_usb_zip
      exit 0;
      ;;
      
    "wipe")
      # Added by Derek Maxson 20210629
      wipeSDCard
      exit 0;
      ;;

    "brand")
      # Added by Derek Maxson 20211102
      setBrand
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
elif [ "$action" = "check" ]; then
  case "$module" in
    "password")
      check_password
      exit 0;
      ;;
  *)
    usage
    ;;

  esac
else
  usage
fi
