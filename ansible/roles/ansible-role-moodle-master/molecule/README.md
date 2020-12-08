## Additional testing through localhost


As we have several scripts that would need to be tested locally in development
mode, here are a few tips on how to launch them on a local install.

Test the check_moodle plugin: 

``
ANSIBLE_ACTION_PLUGINS=`pwd`/action_plugins ANSIBLE_LIBRARY=`pwd/library` ansible -vvv localhost -m check_moodle -a "install_dir=~/websites/htdocs/moodlelatest"
``
