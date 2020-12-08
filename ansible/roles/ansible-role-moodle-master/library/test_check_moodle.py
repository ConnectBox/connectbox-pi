from unittest.mock import Mock

from nose.tools import assert_true

from library.check_moodle import check_php_cli_installed, run_moodle_tool

USUAL_ANSWERS = {
    'installed php -v':
        (0, 'PHP 7.2.28-3+ubuntu16.04.1+deb.sury.org+1', ''),
    'non-installed php -v':
        (127, '', 'bash: php : commande introuvable'),
    'php /tmp/moodletool.php': (0,
                                '{'
                                '"failed": false,'
                                '"msg": null,'
                                '"code": null,'
                                '"moodle_is_installed": true,'
                                '"moodle_needs_upgrading": false,'
                                '"current_version": "3.8.4",'
                                '"current_release": "3.8"'
                                '}', '')
}


def test_check_php_cli_installed_ok():
    ansible_module = Mock()
    ansible_module.run_command = \
        Mock(return_value=USUAL_ANSWERS['installed php -v'])
    check_php_cli_installed(ansible_module)
    ansible_module.fail_json.assert_not_called()


def test_check_php_cli_installed_no_ok():
    ansible_module = Mock()
    ansible_module.run_command = \
        Mock(return_value=USUAL_ANSWERS['non-installed php -v'])
    check_php_cli_installed(ansible_module)
    ansible_module.fail_json.assert_called()


def test_check_moodle():
    ansible_module = Mock()
    ansible_module.run_command = \
        Mock(return_value=USUAL_ANSWERS['php /tmp/moodletool.php'])
    retvalue = run_moodle_tool(ansible_module, '/tmp/moodletool.php', '/tmp')
    expectedvalue = {
        'failed': False,
        "msg": None,
        "code": None,
        'moodle_is_installed': True,
        'moodle_needs_upgrading': False,
        'current_version': '3.8.4',
        'current_release': '3.8',
    }
    assert_true(
        retvalue == expectedvalue
    )
