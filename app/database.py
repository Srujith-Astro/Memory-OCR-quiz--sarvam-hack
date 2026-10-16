import sqlite3
import json
from datetime import datetime, date, timedelta
from app.config import DB_PATH

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        subject TEXT NOT NULL,
        tags TEXT,
        source_type TEXT NOT NULL, -- 'text' or 'image'
        image_path TEXT,
        raw_ocr_text TEXT,
        ocr_blocks_json TEXT,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        is_demo INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS flashcards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id INTEGER,
        subject TEXT NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        explanation TEXT,
        tags TEXT,
        ease_factor REAL DEFAULT 2.5,
        interval_days INTEGER DEFAULT 0,
        repetitions INTEGER DEFAULT 0,
        due_date TEXT NOT NULL,
        last_reviewed TEXT,
        created_at TEXT NOT NULL,
        is_demo INTEGER DEFAULT 0,
        FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS quizzes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id INTEGER,
        subject TEXT NOT NULL,
        question TEXT NOT NULL,
        options_json TEXT NOT NULL,
        answer_index INTEGER NOT NULL,
        explanation TEXT,
        times_attempted INTEGER DEFAULT 0,
        times_correct INTEGER DEFAULT 0,
        last_attempted TEXT,
        created_at TEXT NOT NULL,
        is_demo INTEGER DEFAULT 0,
        FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS user_stats (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        streak_count INTEGER DEFAULT 1,
        last_active_date TEXT,
        cards_reviewed_today INTEGER DEFAULT 0,
        daily_goal INTEGER DEFAULT 15,
        theme TEXT DEFAULT 'dark',
        unlocked_badges_json TEXT DEFAULT '[]',
        weekly_history_json TEXT DEFAULT '{}'
    );

    CREATE TABLE IF NOT EXISTS study_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_type TEXT NOT NULL, -- 'flashcard' or 'quiz'
        item_id INTEGER,
        result TEXT NOT NULL,
        xp_earned INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    );
    """)

    # Ensure user_stats row exists
    cursor.execute("SELECT id FROM user_stats WHERE id = 1")
    if not cursor.fetchone():
        today_str = date.today().isoformat()
        cursor.execute("""
            INSERT INTO user_stats (id, xp, level, streak_count, last_active_date, cards_reviewed_today, daily_goal, theme, unlocked_badges_json, weekly_history_json)
            VALUES (1, 85, 1, 3, ?, 4, 15, 'dark', '["first_review"]', '{}')
        """, (today_str,))

    # Check if demo notes are seeded
    cursor.execute("SELECT COUNT(*) as cnt FROM notes")
    if cursor.fetchone()["cnt"] == 0:
        seed_demo_data(cursor)

    conn.commit()
    conn.close()

def seed_demo_data(cursor):
    now_str = datetime.now().isoformat()
    today_str = date.today().isoformat()

    # Note 1: Cellular Biology
    cursor.execute("""
        INSERT INTO notes (title, subject, tags, source_type, content, created_at, is_demo)
        VALUES (?, ?, ?, ?, ?, ?, 1)
    """, (
        "Mitochondria & Cellular Respiration",
        "Biology",
        "bio, cells, energetics",
        "text",
        "Mitochondria are double-membraned organelles that generate ATP (adenosine triphosphate) through oxidative phosphorylation. The inner membrane has folded cristae that maximize surface area for the electron transport chain. Glycolysis occurs in cytoplasm, while the Krebs cycle happens in the mitochondrial matrix.",
        now_str
    ))
    note1_id = cursor.lastrowid

    # Flashcards for Note 1
    cards_note1 = [
        ("Biology", "Where does the Krebs cycle take place in eukaryotic cells?", "In the mitochondrial matrix.", "The matrix contains the pyruvate dehydrogenase complex and enzymes of the citric acid cycle.", "bio, cells", today_str),
        ("Biology", "What is the primary function of cristae inside mitochondria?", "To increase the inner membrane surface area for ATP synthesis.", "More surface area allows more electron transport complexes and ATP synthase proteins.", "bio, cells", today_str),
        ("Biology", "Which metabolic process produces pyruvate in the cytoplasm?", "Glycolysis.", "Glycolysis breaks glucose down into 2 molecules of pyruvate before entering mitochondria.", "bio, cells", (date.today() + timedelta(days=1)).isoformat())
    ]
    for subj, q, a, exp, tags, due in cards_note1:
        cursor.execute("""
            INSERT INTO flashcards (note_id, subject, question, answer, explanation, tags, due_date, created_at, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (note1_id, subj, q, a, exp, tags, due, now_str))

    # Quizzes for Note 1
    cursor.execute("""
        INSERT INTO quizzes (note_id, subject, question, options_json, answer_index, explanation, created_at, is_demo)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
    """, (
        note1_id,
        "Biology",
        "What molecule directly powers most cellular reactions and is produced in large quantities by mitochondria?",
        json.dumps(["DNA", "ATP (Adenosine Triphosphate)", "Glucose", "Hemoglobin"]),
        1,
        "ATP is the energy currency of the cell, synthesized by ATP synthase using proton gradients across the inner mitochondrial membrane.",
        now_str
    ))

    # Note 2: Computer Systems
    cursor.execute("""
        INSERT INTO notes (title, subject, tags, source_type, content, created_at, is_demo)
        VALUES (?, ?, ?, ?, ?, ?, 1)
    """, (
        "Operating Systems: Concurrency & Semaphores",
        "Computer Science",
        "cs, os, concurrency",
        "text",
        "A race condition occurs when multiple threads access and manipulate shared data concurrently, and the outcome depends on execution timing. Mutexes provide mutual exclusion for a single resource, while counting semaphores allow a fixed number of concurrent accesses.",
        now_str
    ))
    note2_id = cursor.lastrowid

    cards_note2 = [
        ("Computer Science", "What distinguishes a mutex from a counting semaphore?", "A mutex is a locking mechanism for 1 holder; semaphores are signaling mechanisms supporting N concurrent permits.", "Mutexes have ownership semantics (only the locking thread can unlock), whereas semaphores do not.", "cs, os", today_str),
        ("Computer Science", "What condition must occur for a race condition to manifest?", "At least two threads accessing shared memory where at least one write occurs without synchronization.", "Non-atomic read-modify-write sequences are the classic trigger.", "cs, os", today_str)
    ]
    for subj, q, a, exp, tags, due in cards_note2:
        cursor.execute("""
            INSERT INTO flashcards (note_id, subject, question, answer, explanation, tags, due_date, created_at, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (note2_id, subj, q, a, exp, tags, due, now_str))

    cursor.execute("""
        INSERT INTO quizzes (note_id, subject, question, options_json, answer_index, explanation, created_at, is_demo)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
    """, (
        note2_id,
        "Computer Science",
        "Which of the following is NOT one of the 4 Coffman conditions required for Deadlock?",
        json.dumps(["Mutual Exclusion", "Hold and Wait", "Preemption allowed", "Circular Wait"]),
        2,
        "No Preemption is the requirement for deadlock. If preemption is allowed, deadlocks cannot persist.",
        now_str
    ))

def calculate_level(xp: int) -> tuple[int, str, int, int]:
    """Returns (level, title, current_level_base_xp, next_level_xp)"""
    brackets = [
        (1, "Curious Novice", 0, 100),
        (2, "Knowledge Seeker", 100, 250),
        (3, "Memory Apprentice", 250, 500),
        (4, "Active Recall Master", 500, 1000),
        (5, "Grand Mind Architect", 1000, 2500)
    ]
    for lvl, title, base, next_xp in brackets:
        if xp < next_xp:
            return lvl, title, base, next_xp
    return 6, "Omniscient Scholar", 2500, 5000

def award_xp(conn, xp_amount: int, activity_type: str = "review"):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_stats WHERE id = 1")
    stats = dict(cursor.fetchone())

    new_xp = stats["xp"] + xp_amount
    new_level, _, _, _ = calculate_level(new_xp)

    today_str = date.today().isoformat()
    last_active = stats["last_active_date"]

    streak = stats["streak_count"]
    cards_today = stats["cards_reviewed_today"]

    if last_active != today_str:
        yesterday_str = (date.today() - timedelta(days=1)).isoformat()
        if last_active == yesterday_str:
            streak += 1
        else:
            streak = 1
        cards_today = 1 if activity_type == "review" else 0
    else:
        if activity_type == "review":
            cards_today += 1

    # Update weekly history
    history = json.loads(stats["weekly_history_json"] or "{}")
    history[today_str] = history.get(today_str, 0) + (1 if activity_type == "review" else 0)

    # Check badges
    badges = set(json.loads(stats["unlocked_badges_json"] or "[]"))
    if activity_type == "review":
        badges.add("first_review")
    if activity_type == "quiz":
        badges.add("first_quiz")
    if streak >= 3:
        badges.add("streak_3")
    if new_xp >= 500:
        badges.add("xp_500")

    cursor.execute("""
        UPDATE user_stats
        SET xp = ?, level = ?, streak_count = ?, last_active_date = ?,
            cards_reviewed_today = ?, unlocked_badges_json = ?, weekly_history_json = ?
        WHERE id = 1
    """, (new_xp, new_level, streak, today_str, cards_today, json.dumps(list(badges)), json.dumps(history)))

    conn.commit()
    return {"xp": new_xp, "level": new_level, "streak": streak, "xp_earned": xp_amount}
