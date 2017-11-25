""" Database access module """
import sqlalchemy

STATE = {}
STATE['connected'] = False

def connected():
    """ Returns true if connected """
    return STATE['connected']

def open_connection(conn_info):
    """ Open database connection """
    STATE['conn'] = sqlalchemy.create_engine(conn_info)
    STATE['connected'] = True

def setup():
    """ Setup the database """
    cursor = STATE['conn']
    cursor.execute((
        'CREATE TABLE IF NOT EXISTS'
        ' messages (timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,'
        ' handle varchar(256), message text)'))
    cursor.execute((
        'CREATE INDEX IF NOT EXISTS'
        ' timestamp_idx ON messages (timestamp)'))

def commit():
    """ Commit """
    STATE['conn'].commit()

def close():
    """ Close database connection """
    STATE['conn'].close()
    del STATE['conn']
    del STATE['cursor']
    STATE['connected'] = False

def record_count():
    """ Queries count of messages """

    row = STATE['conn'].execute(
        'select count(*) from messages').fetchone()
    return row[0]

def delete_records(max_age=3):
    """ Delete stale records """

    STATE['conn'].execute((
        'delete from messages where '
        '24 * (julianday(\'now\') - julianday(timestamp)) > ?'), [max_age])

def query_messages(since=0, limit=25, offset=0):
    """
    Query record count for a given date and resource
    """
    cursor = STATE['conn']
    results = []
    for row in cursor.execute((
            'SELECT rowid, cast(strftime(\'%s\', timestamp) as integer), '
            'handle, message FROM messages '
            'WHERE rowid >= ? order by timestamp desc limit ? offset ?'),
                              [since, limit, offset]):
        message = dict()
        message['id'] = row[0]
        message['timestamp'] = row[1]
        message['handle'] = row[2]
        message['body'] = row[3]
        results.append(message)
    return results

def insert_message(handle, message):
    """
    Insert record
    """
    STATE['conn'].execute('INSERT INTO messages (handle, message) VALUES (?,?)', [handle, message])
    row = STATE['conn'].execute('SELECT max(rowid) from messages').fetchone()
    row = STATE['conn'].execute((
        'SELECT rowid, cast(strftime(\'%s\', timestamp) as integer), '
        'handle, message from messages where rowid = ?'), [row[0]]).fetchone()
    message = dict()
    message['id'] = row[0]
    message['timestamp'] = row[1]
    message['handle'] = row[2]
    message['body'] = row[3]
    return message
