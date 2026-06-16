"""기존 seed 데이터는 유지한 채 model_sample_data.sql 만 추가 적용합니다."""
import pathlib
import sys

import pymysql

from app.config import Config

ROOT = pathlib.Path(__file__).resolve().parent
MODEL_SEED = ROOT / "database" / "model_sample_data.sql"


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
    if not MODEL_SEED.exists():
        print(f"{MODEL_SEED.name} 파일이 없습니다. 먼저 scripts/generate_model_sample_data.py 를 실행하세요.")
        sys.exit(1)

    print(f"Connecting to MySQL: host={Config.DB_HOST}, user={Config.DB_USER}, db={Config.DB_NAME}")
    try:
        conn = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset=Config.DB_CHARSET,
        )
    except pymysql.err.OperationalError as exc:
        print("DB 연결 실패:", exc)
        sys.exit(1)

    try:
        with conn.cursor() as cursor:
            run_sql_file(cursor, MODEL_SEED)

            cursor.execute("SELECT COUNT(*) AS cnt FROM Users")
            users = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) AS cnt FROM Posts")
            posts = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) AS cnt FROM Scraps")
            scraps = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) AS cnt FROM Comments")
            comments = cursor.fetchone()[0]

        conn.commit()
        print(
            f"모델 샘플 데이터 적용 완료: Users={users}, Posts={posts}, "
            f"Scraps={scraps}, Comments={comments}"
        )
    except Exception as exc:
        print("모델 샘플 데이터 적용 실패:", exc)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
