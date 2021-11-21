import base64,logging,subprocess
from flask import request,abort,jsonify,make_response

valid_properties = ["ssid", "brand", "client-ssid", "client-wifipassword", "channel", "hostname", "staticsite", "password",
                    "system", "ui-config", "wpa-passphrase", "openwell-download", "moodle_download"]

valid_brand_properties = ["Screen_Enable", "g_device", "server_url", "server_authorization", "server_sitename", 
                    "server_siteadmin_name", "server_siteadmin_email", "server_siteadmin_phone", "enable_mass_storage", 
                    "usb0NoMount", "enhanced"]

connectbox_version = 'dev'
try:
    with open('/etc/connectbox-release', 'r') as version_file:
        connectbox_version=version_file.read().replace('\n', '')
except Exception as err:
    logging.warn('Error reading release: %s' % str(err))

def _abort_bad_request():
    abort(make_response("BAD REQUEST", 400))

def _abort_unauthorized():
    abort(make_response("Unauthorized", 401))

def _call_command(extra_args):
    cmd_args = ["sudo", "/usr/local/connectbox/bin/ConnectBoxManage.sh"]
    called_cmd = subprocess.run(
        cmd_args + extra_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logging.debug("_call_command" + " ".join(cmd_args))
    result_string = called_cmd.stdout
    if called_cmd.returncode != 0:
        result_string = called_cmd.stderr

    res = jsonify(
        code=called_cmd.returncode, result=result_string.decode("utf-8").rstrip().split("\n"))
    res.headers['X-Connectbox-Version'] = connectbox_version

    return res

def _authenticate(req):
    logging.debug("_authenticate")
    try:
        auth_header = req.headers.get('Authorization')
        if auth_header:
            if auth_header.startswith("Basic "):
                decoded = base64.b64decode(auth_header.split()[1]).decode('utf-8')
                credentials = decoded.split(":")

                if len(credentials) == 2:
                    cmd_args = [
                        "sudo",
                        "/usr/local/connectbox/bin/ConnectBoxManage.sh",
                        "check", "password", credentials[1]]
                    called_cmd = subprocess.run(
                        cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if called_cmd.returncode == 0:
                        return
    except Exception as err:
        logging.warn('Error authenticating request: %s' % str(err))

    _abort_unauthorized()


def get_property(prop):
    logging.debug("get_property")
    _authenticate(request)

    prop_string = prop
    if prop_string not in valid_properties or prop_string == "password" or prop_string == "client-wifipassword":
        _abort_bad_request()
    return _call_command(["get", prop_string])

def get_brand_property(prop):
   logging.debug("get brand property")
   _authenticate(request)

   prop_string = prop
   if prop_string not in valid_brand_properties or prop_string == "server_authorization":
      _abort_bad_request()
   return _call_command(["get", "brand", prop_string])


def set_property_value_wrapped(prop):
    logging.debug("set_property_value_wrapped")
    _authenticate(request)

    prop_string = prop
    if prop_string not in valid_properties:
        _abort_bad_request() # bad request
    # we don't offer channel setting but the UI still exposes it. Stub it out
    #  until the UI is updated
    if prop_string == "channel":
        res = jsonify(code=0, result="Setting channel no longer supported")
        res.headers['X-Connectbox-Version'] = connectbox_version
        return res

    possible_json = request.get_json(force=True, silent=True)
    if (not possible_json) or ("value" not in possible_json):
        _abort_bad_request() # bad request
    return _call_command(["set", prop_string, possible_json["value"].encode("utf-8")])

def set_property(prop):
    logging.debug("set_property")
    _authenticate(request)

    prop_string = prop
    if prop_string not in valid_brand_properties:
        _abort_bad_request() # bad request

    string_data = request.get_data(as_text=True)
    if not string_data:
        _abort_bad_request() # bad request

    return _call_command(["set", prop_string, string_data.encode("utf-8")])

def set_system_property():
    logging.debug("set_system_property")
    _authenticate(request)

    if (not request.json) or ("value" not in request.json):
        _abort_bad_request() # bad request

    if not request.json["value"] in ["shutdown", "reboot", "unmountusb", "reset"]:
        _abort_bad_request() # bad request

    return _call_command([request.json["value"]])

def not_authorized():
    _abort_unauthorized()

def register(app):
    app.add_url_rule(
        rule='/admin/api',
        endpoint='not_authorized',
        view_func=not_authorized)
    app.add_url_rule(
        rule='/admin/api/',
        endpoint='not_authorized',
        view_func=not_authorized)
    app.add_url_rule(
        rule='/admin/api/brand/<prop>',
        endpoint='get_brand_property',
        methods=['GET'],
        view_func=get_brand_property)
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
        defaults={'prop': 'ui-config'},
        endpoint='set_property',
        methods=['PUT'],
        view_func=set_property)
    app.add_url_rule(
        rule='/admin/api/<prop>',
        endpoint='set_property_value_wrapped',
        methods=['PUT'],
        view_func=set_property_value_wrapped)
