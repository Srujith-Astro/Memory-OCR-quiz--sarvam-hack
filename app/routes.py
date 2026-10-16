import os
import json
import uuid
import shutil
from datetime import datetime, date, timedelta
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from app.config import UPLOADS_DIR
from app.database import get_db, calculate_level, award_xp, seed_demo_data
from app.models import (
    GenerateRequest,
    SaveGeneratedRequest,
    ReviewCardRequest,
    QuizAttemptRequest,
    SettingsUpdateRequest
)
from app.sarvam_service import perform_ocr, generate_study_materials

router = APIRouter(prefix="/api")

# ----------------- HOME / DASHBOARD -----------------
@router.get("/dashboard")
def get_dashboard():
    conn = get_db()
    cursor = conn.cursor()
    today_str = date.today().isoformat()

    # User stats
    cursor.execute("SELECT * FROM user_stats WHERE id = 1")
    stats_row = cursor.fetchone()
    stats = dict(stats_row) if stats_row else {}

    xp = stats.get("xp", 0)
    level, title, base_xp, next_xp = calculate_level(xp)

    # Flashcards due
    cursor.execute("SELECT COUNT(*) as cnt FROM flashcards WHERE due_date <= ?", (today_str,))
    cards_due = cursor.fetchone()["cnt"]

    # New flashcards (repetitions == 0)
    cursor.execute("SELECT COUNT(*) as cnt FROM flashcards WHERE repetitions = 0")
    new_cards = cursor.fetchone()["cnt"]

    # Total flashcards
    cursor.execute("SELECT COUNT(*) as cnt FROM flashcards")
    total_cards = cursor.fetchone()["cnt"]

    # Total notes
    cursor.execute("SELECT COUNT(*) as cnt FROM notes")
    total_notes = cursor.fetchone()["cnt"]

    # Total quizzes
    cursor.execute("SELECT COUNT(*) as cnt FROM quizzes")
    total_quizzes = cursor.fetchone()["cnt"]

    # Recent notes
    cursor.execute("SELECT id, title, subject, source_type, created_at, is_demo FROM notes ORDER BY id DESC LIMIT 5")
    recent_notes = [dict(r) for r in cursor.fetchall()]

    # Weak topics: subjects where card ease_factor is low or quiz accuracy < 60%
    cursor.execute("""
        SELECT subject, AVG(ease_factor) as avg_ease, COUNT(*) as card_count
        FROM flashcards
        GROUP BY subject
        HAVING avg_ease < 2.3
        ORDER BY avg_ease ASC
        LIMIT 3
    """)
    weak_topics = [dict(r) for r in cursor.fetchall()]

    # Weekly history (past 7 days)
    history_raw = json.loads(stats.get("weekly_history_json") or "{}")
    weekly_activity = []
    for i in range(6, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        day_name = (date.today() - timedelta(days=i)).strftime("%a")
        weekly_activity.append({
            "date": d,
            "day": day_name,
            "count": history_raw.get(d, 0)
        })

    conn.close()

    return {
        "xp": xp,
        "level": level,
        "level_title": title,
        "base_xp": base_xp,
        "next_xp": next_xp,
        "streak_count": stats.get("streak_count", 1),
        "cards_reviewed_today": stats.get("cards_reviewed_today", 0),
        "daily_goal": stats.get("daily_goal", 15),
        "cards_due": cards_due,
        "new_cards": new_cards,
        "total_cards": total_cards,
        "total_notes": total_notes,
        "total_quizzes": total_quizzes,
        "weekly_activity": weekly_activity,
        "recent_notes": recent_notes,
        "weak_topics": weak_topics
    }

# ----------------- KNOWLEDGE / NOTES -----------------
@router.get("/notes")
def get_notes(subject: str = Query(None)):
    conn = get_db()
    cursor = conn.cursor()
    if subject:
        cursor.execute("SELECT * FROM notes WHERE subject = ? ORDER BY id DESC", (subject,))
    else:
        cursor.execute("SELECT * FROM notes ORDER BY id DESC")
    notes = [dict(r) for r in cursor.fetchall()]

    # Attach counts of flashcards and quizzes
    for n in notes:
        cursor.execute("SELECT COUNT(*) as cnt FROM flashcards WHERE note_id = ?", (n["id"],))
        n["flashcard_count"] = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM quizzes WHERE note_id = ?", (n["id"],))
        n["quiz_count"] = cursor.fetchone()["cnt"]

    conn.close()
    return notes

@router.get("/notes/{note_id}")
def get_note_detail(note_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Note not found")

    note = dict(row)
    if note.get("ocr_blocks_json"):
        try:
            note["ocr_blocks"] = json.loads(note["ocr_blocks_json"])
        except:
            note["ocr_blocks"] = []

    # Get linked flashcards
    cursor.execute("SELECT * FROM flashcards WHERE note_id = ?", (note_id,))
    note["flashcards"] = [dict(r) for r in cursor.fetchall()]

    # Get linked quizzes
    cursor.execute("SELECT * FROM quizzes WHERE note_id = ?", (note_id,))
    quizzes = []
    for q in cursor.fetchall():
        qd = dict(q)
        try:
            qd["options"] = json.loads(qd["options_json"])
        except:
            qd["options"] = []
        quizzes.append(qd)
    note["quizzes"] = quizzes

    conn.close()
    return note

@router.delete("/notes/{note_id}")
def delete_note(note_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM flashcards WHERE note_id = ?", (note_id,))
    cursor.execute("DELETE FROM quizzes WHERE note_id = ?", (note_id,))
    cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()
    return {"message": "Note and associated materials deleted successfully"}

# ----------------- OCR EXTRACTION -----------------
@router.post("/ocr")
async def upload_for_ocr(
    file: UploadFile = File(...),
    content_type: str = Form("handwritten"),
    language: str = Form("en-IN")
):
    """Processes uploaded photo/document with Sarvam Doc AI digitise"""
    filename = file.filename or f"upload_{uuid.uuid4().hex[:8]}.jpg"
    file_bytes = await file.read()

    # Save to local uploads directory
    local_filename = f"{uuid.uuid4().hex[:12]}_{filename}"
    save_path = UPLOADS_DIR / local_filename
    with open(save_path, "wb") as f:
        f.write(file_bytes)

    try:
        ocr_result = perform_ocr(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
            language=language
        )
    except Exception as e:
        # If API or network error occurs, preserve uploaded file so user can manually type or retry
        return {
            "success": False,
            "error": str(e),
            "image_path": f"/uploads/{local_filename}",
            "full_text": "",
            "blocks": [],
            "message": "OCR encountered an issue, but your image was saved. You can type or paste notes manually."
        }

    return {
        "success": True,
        "image_path": f"/uploads/{local_filename}",
        "full_text": ocr_result["full_text"],
        "blocks": ocr_result["blocks"],
        "page_count": ocr_result.get("page_count", 1)
    }

# ----------------- AI GENERATION -----------------
@router.post("/generate")
def generate_study_items(payload: GenerateRequest):
    if not payload.text or len(payload.text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Text must contain at least 10 characters to generate study materials.")

    try:
        materials = generate_study_materials(
            study_text=payload.text,
            num_cards=payload.num_cards or 4,
            num_quizzes=payload.num_quizzes or 2,
            subject=payload.subject,
            target_language=payload.target_language or "auto"
        )
        return materials
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate study materials: {str(e)}")

@router.post("/notes/save-generated")
def save_generated_package(payload: SaveGeneratedRequest):
    conn = get_db()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    today_str = date.today().isoformat()

    # 1. Insert note
    cursor.execute("""
        INSERT INTO notes (title, subject, tags, source_type, image_path, raw_ocr_text, ocr_blocks_json, content, created_at, is_demo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (
        payload.title,
        payload.subject,
        payload.tags or "",
        payload.source_type,
        payload.image_path,
        payload.raw_ocr_text,
        payload.ocr_blocks_json,
        payload.content,
        now_str
    ))
    note_id = cursor.lastrowid

    # 2. Insert flashcards
    for card in payload.flashcards:
        cursor.execute("""
            INSERT INTO flashcards (note_id, subject, question, answer, explanation, tags, due_date, created_at, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            note_id,
            payload.subject,
            card.question,
            card.answer,
            card.explanation or "",
            card.tags or payload.tags or "",
            today_str,
            now_str
        ))

    # 3. Insert quizzes
    for q in payload.quizzes:
        cursor.execute("""
            INSERT INTO quizzes (note_id, subject, question, options_json, answer_index, explanation, created_at, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            note_id,
            payload.subject,
            q.question,
            json.dumps(q.options),
            q.answer_index,
            q.explanation or "",
            now_str
        ))

    # Award XP for note creation
    xp_result = award_xp(conn, 30, activity_type="note_create")

    # Update badge
    cursor.execute("SELECT unlocked_badges_json FROM user_stats WHERE id = 1")
    badges = set(json.loads(cursor.fetchone()["unlocked_badges_json"] or "[]"))
    badges.add("first_note")
    if payload.source_type == "image":
        badges.add("ocr_master")
    cursor.execute("UPDATE user_stats SET unlocked_badges_json = ? WHERE id = 1", (json.dumps(list(badges)),))

    conn.commit()
    conn.close()

    return {
        "note_id": note_id,
        "message": "Knowledge package saved successfully!",
        "xp_awarded": 30,
        "new_xp": xp_result["xp"]
    }

# ----------------- REVIEW & SPACED REPETITION -----------------
@router.get("/review/queue")
def get_review_queue(subject: str = Query(None)):
    conn = get_db()
    cursor = conn.cursor()
    today_str = date.today().isoformat()

    query = """
        SELECT f.*, n.title as note_title
        FROM flashcards f
        LEFT JOIN notes n ON f.note_id = n.id
        WHERE f.due_date <= ?
    """
    params = [today_str]
    if subject:
        query += " AND f.subject = ?"
        params.append(subject)

    query += " ORDER BY f.due_date ASC, f.id ASC LIMIT 50"

    cursor.execute(query, params)
    cards = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return cards

@router.post("/flashcards/{card_id}/review")
def review_flashcard(card_id: int, payload: ReviewCardRequest):
    """
    Implements SM-2 Spaced Repetition Algorithm.
    Grades:
    - 'again': reps=0, interval=1, ease down
    - 'hard': reps+=1, interval*=1.2, slight ease down
    - 'good': reps+=1, interval*=ease, maintain ease
    - 'easy': reps+=1, interval*=ease*1.3, ease up
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM flashcards WHERE id = ?", (card_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Flashcard not found")

    card = dict(row)
    reps = card["repetitions"]
    interval = card["interval_days"]
    ease = card["ease_factor"]
    grade = payload.grade.lower()

    xp_gained = 15
    if grade == "again":
        reps = 0
        interval = 1
        ease = max(1.3, ease - 0.2)
        xp_gained = 5
    elif grade == "hard":
        reps += 1
        interval = max(1, int(interval * 1.2)) if interval > 0 else 1
        ease = max(1.3, ease - 0.15)
        xp_gained = 10
    elif grade == "good":
        reps += 1
        if reps == 1:
            interval = 1
        elif reps == 2:
            interval = 6
        else:
            interval = max(1, int(interval * ease))
        xp_gained = 15
    elif grade == "easy":
        reps += 1
        if reps == 1:
            interval = 2
        elif reps == 2:
            interval = 8
        else:
            interval = max(1, int(interval * ease * 1.3))
        ease = min(3.0, ease + 0.15)
        xp_gained = 20

    next_due = (date.today() + timedelta(days=interval)).isoformat()
    now_str = datetime.now().isoformat()

    cursor.execute("""
        UPDATE flashcards
        SET repetitions = ?, interval_days = ?, ease_factor = ?, due_date = ?, last_reviewed = ?
        WHERE id = ?
    """, (reps, interval, ease, next_due, now_str, card_id))

    # Log review
    cursor.execute("""
        INSERT INTO study_logs (session_type, item_id, result, xp_earned, created_at)
        VALUES ('flashcard', ?, ?, ?, ?)
    """, (card_id, grade, xp_gained, now_str))

    # Award XP
    xp_info = award_xp(conn, xp_gained, activity_type="review")

    # Check 25 cards badge
    cursor.execute("SELECT COUNT(*) as cnt FROM study_logs WHERE session_type = 'flashcard'")
    if cursor.fetchone()["cnt"] >= 25:
        cursor.execute("SELECT unlocked_badges_json FROM user_stats WHERE id = 1")
        badges = set(json.loads(cursor.fetchone()["unlocked_badges_json"] or "[]"))
        badges.add("cards_25")
        cursor.execute("UPDATE user_stats SET unlocked_badges_json = ? WHERE id = 1", (json.dumps(list(badges)),))

    conn.commit()
    conn.close()

    return {
        "card_id": card_id,
        "next_due": next_due,
        "interval_days": interval,
        "xp_earned": xp_gained,
        "user_xp": xp_info["xp"],
        "level": xp_info["level"],
        "streak": xp_info["streak"]
    }

# ----------------- QUIZZES -----------------
@router.get("/quizzes")
def get_quizzes(subject: str = Query(None)):
    conn = get_db()
    cursor = conn.cursor()
    query = """
        SELECT q.*, n.title as note_title
        FROM quizzes q
        LEFT JOIN notes n ON q.note_id = n.id
    """
    params = []
    if subject:
        query += " WHERE q.subject = ?"
        params.append(subject)

    query += " ORDER BY q.id DESC"
    cursor.execute(query, params)

    quizzes = []
    for r in cursor.fetchall():
        item = dict(r)
        try:
            item["options"] = json.loads(item["options_json"])
        except:
            item["options"] = []
        quizzes.append(item)

    conn.close()
    return quizzes

@router.post("/quizzes/{quiz_id}/attempt")
def attempt_quiz(quiz_id: int, payload: QuizAttemptRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Quiz question not found")

    quiz = dict(row)
    is_correct = (payload.selected_index == quiz["answer_index"])
    now_str = datetime.now().isoformat()

    new_attempted = quiz["times_attempted"] + 1
    new_correct = quiz["times_correct"] + (1 if is_correct else 0)

    cursor.execute("""
        UPDATE quizzes
        SET times_attempted = ?, times_correct = ?, last_attempted = ?
        WHERE id = ?
    """, (new_attempted, new_correct, now_str, quiz_id))

    xp_gained = 25 if is_correct else 5

    # Log study attempt
    cursor.execute("""
        INSERT INTO study_logs (session_type, item_id, result, xp_earned, created_at)
        VALUES ('quiz', ?, ?, ?, ?)
    """, (quiz_id, "correct" if is_correct else "incorrect", xp_gained, now_str))

    xp_info = award_xp(conn, xp_gained, activity_type="quiz")

    # Check quiz ace badge
    if is_correct:
        cursor.execute("SELECT unlocked_badges_json FROM user_stats WHERE id = 1")
        badges = set(json.loads(cursor.fetchone()["unlocked_badges_json"] or "[]"))
        badges.add("quiz_ace")
        cursor.execute("UPDATE user_stats SET unlocked_badges_json = ? WHERE id = 1", (json.dumps(list(badges)),))

    conn.commit()
    conn.close()

    return {
        "is_correct": is_correct,
        "correct_index": quiz["answer_index"],
        "explanation": quiz["explanation"],
        "xp_earned": xp_gained,
        "user_xp": xp_info["xp"],
        "level": xp_info["level"],
        "streak": xp_info["streak"]
    }

# ----------------- PROGRESS & GAMIFICATION -----------------
@router.get("/progress")
def get_progress():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM user_stats WHERE id = 1")
    stats = dict(cursor.fetchone())
    xp = stats.get("xp", 0)
    level, title, base_xp, next_xp = calculate_level(xp)

    # Subject mastery breakdown
    cursor.execute("""
        SELECT subject,
               COUNT(*) as total_cards,
               SUM(CASE WHEN repetitions >= 3 THEN 1 ELSE 0 END) as mastered_cards,
               SUM(CASE WHEN repetitions BETWEEN 1 AND 2 THEN 1 ELSE 0 END) as learning_cards,
               SUM(CASE WHEN repetitions = 0 THEN 1 ELSE 0 END) as new_cards
        FROM flashcards
        GROUP BY subject
    """)
    mastery = [dict(r) for r in cursor.fetchall()]

    # Quiz accuracy by subject
    cursor.execute("""
        SELECT subject,
               SUM(times_attempted) as total_attempts,
               SUM(times_correct) as total_correct
        FROM quizzes
        GROUP BY subject
    """)
    quiz_stats = [dict(r) for r in cursor.fetchall()]

    # Badges catalog
    unlocked = set(json.loads(stats.get("unlocked_badges_json") or "[]"))
    all_badges = [
        {"id": "first_note", "title": "First Step", "desc": "Captured your first learning note", "icon": "file-text", "unlocked": "first_note" in unlocked},
        {"id": "first_review", "title": "Recall Spark", "desc": "Completed your first active recall session", "icon": "zap", "unlocked": "first_review" in unlocked},
        {"id": "first_quiz", "title": "Quiz Initiate", "desc": "Attempted your first interactive quiz", "icon": "award", "unlocked": "first_quiz" in unlocked},
        {"id": "streak_3", "title": "Flame Keeper", "desc": "Kept a study streak for 3+ consecutive days", "icon": "flame", "unlocked": "streak_3" in unlocked},
        {"id": "quiz_ace", "title": "Sharp Mind", "desc": "Answered a quiz challenge correctly", "icon": "target", "unlocked": "quiz_ace" in unlocked},
        {"id": "cards_25", "title": "Flashcard Adept", "desc": "Reviewed 25 or more flashcards", "icon": "layers", "unlocked": "cards_25" in unlocked},
        {"id": "ocr_master", "title": "Visionary", "desc": "Extracted handwriting or textbook with Sarvam Doc AI", "icon": "camera", "unlocked": "ocr_master" in unlocked},
        {"id": "xp_500", "title": "Memory Titan", "desc": "Earned over 500 Knowledge XP", "icon": "crown", "unlocked": "xp_500" in unlocked}
    ]

    conn.close()

    return {
        "xp": xp,
        "level": level,
        "level_title": title,
        "base_xp": base_xp,
        "next_xp": next_xp,
        "streak_count": stats.get("streak_count", 1),
        "cards_reviewed_today": stats.get("cards_reviewed_today", 0),
        "daily_goal": stats.get("daily_goal", 15),
        "mastery": mastery,
        "quiz_stats": quiz_stats,
        "badges": all_badges
    }

# ----------------- SETTINGS & BACKUP -----------------
@router.get("/settings")
def get_settings():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT daily_goal, theme FROM user_stats WHERE id = 1")
    s = dict(cursor.fetchone())
    conn.close()
    return s

@router.post("/settings")
def update_settings(payload: SettingsUpdateRequest):
    conn = get_db()
    cursor = conn.cursor()
    if payload.daily_goal is not None:
        cursor.execute("UPDATE user_stats SET daily_goal = ? WHERE id = 1", (payload.daily_goal,))
    if payload.theme is not None:
        cursor.execute("UPDATE user_stats SET theme = ? WHERE id = 1", (payload.theme,))
    conn.commit()
    conn.close()
    return {"message": "Settings updated"}

@router.post("/settings/reset-demo")
def reset_to_demo():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM flashcards")
    cursor.execute("DELETE FROM quizzes")
    cursor.execute("DELETE FROM notes")
    cursor.execute("DELETE FROM study_logs")
    cursor.execute("""
        UPDATE user_stats
        SET xp = 85, level = 1, streak_count = 3, cards_reviewed_today = 4,
            daily_goal = 15, unlocked_badges_json = '["first_review"]', weekly_history_json = '{}'
        WHERE id = 1
    """)
    seed_demo_data(cursor)
    conn.commit()
    conn.close()
    return {"message": "Sample demo data restored successfully"}

@router.get("/export")
def export_data():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes")
    notes = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM flashcards")
    flashcards = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM quizzes")
    quizzes = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM user_stats WHERE id = 1")
    stats = dict(cursor.fetchone())
    conn.close()
    return {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "stats": stats,
        "notes": notes,
        "flashcards": flashcards,
        "quizzes": quizzes
    }
