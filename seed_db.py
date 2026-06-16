"""schema.sql + seed.sql 을 MySQL에 적용합니다."""
import pathlib

import pymysql

from app.db import db_config

ROOT = pathlib.Path(__file__).resolve().parent
SCHEMA = ROOT / "database" / "schema.sql"
SEED = ROOT / "database" / "seed.sql"


def _clean_line(line):
    if "--" in line:
        return line.split("--", 1)[0]
    return line


def run_sql_file(cursor, path):
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cleaned = _clean_line(line).strip()
        if cleaned:
            lines.append(cleaned)

    for statement in " ".join(lines).split(";"):
        stmt = statement.strip()
        if stmt:
            cursor.execute(stmt)


def main():
    conn = pymysql.connect(
        host=db_config["host"],
        user=db_config["user"],
        password=db_config["password"],
        charset=db_config["charset"],
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "CREATE DATABASE IF NOT EXISTS our_trip_db "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
            )
            cursor.execute("USE our_trip_db")
            run_sql_file(cursor, SCHEMA)
            run_sql_file(cursor, SEED)
        conn.commit()
        print("DB 초기화 완료: our_trip_db")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
