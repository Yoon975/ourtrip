from flask import g
import pymysql

from app.config import Config


def get_db_config():
    return {
        "host": Config.DB_HOST,
        "user": Config.DB_USER,
        "password": Config.DB_PASSWORD,
        "db": Config.DB_NAME,
        "charset": Config.DB_CHARSET,
        "cursorclass": pymysql.cursors.DictCursor,
    }


def get_db():
    if "db" not in g:
        g.db = pymysql.connect(**get_db_config())
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
