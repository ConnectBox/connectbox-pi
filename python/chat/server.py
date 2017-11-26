from flask import jsonify, request
import datasource

def add_message(message):
    return datasource.insert_message(message['handle'], message['body'])

def get_messages(max_id=None):
    return datasource.query_messages(since=max_id)

def cleanup_messages():
    before = datasource.record_count()
    datasource.delete_records()
    after = datasource.record_count()
    return before - after

def messages_endpoint():
    result = None
    if request.method == 'GET':
        max_id = request.args.get('max_id', 0)
        result = get_messages(max_id=max_id)
    elif request.method == 'POST':
        payload = request.json or {}
        result = add_message(payload)
    elif request.method == 'DELETE':
        # Only allow cleanup from 127.0.0.1
        if request.host != '127.0.0.1:5000':
            res = jsonify({'result': 'Method Not Allowed'})
            res.status_code = 405
            return res
        result = cleanup_messages()

    return jsonify({'result': result})

def register(app, chat_connection_info):
    datasource.open_connection(chat_connection_info())
    datasource.setup()
    app.add_url_rule(
        rule='/chat/messages',
        endpoint='messages_endpoint',
        methods=['GET', 'POST', 'DELETE'],
        view_func=messages_endpoint)
