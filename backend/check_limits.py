import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv("backend/.env")
db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("No DATABASE_URL found.")
else:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        res = conn.execute(text("""
SELECT u.email, u.bonus_limit, u.monthly_bonus_limit,
       COALESCE(SUM(pc.bonus_limit), 0) as expected_bonus
FROM users u
LEFT JOIN promo_code_usages pcu ON pcu.user_id = u.id
LEFT JOIN promo_codes pc ON pc.id = pcu.promo_code_id
WHERE u.bonus_limit > 0 OR u.monthly_bonus_limit > 0 OR pcu.id IS NOT NULL
GROUP BY u.email, u.bonus_limit, u.monthly_bonus_limit;
"""))
        for row in res.fetchall():
            print(f"User {row[0]}: DB Bonus={row[1]}, Monthly={row[2]}, Expected from Usage={row[3]}")
