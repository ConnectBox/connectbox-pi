#!/usr/bin/python

DOCUMENTATION = '''
---
module: fa_icons
short_description: Generate font awesome metadata in Javascript
'''

EXAMPLES = '''
- name: Generate FA metadata js file
  fa_icons:
    icons_url: "https://raw.githubusercontent.com/FortAwesome/Font-Awesome/master/src/icons.yml"
    output_dir: "../html/client/lib"
    output_filename: "fa-icon-metadata.js"
    var_name: iconMetadata
'''

import urllib2
import yaml
import json

from ansible.module_utils.basic import *

def generate_icon_metadata(src_url, output_dir, filename, var_name):
    response = urllib2.urlopen("https://raw.githubusercontent.com/FortAwesome/Font-Awesome/master/src/icons.yml")
    source = response.read()
    result = yaml.load(source)

    id_list = []
    name_dict = dict()
    for icon in result['icons']:
        id_list.append(icon['id'])
        name_dict[icon['name']] = icon['id']

    icon_metadata = dict()
    icon_metadata['ids'] = id_list
    icon_metadata['names'] = name_dict

    out = open("%s/%s" % (output_dir, filename), 'w')
    out.write("var %s = %s;" % (var_name, json.dumps(icon_metadata)))
    out.close()

def main():
    fields = {
        "icons_url": {"required": False, "type": "str", "default": "https://raw.githubusercontent.com/FortAwesome/Font-Awesome/master/src/icons.yml"},
        "output_dir" : {"required": False, "type": "str", "default": "../html/client/lib"},
        "output_filename" : {"required": False, "type": "str", "default": "fa-icon-metadata.js"},
        "var_name" : {"required": False, "type": "str", "default": "iconMetadata"}
    }

    module = AnsibleModule(argument_spec=fields)
    generate_icon_metadata(module.params['icons_url'],
        module.params['output_dir'], module.params['output_filename'], module.params['var_name'])
    module.exit_json(changed=True, meta={"status": 0, "data": "SUCCESS"})

if __name__ == '__main__':
    main()