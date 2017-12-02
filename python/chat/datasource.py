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
    STATE['messages_table'] = sqlalchemy.schema.MetaData(
        STATE['conn'], reflect=True).tables['messages']
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

def delete_records(max_age_hours=3):
    """ Delete stale records """

    STATE['conn'].execute((
        'delete from messages where '
        '24 * (julianday(\'now\') - julianday(timestamp)) > ?'), [max_age_hours])

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
    ins = STATE['messages_table'].insert().values(handle=handle, message=message)
    res = STATE['conn'].execute(ins)
    return {
        'id': res.lastrowid
    }
