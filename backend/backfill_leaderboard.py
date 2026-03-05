"""
backfill_leaderboard.py
-----------------------
One-time script to:
1. Find all community test attempts (test_id IS NOT NULL) that are 
   timed out (IN_PROGRESS but timer expired) or SUBMITTED but missing 
   leaderboard entries.
2. Score them and write TestLeaderboard entries.

Run once:  python backfill_leaderboard.py
"""

import json
from datetime import datetime, timezone
from database import get_db, init_db
from models import TestAttempt, QuestionResponse, TestLeaderboard

def score_attempt(attempt, responses):
    total_score = 0
    max_score = 0
    correct_count = 0
    wrong_count = 0
    unattempted_count = 0

    for r in responses:
        max_score += r.marks_correct
        if r.user_answer is None or r.user_answer == "":
            unattempted_count += 1
        elif r.user_answer == r.correct_answer:
            correct_count += 1
            total_score += r.marks_correct
            r.is_correct = True
            r.marks_obtained = r.marks_correct
        else:
            wrong_count += 1
            total_score += r.marks_wrong
            r.is_correct = False
            r.marks_obtained = r.marks_wrong

    return total_score, max_score, correct_count, wrong_count, unattempted_count


def main():
    init_db()
    db = next(get_db())

    # Find all community attempts (test_id is set)
    attempts = db.query(TestAttempt).filter(TestAttempt.test_id.isnot(None)).all()
    print(f"Found {len(attempts)} community test attempts")

    processed = 0
    for attempt in attempts:
        responses = db.query(QuestionResponse).filter(
            QuestionResponse.test_attempt_id == attempt.id
        ).all()

        now = datetime.now(timezone.utc)

        # Check if timed out but not submitted
        started = attempt.started_at
        if started and started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)

        is_timed_out = (
            attempt.status == "IN_PROGRESS" and
            started is not None and
            (now - started).total_seconds() > attempt.duration_minutes * 60
        )

        # Process if: timed out OR submitted but missing leaderboard
        if is_timed_out:
            print(f"  Auto-submitting timed-out attempt {attempt.id} (user: {attempt.user_id})")
            total_score, max_score, correct_count, wrong_count, unattempted_count = score_attempt(attempt, responses)

            attempt.status = "SUBMITTED"
            attempt.submitted_at = now
            attempt.total_score = total_score
            attempt.max_score = max_score
            attempt.correct_count = correct_count
            attempt.wrong_count = wrong_count
            attempt.unattempted_count = unattempted_count
            db.commit()

        elif attempt.status != "SUBMITTED":
            continue

        # Now try to write leaderboard entry
        existing = db.query(TestLeaderboard).filter(
            TestLeaderboard.test_id == attempt.test_id,
            TestLeaderboard.user_id == attempt.user_id
        ).first()

        submitted_at = attempt.submitted_at or now
        if submitted_at.tzinfo is None:
            submitted_at = submitted_at.replace(tzinfo=timezone.utc)

        started_at = attempt.started_at
        if started_at and started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)

        time_taken = int((submitted_at - started_at).total_seconds()) if started_at else attempt.duration_minutes * 60
        total_attempted = (attempt.correct_count or 0) + (attempt.wrong_count or 0)
        accuracy = ((attempt.correct_count or 0) / total_attempted * 100) if total_attempted > 0 else 0

        if not existing:
            db.add(TestLeaderboard(
                test_id=attempt.test_id,
                user_id=attempt.user_id,
                score=attempt.total_score or 0,
                time_taken_seconds=time_taken,
                accuracy=accuracy,
                submitted_at=submitted_at
            ))
            print(f"  + Created leaderboard entry for attempt {attempt.id} (score: {attempt.total_score})")
            processed += 1
        elif (attempt.total_score or 0) > existing.score:
            existing.score = attempt.total_score or 0
            existing.time_taken_seconds = time_taken
            existing.accuracy = accuracy
            existing.submitted_at = submitted_at
            print(f"  ~ Updated leaderboard entry for attempt {attempt.id} (score: {attempt.total_score})")
            processed += 1

    db.commit()
    print(f"\n✅ Done. Processed {processed} leaderboard entries.")


if __name__ == "__main__":
    main()
