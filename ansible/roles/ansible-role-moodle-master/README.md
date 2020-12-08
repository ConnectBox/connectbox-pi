# Ansible Role: Moodle

Installs Moodle (3.0+) on RedHat and Debian/Ubuntu servers.
Tested with Ansible 2.5

## Requirements

Needs to be a recent LTS release of Ubuntu or REL which have PHP 7.0+, Apache 2.4 and 
Postgres or Mysql installed.
 

## Role Variables

Available variables are listed below, along with default values (see `defaults/main.yml`):

## Dependencies

No dependencies if the host is installed and setup with a LAMP stack 
( or similar ) environement.
If you are required to install the full environment, I suggest you check:
 - geerlingguy.php (Install of PHP 7.x or earlier)
 - geerlingguy.apache (Installation of Apache 2.x)
 - geerlingguy.postgresql (Installation of Postgres)
 - geerlingguy.mysql (Installatiion of Mysql)

## Example Playbook

## License

MIT / BSD

## Author Information

This role was created in 2017 by [Laurent David](https://github.com/laurentdavid), from 
[Jeff Geerling](https://www.jeffgeerling.com/) roles templates author of 
[Ansible for DevOps](https://www.ansiblefordevops.com/).

## Testing

We have used Jeff Geerling's tests as a base, so:

- Test should run on travis  
- Locally you can start the test process using the command

        ./tests/test_local.sh
    
    The docker instance is destroyed at the end of the test, but you can keep it by setting the
     environment variable "cleanup" to "false":
     
        cleanup="false" ./tests/test_local.sh
     
- Once the docker has been launch you can rerun the playbook by running:
```bash
    container_id=xxxxyyy
    docker exec --tty $container_id env TERM=xterm ansible-playbook /etc/ansible/roles/role_under_test/tests/test.yml
```

To test specific playbook such as the check_moodle.py part:
 
```bash
    container_id=xxxxyyy
    docker exec $container_id env TERM=xterm env ANSIBLE_FORCE_COLOR=1 ansible-playbook -i 'localhost,' -M /etc/ansible/roles/role_under_test/library /etc/ansible/roles/role_under_test/tests/test-check-moodle.yml
```

Prerequisites are to have docker installed locally.
It will run the tests on postgresql only. More info in the README.md file in the tests folder.

### Library testing
There is a small module that checks if moodle is installed/configured in the library folder.
More info in the README.md of the library folder.

## #TODO

- Tags tasks 
    -  Pure setup without running moodle install (just folders and source code)
    -  Install with moodle install,
    - ...  some optional task such as change password, update, dump database, ...
      
