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
        ' nick varchar(256), message text, textDirection varchar(3))'))
    cursor.execute((
        'CREATE TABLE IF NOT EXISTS'
        ' message_stats (ltr integer, rtl integer)'))
    cursor.execute((
        'CREATE INDEX IF NOT EXISTS'
        ' timestamp_idx ON messages (timestamp)'))
    STATE['messages_table'] = sqlalchemy.schema.MetaData(
        STATE['conn'], reflect=True).tables['messages']
    STATE['stats_table'] = sqlalchemy.schema.MetaData(
        STATE['conn'], reflect=True).tables['message_stats']

    # Initialize the stats table
    row = cursor.execute('select count(*) from message_stats').fetchone()
    if not row[0]:
        ins = STATE['stats_table'].insert().values(ltr=0, rtl=0)
        cursor.execute(ins)

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
            'nick, message, textDirection FROM messages '
            'WHERE rowid > ? order by timestamp desc limit ? offset ?'),
                              [since, limit, offset]):
        message = dict()
        message['id'] = row[0]
        message['timestamp'] = row[1]
        message['nick'] = row[2]
        message['body'] = row[3]
        message['textDirection'] = row[4]
        results.append(message)
    return results

def query_defaultTextDirection():
    """
    Query text direction
    """
    cursor = STATE['conn']
    row = cursor.execute('select ltr, rtl from message_stats').fetchone()

    return 'ltr' if row[0] >= row[1] else 'rtl'

def insert_message(nick, message, textDirection):
    """
    Insert record
    """
    ins = STATE['messages_table'].insert().values(
        nick=nick, message=message, textDirection=textDirection)
    res = STATE['conn'].execute(ins)

    ltr = 1 if textDirection == 'ltr' else 0
    rtl = 1 if textDirection == 'rtl' else 0
    STATE['conn'].execute(
        'update message_stats set ltr = ltr + ?, rtl = rtl + ?',
        ltr, rtl)

    return {
        'id': res.lastrowid
    }
