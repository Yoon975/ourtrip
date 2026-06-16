from flask import g
import pymysql

db_config = {
    'host': 'localhost',       # 3.36.28.140 -> 강사님 서버
    'user': 'root',            # jmcoding
    'password': '1234',        # 123qwe!
    'db': 'our_trip_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(**db_config)
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()
