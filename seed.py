import psycopg
import uuid
from datetime import datetime, timezone

DB_URL = "postgresql://postgres:testpass@localhost:5433/postgres"
past_date = datetime(2026, 3, 20, tzinfo=timezone.utc)

with psycopg.connect(DB_URL) as conn:
    with conn.cursor() as cur:
        cur.execute("TRUNCATE safety_reports CASCADE")
        cur.execute("TRUNCATE app_users CASCADE")
        
        user_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO app_users (id, clerk_user_id, created_at) VALUES (%s, %s, %s)", 
            (user_id, "test_user_final", past_date)
        )
        
        # The Starting Coordinate
        base_lon = -0.1278
        base_lat = 51.5074
        
        # Seed 3 distinct crimes, spaced a few meters apart!
        for i in range(3):
            # Jitter the coordinates so the API counts EVERY single one
            lon = base_lon + (i * 0.0001)
            lat = base_lat + (i * 0.0001)
            
            cur.execute("""
                INSERT INTO safety_reports (id, user_id, category, severity, summary, details, location, created_at)
                VALUES (%s, %s, 'violent-crime', 'high', 'E2E', 'Jitter Fix', ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s)
            """, (str(uuid.uuid4()), user_id, lon, lat, past_date))
        
    conn.commit()
    print("Success! 3 uniquely scattered crimes seeded. The API cannot ignore this.")