import sqlite3
from pathlib import Path

DDL_PATH = Path("schema_sqlite.sql")  # paste SQLite DDL into this file

def main():
    db_path = Path("db.sqlite3")
    conn = sqlite3.connect(db_path.as_posix())
    conn.execute("PRAGMA foreign_keys=ON;")
    ddl = DDL_PATH.read_text(encoding="utf-8")
    conn.executescript(ddl)
    conn.commit()
    conn.close()
    print(f"OK: initialized {db_path}")

if __name__ == "__main__":
    main()
