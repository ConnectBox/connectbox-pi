#!/usr/bin/env python3
import json

from ansible.module_utils._text import to_text
from ansible.module_utils.basic import AnsibleModule


def check_php_cli_installed(module):
    """ Check if PHP is installed.  Process will exit with an error message if
    fails (see fail_json).
    """
    (rc, returnvalue, returnerr) = module.run_command(["php", "-v"])
    if rc != 0:
        retvalue = {
            'failed': True,
            'msg': 'Could not run php cli tool',
            'code': 'moodletoolgeneralerror'
        }
        module.fail_json(**retvalue)


def run_moodle_tool(module, moodle_tool_path, install_dir,
                    additional_command=None):
    """ Check if Moodle is installed and / or configured.
    """

    retvalue = {
        'failed': False,
        "msg": None,
        "code": None,
        'moodle_is_installed': False,
        'moodle_needs_upgrading': False,
        'current_version': None,
        'current_release': None,
    }

    (rc, returnvalue, returnerr) = module.run_command(
        ["php", moodle_tool_path, install_dir])

    if not rc:
        return json.loads(returnvalue)
    retvalue[
        'msg'] = 'Could not run the Moodle tool - ' + returnvalue + returnerr
    retvalue['failed'] = True
    retvalue['code'] = 'moodletoolgeneralerror'
    return retvalue


def __convert_output(self, output, strip=True):
    if strip:
        output = output.strip()
    try:
        output = to_text(output, errors='surrogate_or_strict')
    except UnicodeError:
        pass
    return output


def main():
    # Parsing argument file
    module = AnsibleModule(
        argument_spec=dict(
            install_dir=dict(required=True),
            moodle_tool_path=dict(required=True)
        ),
        supports_check_mode=True
    )
    install_dir = module.params.get('install_dir')
    moodle_tool_path = module.params.get('moodle_tool_path')
    check_php_cli_installed(module)  # Fails immediately by calling fail_json
    retvalue = run_moodle_tool(module, moodle_tool_path, install_dir)
    if retvalue and retvalue.get('failed', False):
        module.fail_json(**retvalue)
    module.exit_json(**retvalue)


if __name__ == "__main__":
    main()
