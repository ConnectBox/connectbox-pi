<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Moodle is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Moodle.  If not, see <http://www.gnu.org/licenses/>.

/**
 * This is a CLI Script that will allow different actions to be taken or
 * to gather information about the current Moodle installation.
 * This should not fail and always return the right error message.
 *
 * @copyright   2020 CALL Learning <laurent@call-learning.fr>
 * @license     http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

define('CLI_SCRIPT', true);

/**
 * Returns cli script parameters.
 * This is a copy of the Moodle cli_get_params (and will be updated accordingly).
 * The idea here is that we are not sure we have a Moodle accessible somewhere so
 * we cannot rely on the inclusion of clilib.php
 *
 * @param array $longoptions array of --style options ex:('verbose'=>false)
 * @param array $shortmapping array describing mapping of short to long style options ex:('h'=>'help', 'v'=>'verbose')
 * @return array array of arrays, options, unrecognised as optionlongname=>value
 */
function moodle_cli_get_params(array $longoptions, array $shortmapping = null) {
    $shortmapping = (array) $shortmapping;
    $options = array();
    $unrecognized = array();

    if (empty($_SERVER['argv'])) {
        // bad luck, we can continue in interactive mode ;-)
        return array($options, $unrecognized);
    }
    $rawoptions = $_SERVER['argv'];

    //remove anything after '--', options can not be there
    if (($key = array_search('--', $rawoptions)) !== false) {
        $rawoptions = array_slice($rawoptions, 0, $key);
    }

    //remove script
    unset($rawoptions[0]);
    foreach ($rawoptions as $raw) {
        if (substr($raw, 0, 2) === '--') {
            $value = substr($raw, 2);
            $parts = explode('=', $value);
            if (count($parts) == 1) {
                $key = reset($parts);
                $value = true;
            } else {
                $key = array_shift($parts);
                $value = implode('=', $parts);
            }
            if (array_key_exists($key, $longoptions)) {
                $options[$key] = $value;
            } else {
                $unrecognized[] = $raw;
            }

        } else if (substr($raw, 0, 1) === '-') {
            $value = substr($raw, 1);
            $parts = explode('=', $value);
            if (count($parts) == 1) {
                $key = reset($parts);
                $value = true;
            } else {
                $key = array_shift($parts);
                $value = implode('=', $parts);
            }
            if (array_key_exists($key, $shortmapping)) {
                $options[$shortmapping[$key]] = $value;
            } else {
                $unrecognized[] = $raw;
            }
        } else {
            $unrecognized[] = $raw;
            continue;
        }
    }
    //apply defaults
    foreach ($longoptions as $key => $default) {
        if (!array_key_exists($key, $options)) {
            $options[$key] = $default;
        }
    }
    // finished
    return array($options, $unrecognized);
}

// No error display here.
if (empty($options['debug'])) {
    ob_start();
    ini_set('display_errors', '0');
    ini_set('log_errors', 0);
    define('NO_DEBUG_DISPLAY', true); // Do not display error on the command line.
}
list($options, $unrecognised) = moodle_cli_get_params([
    'help' => false,
], [
    'h' => 'help',
]);

$cfgpath = './';
if ($unrecognised) {
    $cfgpath = reset($unrecognised);
    $cfgpath = rtrim($cfgpath, '/') . '/';
}

if (is_file($cfgpath . 'config.php')) {
    include_once($cfgpath . 'config.php');
}

$usage = "Moodle php tool to check and do various actions in conjunction with ansible (see ansible-role-moodle)

Usage:
    # php moodletool.php  PATH
    # php moodletool.php [--help|-h]

Options:
    -h --help                   Print this help.
    --config-set|-c             Set the 'config configname','configvalue'
    PATH                        Current installation path. If not provided this will be considered to be the current directory.

Without argument this will just return a json encoded string that represents the state of the moodle installation.
This will be an json object with the following values:
{
    'failed': [True or false],
    'msg': [Text message if failed], // Optional
    'code': [Error code if failed],  // Optional
    'current_version': [Current Moodle version], // Optional
    'moodle_is_installed': [true or false],
    'moodle_needs_upgrading': [true or false],
}

Other commands might return a different set of values, but failed, msg and code are
pretty much always there.
In the read mode, the script exits with success status 0 even if we have not found
the config file (config.php).
In case of unexpected error, the script exits with error status 1.

Examples:

    # php moodletool.php
        Return the basic information regarding the current moodle installation

    # php moodletool.php /my/installation/path
        Same as above but will look into the installation path provided.
";

$returnvalue = [];
if (!isset($CFG) || empty($CFG->version)) {
    if (is_file($cfgpath . 'config-dist.php')) {
        $returnvalue = [
            'failed' => false,
            'msg' => 'Moodle config.php file not found on :' . $cfgpath,
            'moodle_is_installed' => false,
        ];
    } else {
        $returnvalue =
            [
                'failed' => true,
                'msg' => 'No Moodle installation on :' . $cfgpath,
                'code' => 'moodlesourcenotfound'
            ];
    }
} else {
    // Now we have access to the full clilib.php
    require_once($CFG->libdir . '/clilib.php');
    require_once($CFG->libdir . '/adminlib.php');
    require_once($CFG->libdir . '/upgradelib.php');     // general upgrade/install related functions
    require_once($CFG->libdir . '/environmentlib.php');
    $moodleneedsupgrade = intval(moodle_needs_upgrading());

    if ($options['help']) {
        cli_write($usage);
        exit(0);
    }
    if (!$returnvalue) {
        $returnvalue = [
            'failed' => false,
            'current_version' => $CFG->version,
            'current_release' => $CFG->release,
            'moodle_is_installed' => true,
            'moodle_needs_upgrading' => $moodleneedsupgrade,
        ];
    }
}
if (empty($options['debug'])) {
    ob_clean();
}
echo json_encode($returnvalue);
