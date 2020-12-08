# Check Moodle state module

This module is intended to check Moodle state (installed, to be upgraded) so we can take decision regarding
what needs to be done in term of setting it up.

    - name: Check the state of current moodle
      check_moodle:
        install_dir: "{{ moodle_src_path }}"
      register: moodle_state

The moodle_state will have the following values:

* msg: an error message if any (this contains the error message sent by moodle, for example if we cannot
connect to existing database)
* code: error code if any (from moodle)
* moodle_needs_upgrading: boolean - moodle needs upgrading
* moodle_is_installed: boolean - moodle is installed (a *valid* config file is there)

The process can also fail if the PHP CLI command (`php`) does not work or the provided folder is not a moodle folder.

# Implementation notes

Here we use the combination of action module (to push the moodletool.php script first) followed
by the usual Ansible module library.
So check_moodle will first call the code in action_plugin/check_moodle.py and then the code in check_moodle.py.


## Testing 
To test it you need to install nose

    pip install nose
    
Then:

    cd library
    nosetests -v test_check_moodle.py
    
Also you can directly test the script by doing:

    python library/check_moodle.py  < library/test-check_moodle_input.json 

If you need to test the action module (that will call this same library module), and in the root folder of this role:

    ANSIBLE_ACTION_PLUGINS=`pwd`/action_plugins ANSIBLE_LIBRARY=`pwd`/library /home/laurentd/.virtualenvs/ansible-role-moodle/bin/ansible -vvv localhost -m check_moodle -a "install_dir=~/websites/htdocs/moodlelatest"
