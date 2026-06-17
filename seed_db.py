"""schema.sql + seed.sql 을 MySQL에 적용합니다.

주의: 모든 테이블을 DROP/TRUNCATE 합니다. 기존 DB 데이터가 전부 삭제됩니다.
일반 앱 실행(run.py) 시에는 이 스크립트를 실행하지 마세요.
"""
import pathlib
import sys

import pymysql

from app.config import Config

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
    print(f"Connecting to MySQL: host={Config.DB_HOST}, user={Config.DB_USER}, db={Config.DB_NAME}")
    try:
        conn = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            charset=Config.DB_CHARSET,
        )
    except pymysql.err.OperationalError as exc:
        print("DB 연결 실패:", exc)
        print(".env 파일의 DB_HOST, DB_USER, DB_PASSWORD를 확인하세요.")
        sys.exit(1)

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
            )
            cursor.execute(f"USE `{Config.DB_NAME}`")
            run_sql_file(cursor, SCHEMA)
            run_sql_file(cursor, SEED)

            cursor.execute("SELECT COUNT(*) AS cnt FROM Users")
            users = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) AS cnt FROM Posts")
            posts = cursor.fetchone()[0]

        conn.commit()
        print(f"DB 초기화 완료: {Config.DB_NAME} (Users={users}, Posts={posts})")
    except Exception as exc:
        print("시드 적용 실패:", exc)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
