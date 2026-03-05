"""
backfill_leaderboard_direct.py
One-time script using direct psycopg2 — no app imports needed.
Run: python backfill_leaderboard_direct.py
"""

import psycopg2
from datetime import datetime, timezone

DATABASE_URL = "postgresql://postgres:priyanshuaws123@infinitest.cuf8es4uybc1.us-east-1.rds.amazonaws.com:5432/infinitest"

def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Find all community attempts (test_id IS NOT NULL) that are IN_PROGRESS and timed out
    cur.execute("""
        SELECT id, user_id, test_id, status, started_at, duration_minutes
        FROM test_attempts
        WHERE test_id IS NOT NULL
        AND (
            status = 'IN_PROGRESS'
            OR (status = 'SUBMITTED' AND id NOT IN (
                SELECT DISTINCT tl.user_id
                FROM test_leaderboard tl
                WHERE tl.test_id = test_attempts.test_id
                AND tl.user_id = test_attempts.user_id
            ))
        )
    """)
    attempts = cur.fetchall()
    print(f"Found {len(attempts)} community attempts to process")

    now = datetime.now(timezone.utc)
    processed = 0

    for attempt_id, user_id, test_id, status, started_at, duration_minutes in attempts:
        # Check if timed out
        if status == 'IN_PROGRESS':
            if started_at is None:
                continue
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            elapsed = (now - started_at).total_seconds()
            if elapsed < duration_minutes * 60:
                print(f"  Skipping {attempt_id} — still in progress ({int(elapsed)}s elapsed)")
                continue

            # Score all responses
            cur.execute("""
                SELECT user_answer, correct_answer, marks_correct, marks_wrong
                FROM question_responses
                WHERE test_attempt_id = %s
            """, (attempt_id,))
            responses = cur.fetchall()

            total_score = 0
            max_score = 0
            correct_count = 0
            wrong_count = 0
            unattempted_count = 0

            for user_answer, correct_answer, marks_correct, marks_wrong in responses:
                max_score += marks_correct
                if not user_answer:
                    unattempted_count += 1
                elif user_answer == correct_answer:
                    correct_count += 1
                    total_score += marks_correct
                else:
                    wrong_count += 1
                    total_score += marks_wrong

            submitted_at = now
            cur.execute("""
                UPDATE test_attempts
                SET status='SUBMITTED', submitted_at=%s, total_score=%s, max_score=%s,
                    correct_count=%s, wrong_count=%s, unattempted_count=%s
                WHERE id=%s
            """, (submitted_at, total_score, max_score, correct_count, wrong_count, unattempted_count, attempt_id))
            print(f"  ✓ Auto-submitted {attempt_id} (score: {total_score}/{max_score})")

        else:
            # Already submitted — get the score
            cur.execute("""
                SELECT total_score, max_score, correct_count, wrong_count, submitted_at
                FROM test_attempts WHERE id=%s
            """, (attempt_id,))
            row = cur.fetchone()
            if not row:
                continue
            total_score, max_score, correct_count, wrong_count, submitted_at = row

        # Write leaderboard entry
        if started_at is None:
            cur.execute("SELECT started_at FROM test_attempts WHERE id=%s", (attempt_id,))
            started_at = cur.fetchone()[0]

        if submitted_at is None:
            submitted_at = now

        if started_at and submitted_at:
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            if submitted_at.tzinfo is None:
                submitted_at = submitted_at.replace(tzinfo=timezone.utc)
            time_taken = int((submitted_at - started_at).total_seconds())
        else:
            time_taken = duration_minutes * 60

        total_attempted = (correct_count or 0) + (wrong_count or 0)
        accuracy = ((correct_count or 0) / total_attempted * 100) if total_attempted > 0 else 0

        cur.execute("""
            SELECT id, score FROM test_leaderboard
            WHERE test_id=%s AND user_id=%s
        """, (test_id, user_id))
        existing = cur.fetchone()

        if not existing:
            cur.execute("""
                INSERT INTO test_leaderboard (id, test_id, user_id, score, time_taken_seconds, accuracy, submitted_at)
                VALUES (gen_random_uuid()::text, %s, %s, %s, %s, %s, %s)
            """, (test_id, user_id, total_score or 0, time_taken, accuracy, submitted_at))
            print(f"  + Leaderboard entry created for {attempt_id} (score: {total_score})")
            processed += 1
        elif (total_score or 0) > existing[1]:
            cur.execute("""
                UPDATE test_leaderboard
                SET score=%s, time_taken_seconds=%s, accuracy=%s, submitted_at=%s
                WHERE id=%s
            """, (total_score, time_taken, accuracy, submitted_at, existing[0]))
            print(f"  ~ Leaderboard entry updated for {attempt_id} (score: {total_score})")
            processed += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"\n✅ Done. Created/updated {processed} leaderboard entries.")

if __name__ == "__main__":
    main()
