# coding: utf-8
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
import os

from ansible.errors import AnsibleError
from ansible.plugins.action import ActionBase

TOOL_FILENAME = 'moodletool.php'


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        ''' handler for transfering the tools '''
        if task_vars is None:
            task_vars = dict()
        self.TRANSFERS_FILES = True  # make sure tmp folder is created first.
        super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect (this is deprecated)
        remote_path = os.path.join(self._connection._shell.tmpdir,
                                   TOOL_FILENAME)
        tool_path = self._shared_loader_obj.module_loader.find_plugin(
            'check_moodle')
        tool_path = os.path.join(
            os.path.dirname(tool_path if tool_path else ''),
            TOOL_FILENAME)
        if os.path.isfile(tool_path):
            module_args = dict(self._task.args)
            module_args.update({'moodle_tool_path': remote_path})
            self._transfer_file(tool_path, remote_path)
            self._cleanup_remote_tmp = False  # Do not cleanup the tmp file yet
            # If set to true, this will delete the folder before the call to
            # the script.
            self._fixup_perms2([remote_path, self._connection._shell.tmpdir])
            return_value = self._execute_module(module_name='check_moodle',
                                                module_args=module_args,
                                                task_vars=task_vars)
            self.cleanup(True)  # Now command is executed we can cleanup
            return return_value
        else:
            raise AnsibleError(
                'Failed to find the tool (%s) on path (%s) to run '
                'the check_moodle ' % (TOOL_FILENAME, tool_path))
