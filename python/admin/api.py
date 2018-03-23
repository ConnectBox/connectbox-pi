import os,subprocess
from flask import Flask,request,abort,jsonify

valid_properties = ["ssid", "channel", "hostname", "staticsite", "password", "system", "ui-config"]
    

def _call_command(extra_args):
    cmd_args = ["sudo", "/usr/local/connectbox/bin/ConnectBoxManage.sh"]
    called_cmd = subprocess.run(cmd_args + extra_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if called_cmd.returncode == 0:
        return jsonify(code=0, result=called_cmd.stdout.decode("utf-8").strip())
    else:
        return jsonify(code=called_cmd.returncode, result=called_cmd.stderr.decode("utf-8").strip())


def get_property(prop):
    prop_string = prop
    if prop_string not in valid_properties:
        abort(405)
    return _call_command(["get", prop_string])


def set_property(prop):
    prop_string = prop
    if prop_string not in valid_properties:
        abort(400) # bad request
    if not request.json:
        abort(400) # bad request
    return _call_command(["set", prop_string])


def set_system_property():
    if (not request.json) or ("value" not in request.json):
        abort(400) # bad request

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
        rule='/admin/api/<prop>',
        endpoint='set_property',
        methods=['PUT'],
        view_func=set_property)
