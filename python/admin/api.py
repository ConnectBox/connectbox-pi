import os,subprocess
from flask import Flask,request,abort,jsonify,make_response

valid_properties = ["ssid", "channel", "hostname", "staticsite", "password", "system", "ui-config"]

def _abort_bad_request():
    abort(make_response("BAD REQUEST", 400))
    

def _call_command(extra_args):
    cmd_args = ["sudo", "/usr/local/connectbox/bin/ConnectBoxManage.sh"]
    called_cmd = subprocess.run(cmd_args + extra_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    result_string= called_cmd.stdout
    if called_cmd.returncode != 0:
        result_string= called_cmd.stderr

    return jsonify(code=called_cmd.returncode,
           result=result_string.decode("utf-8").rstrip().split("\n"))


def get_property(prop):
    prop_string = prop
    if prop_string not in valid_properties:
        _abort_bad_request()
    return _call_command(["get", prop_string])


def set_property_value_wrapped(prop):
    prop_string = prop
    if prop_string not in valid_properties:
        _abort_bad_request() # bad request
    possible_json = request.get_json(force=True, silent=True)
    if (not possible_json) or ("value" not in possible_json):
        _abort_bad_request() # bad request
    return _call_command(["set", prop_string, possible_json["value"].encode("utf-8")])


def set_property(prop):
    prop_string = prop
    if prop_string not in valid_properties:
        _abort_bad_request() # bad request
    possible_json = request.get_json(force=True, silent=True)
    if not possible_json:
        _abort_bad_request() # bad request
    return _call_command(["set", prop_string, possible_json.encode("utf-8")])


def set_system_property():
    if (not request.json) or ("value" not in request.json):
        _abort_bad_request() # bad request

    if request.json["value"] in ["shutdown", "reboot"]:
        # Safe as input is limited
        subprocess.Popen("sleep 1; " + request.json["value"], shell=True)
        return jsonify(code=0, result="SUCCESS")

    return _call_command([request.json["value"]])


def register(app):
    app.add_url_rule(
        rule='/admin/api/<prop>',
        endpoint='get_property',
        methods=['GET'],
        view_func=get_property)
    app.add_url_rule(
        rule='/admin/api/system',
        endpoint='set_system_property',
        methods=['POST'],
        view_func=set_system_property)
    app.add_url_rule(
        rule='/admin/api/ui-config',
        endpoint='set_property',
        methods=['PUT'],
        view_func=set_property)
    app.add_url_rule(
        rule='/admin/api/<prop>',
        endpoint='set_property_value_wrapped',
        methods=['PUT'],
        view_func=set_property_value_wrapped)
