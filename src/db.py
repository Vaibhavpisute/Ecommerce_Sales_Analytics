"""Database helpers. All settings come from the .env file (see .env.example)."""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

load_dotenv()


def get_engine(db_name=None):
    """Return a SQLAlchemy engine for the pipeline PostgreSQL server.

    db_name: database to use. Default is the analytics database (ANALYTICS_DB).
    """
    url = URL.create(
        "postgresql+psycopg2",
        username=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
        host=os.environ.get("PG_HOST", "localhost"),
        port=int(os.environ.get("PG_PORT", 5433)),
        database=db_name or os.environ["ANALYTICS_DB"],
    )
    return create_engine(url, future=True)


def ensure_database(db_name):
    """Create the database if it does not exist yet (uses the default 'postgres' database)."""
    engine = get_engine("postgres").execution_options(isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": db_name}).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
            print(f"Created database {db_name}")
        else:
            print(f"Database {db_name} already exists")


def run_sql_file(engine, path):
    """Run a .sql file (several statements) in one transaction."""
    with open(path, encoding="utf-8") as f:
        sql = f.read()
    raw = engine.raw_connection()
    try:
        raw.cursor().execute(sql)
        raw.commit()
    finally:
        raw.close()


def copy_df(engine, df, table):
    """Fast bulk load of a DataFrame into an existing table with COPY. Missing values become NULL."""
    import io

    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, na_rep="")
    buf.seek(0)
    cols = ", ".join(f'"{c}"' for c in df.columns)
    raw = engine.raw_connection()
    try:
        raw.cursor().copy_expert(f'COPY {table} ({cols}) FROM STDIN WITH (FORMAT csv)', buf)
        raw.commit()
    finally:
        raw.close()


if __name__ == "__main__":
    with get_engine().connect() as c:
        print("Connected to:", c.execute(text("select current_database(), version()")).fetchone())
