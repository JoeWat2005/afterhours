import psycopg

DB_URL = "postgresql://postgres:testpass@localhost:5433/postgres"

with psycopg.connect(DB_URL) as conn:
    conn.execute("TRUNCATE safety_reports CASCADE")
    conn.commit()
    print("Black hole cleared! The database is empty.")