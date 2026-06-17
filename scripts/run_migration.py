"""Run SQL migration files against the configured database."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app
from app.db import get_db


def run_sql_file(path: Path):
    sql = path.read_text(encoding="utf-8")
    statements = [part.strip() for part in sql.split(";") if part.strip()]
    db = get_db()
    with db.cursor() as cursor:
        for statement in statements:
            try:
                cursor.execute(statement)
            except Exception as exc:
                message = str(exc).lower()
                if "duplicate column" in message or "already exists" in message:
                    continue
                raise
    db.commit()
    print(f"Applied: {path.name}")


def main():
    app = create_app()
    with app.app_context():
        migration_dir = ROOT / "database" / "migrations"
        for path in sorted(migration_dir.glob("*.sql")):
            run_sql_file(path)


if __name__ == "__main__":
    main()
