# seed some sample reports for the demo, run after migrations

import os
import random
import uuid
from datetime import datetime, timedelta, timezone

import psycopg
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://afterhours:afterhours@localhost:5432/afterhours",
).replace("+psycopg", "")

# birmingham city centre, roughly
BASE_LAT = 52.4814
BASE_LNG = -1.8998

REPORTS = [
    ("assault", "high", "Assault reported near Broad Street", "A group was involved in an altercation outside a bar late at night"),
    ("robbery", "high", "Phone snatched on New Street", "Someone grabbed a phone from a pedestrian and ran towards the station"),
    ("harassment", "high", "Verbal harassment near Bullring", "A person was followed and verbally harassed while walking alone"),
    ("theft", "high", "Bike stolen from Digbeth", "Bike was cut from a rack outside a cafe, happened during the afternoon"),
    ("suspicious activity", "medium", "Suspicious behaviour near Five Ways", "A group hanging around parked cars trying door handles"),
    ("poor lighting", "medium", "Dark underpass near Selly Oak", "The underpass on the canal path has no working lights at all"),
    ("poor lighting", "medium", "Broken streetlights on Pershore Road", "Three streetlights in a row are out, makes the pavement pitch black"),
    ("unsafe crossing", "medium", "Dangerous crossing at Bristol Road", "No pedestrian lights and cars go really fast here especially at night"),
    ("hazard", "low", "Flooding on canal towpath", "The path floods badly after rain, nearly slipped over twice"),
    ("other", "low", "Abandoned shopping trolleys blocking path", "Trolleys dumped on the path near Edgbaston reservoir, hard to get past"),
    ("harassment", "high", "Catcalling near Jewellery Quarter", "Multiple reports of catcalling on Vyse Street in the evenings"),
    ("suspicious activity", "medium", "Van circling residential streets", "A white van was seen circling Harborne streets slowly after midnight"),
    ("poor lighting", "medium", "Park path unlit after sunset", "The path through Cannon Hill Park has no lighting past the car park"),
    ("assault", "high", "Fight outside a takeaway in Digbeth", "Two people fighting, one had a bottle, happened around 1am"),
    ("theft", "high", "Bag stolen on the 50 bus", "Someone took a bag from the overhead rack on the bus towards Moseley"),
]


def jitter():
    # spread reports within about 2km of the centre
    return random.uniform(-0.015, 0.015)


def seed():
    now = datetime.now(tz=timezone.utc)
    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()

    # make a demo user for the reports, or grab the existing one
    cur.execute("SELECT id FROM app_users WHERE clerk_user_id = 'demo-user'")
    row = cur.fetchone()
    if row:
        user_id = str(row[0])
    else:
        user_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO app_users (id, clerk_user_id, created_at) VALUES (%s, %s, %s)",
            (user_id, "demo-user", now),
        )

    # check if we already seeded (avoid duplicates on re-run)
    cur.execute("SELECT COUNT(*) FROM safety_reports WHERE summary LIKE '%%near%%' OR summary LIKE '%%on%%'")
    existing = cur.fetchone()[0]
    if existing >= len(REPORTS):
        print(f"already have {existing} reports, skipping seed")
        conn.close()
        return

    count = 0
    for i, (category, severity, summary, details) in enumerate(REPORTS):
        lat = BASE_LAT + jitter()
        lng = BASE_LNG + jitter()
        # spread timestamps over the last couple of weeks
        created = now - timedelta(days=random.randint(0, 14), hours=random.randint(0, 23))
        cur.execute(
            """
            INSERT INTO safety_reports (id, user_id, category, severity, summary, details, location, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s)
            """,
            (str(uuid.uuid4()), user_id, category, severity, summary, details, lng, lat, created),
        )
        count += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"seeded {count} sample reports around birmingham")


if __name__ == "__main__":
    seed()
