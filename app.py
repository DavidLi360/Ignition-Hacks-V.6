import os
import csv
import sqlite3
from io import StringIO

# Prevent transformers from trying to load TensorFlow/Keras during import.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from flask import Flask, render_template, request, redirect, url_for, session, g, flash, jsonify
from sentence_transformers import SentenceTransformer, util
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import json
import tensorflow as tf
import numpy as np
from datetime import datetime, timedelta
from module.summarizer import summarize_text, docx_to_sentences


# Define your model architecture here (example: a simple Sequential model)
# input_shape = [3]  # State space normalized WPM, learning state, 
# n_outputs = 6  # Action space (10 min, 1 day, 3 days, 1 week, 1 month, 3 months)

# SR_model = tf.keras.Sequential([
#     tf.keras.layers.InputLayer(input_shape=input_shape),
#     tf.keras.layers.Dense(32, activation='elu'),
#     tf.keras.layers.Dense(32, activation='elu'),
#     tf.keras.layers.Dense(32, activation='elu'),
#     tf.keras.layers.Dense(n_outputs)
# ])
# SR_model.load_weights('model.weights.h5')
# Load model once (fast reuse)
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

app = Flask(__name__)
app.secret_key = "supersecretkey"  # change this in production

UPLOAD_FOLDER = "uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

is_test_mode = False
review_extra_enabled = False
DATABASE = "database.db"
SR_INTERVALS_SECONDS = [600, 86400, 259200, 604800, 2592000, 7776000]
EXTRA_REVIEW_COUNT = 5


def _load_sr_model():
    model_path = "spaced_repetition_model.keras"
    if not os.path.exists(model_path):
        return None
    try:
        return tf.keras.models.load_model(model_path)
    except Exception as exc:
        print(f"Unable to load spaced repetition model: {exc}")
        return None


sr_model = _load_sr_model()


def _parse_timestamp(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _predict_next_interval_seconds(learn_state, normalized_wpm, days_since_last_review, is_correct, similarity):
    if not is_correct:
        return SR_INTERVALS_SECONDS[0], "fallback"

    model_state = np.array([
        [
            min(max(learn_state / 3.0, 0.0), 1.0),
            min(max(normalized_wpm, 0.0), 1.0),
            min(max(days_since_last_review / 90.0, 0.0), 1.0),
        ]
    ], dtype=np.float32)

    if sr_model is not None:
        try:
            model_output = sr_model.predict(model_state, verbose=0)[0]
            action = int(np.argmax(model_output))
            action = min(max(action, 0), len(SR_INTERVALS_SECONDS) - 1)
            return SR_INTERVALS_SECONDS[action], "model"
        except Exception as exc:
            print(f"Spaced repetition model predict failed, falling back: {exc}")

    confidence = (0.6 * similarity) + (0.4 * normalized_wpm)
    state_bonus = {0: 0, 1: 1, 2: 1, 3: 2}.get(learn_state, 0)
    interval_idx = int(round(confidence * (len(SR_INTERVALS_SECONDS) - 1))) + state_bonus
    interval_idx = min(max(interval_idx, 0), len(SR_INTERVALS_SECONDS) - 1)
    return SR_INTERVALS_SECONDS[interval_idx], "heuristic"


def _get_dashboard_counts(db, user_id):
    rows = db.execute(
        """
        SELECT
            s.id AS set_id,
            COUNT(f.id) AS total_count,
            SUM(CASE WHEN f.id IS NOT NULL AND p.card_id IS NULL THEN 1 ELSE 0 END) AS new_count,
            SUM(CASE WHEN p.card_id IS NOT NULL AND (p.next_review_at IS NULL OR datetime(p.next_review_at) <= CURRENT_TIMESTAMP) THEN 1 ELSE 0 END) AS due_count,
            SUM(CASE WHEN p.card_id IS NOT NULL AND p.next_review_at IS NOT NULL AND datetime(p.next_review_at) > CURRENT_TIMESTAMP THEN 1 ELSE 0 END) AS upcoming_count
        FROM flashcard_sets s
        LEFT JOIN flashcards f ON f.set_id = s.id
        LEFT JOIN flashcard_progress p ON p.card_id = f.id AND p.user_id = ?
        WHERE s.user_id = ?
        GROUP BY s.id
        """,
        (user_id, user_id),
    ).fetchall()

    counts = {}
    for row in rows:
        counts[int(row["set_id"])] = {
            "total_count": int(row["total_count"] or 0),
            "new_count": int(row["new_count"] or 0),
            "due_count": int(row["due_count"] or 0),
            "upcoming_count": int(row["upcoming_count"] or 0),
        }
    return counts


def _fetch_review_cards(db, user_id, set_id, include_extra=False):
    due_cards = db.execute(
        """
        SELECT f.id, f.question, f.answer
        FROM flashcards f
        LEFT JOIN flashcard_progress p
            ON p.card_id = f.id AND p.user_id = ?
        WHERE f.set_id = ?
          AND (p.next_review_at IS NULL OR datetime(p.next_review_at) <= CURRENT_TIMESTAMP)
        ORDER BY COALESCE(p.next_review_at, '1970-01-01 00:00:00') ASC, f.id ASC
        """,
        (user_id, set_id),
    ).fetchall()

    if not include_extra:
        return [dict(card) for card in due_cards]

    due_ids = {card["id"] for card in due_cards}
    if due_ids:
        placeholders = ", ".join(["?"] * len(due_ids))
        extra_cards = db.execute(
            f"""
            SELECT f.id, f.question, f.answer
            FROM flashcards f
            LEFT JOIN flashcard_progress p
                ON p.card_id = f.id AND p.user_id = ?
            WHERE f.set_id = ?
              AND f.id NOT IN ({placeholders})
            ORDER BY COALESCE(p.next_review_at, '1970-01-01 00:00:00') ASC, f.id ASC
            LIMIT ?
            """,
            [user_id, set_id, *list(due_ids), EXTRA_REVIEW_COUNT],
        ).fetchall()
    else:
        extra_cards = db.execute(
            """
            SELECT f.id, f.question, f.answer
            FROM flashcards f
            LEFT JOIN flashcard_progress p
                ON p.card_id = f.id AND p.user_id = ?
            WHERE f.set_id = ?
            ORDER BY COALESCE(p.next_review_at, '1970-01-01 00:00:00') ASC, f.id ASC
            LIMIT ?
            """,
            (user_id, set_id, EXTRA_REVIEW_COUNT),
        ).fetchall()

    combined_cards = [dict(card) for card in due_cards]
    combined_cards.extend(dict(card) for card in extra_cards)
    return combined_cards


def _parse_csv_flashcards(file_storage):
    raw_bytes = file_storage.read()
    if not raw_bytes:
        return []

    text = raw_bytes.decode("utf-8-sig")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",	;|")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(StringIO(text), dialect=dialect)
    if reader.fieldnames:
        normalized_headers = {header.strip().lower(): header for header in reader.fieldnames if header}
    else:
        normalized_headers = {}

    def _resolve_header(*aliases):
        for alias in aliases:
            header = normalized_headers.get(alias)
            if header:
                return header
        return None

    question_field = _resolve_header("question", "front", "term", "prompt", "cue")
    answer_field = _resolve_header("answer", "back", "definition", "response", "meaning")

    cards = []
    for row in reader:
        question = (row.get(question_field) or "").strip() if question_field else ""
        answer = (row.get(answer_field) or "").strip() if answer_field else ""
        if not question and reader.fieldnames:
            first_field = reader.fieldnames[0]
            second_field = reader.fieldnames[1] if len(reader.fieldnames) > 1 else None
            question = (row.get(first_field) or "").strip() if first_field else ""
            answer = (row.get(second_field) or "").strip() if second_field else ""

        if question and answer:
            cards.append({"term": question, "definition": answer})

    return cards

# -------------------------
# Database Helper Functions
# -------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS flashcard_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            set_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            FOREIGN KEY (set_id) REFERENCES flashcard_sets (id)
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS flashcard_progress (
            user_id INTEGER NOT NULL,
            card_id INTEGER NOT NULL,
            learn_state INTEGER NOT NULL DEFAULT 0,
            last_wpm REAL NOT NULL DEFAULT 0,
            max_wpm REAL NOT NULL DEFAULT 0,
            last_similarity REAL NOT NULL DEFAULT 0,
            review_count INTEGER NOT NULL DEFAULT 0,
            correct_streak INTEGER NOT NULL DEFAULT 0,
            last_review_at TEXT,
            next_review_at TEXT,
            PRIMARY KEY (user_id, card_id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (card_id) REFERENCES flashcards (id)
        )"""
    )
    db.commit()

# -------------------------
# Default flashcards (for testing)
# -------------------------
def default_flashcards():
    return [
        {"id": None, "question": "What is the capital of France?", "answer": "Paris"},
        {"id": None, "question": "What is 2 + 2?", "answer": "4"},
        {"id": None, "question": "What is the largest ocean on Earth?", "answer": "Pacific Ocean"},
    ]

# -------------------------
# Routes
# -------------------------
@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    sets = db.execute("SELECT * FROM flashcard_sets WHERE user_id = ?", (session["user_id"],)).fetchall()
    set_counts = _get_dashboard_counts(db, session["user_id"])
    overall_new = sum(counts["new_count"] for counts in set_counts.values())
    overall_due = sum(counts["due_count"] for counts in set_counts.values())
    overall_total = sum(counts["total_count"] for counts in set_counts.values())

    return render_template(
        "home.html",
        sets=sets,
        set_counts=set_counts,
        overall_new=overall_new,
        overall_due=overall_due,
        overall_total=overall_total,
        is_test_mode=is_test_mode,
        review_extra_enabled=session.get("review_extra_enabled", False),
    )


# ---------- Similarity Check ----------
@app.route('/check_answer', methods=['POST'])
def check_answer():
    data = request.get_json()
    user_answer = data.get("user_answer", "")
    correct_answer = data.get("correct_answer", "")

    embeddings = model.encode([user_answer, correct_answer], convert_to_tensor=True)
    similarity = util.pytorch_cos_sim(embeddings[0], embeddings[1]).item()

    return jsonify({
        "similarity": similarity,
        "is_correct": similarity > 0.7
    })

# ---------- Summarizer ----------
@app.route("/summarize", methods=["POST"])
def summarize():
    try:
        data = request.get_json()
        text = data.get("text", "")
        summary = summarize_text(text)
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/summarize-docx", methods=["POST"])
def summarize_docx():
    file = request.files.get("file")
    if not file or not file.filename.endswith(".docx"):
        return jsonify({"error": "Please upload a DOCX file"}), 400

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
    file.save(file_path)

    sentences = docx_to_sentences(file_path)
    summary = summarize_text(" ".join(sentences))
    return jsonify(summary)

@app.route('/toggle', methods=['POST'])
def handle_toggle():
    global is_test_mode
    if not request.json:
        return jsonify({'error': 'Invalid request'}), 400
    status = request.json.get('status')
    is_test_mode = bool(status)
    return jsonify({'message': 'Status received successfully', 'current_status': status})


@app.route('/toggle-extra', methods=['POST'])
def handle_extra_toggle():
    if not request.json:
        return jsonify({'error': 'Invalid request'}), 400
    status = request.json.get('status')
    session['review_extra_enabled'] = bool(status)
    return jsonify({
        'message': 'Extra review status received successfully',
        'current_status': session['review_extra_enabled']
    })


@app.route('/import-csv', methods=['POST'])
def import_csv():
    if "user_id" not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    file = request.files.get('file')
    if not file or not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'Please upload a CSV file'}), 400

    try:
        cards = _parse_csv_flashcards(file)
    except UnicodeDecodeError:
        return jsonify({'error': 'CSV must be UTF-8 encoded'}), 400

    return jsonify({'cards': cards})

# ---------- Create ----------
@app.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        user_id = session.get("user_id")
        if not user_id:
            flash("Please log in before creating a flashcard set.", "error")
            return redirect(url_for("login"))

        if not title or not title.strip():
            flash("A set title is required.", "error")
            return redirect(url_for("create"))

        db = get_db()
        flashcards_json = request.form.get('flashcards_data')
        if flashcards_json:
            try:
                flashcards = json.loads(flashcards_json)
            except json.JSONDecodeError:
                flash("The flashcard data could not be read. Please try again.", "error")
                return redirect(url_for("create"))
        else:
            flashcards = []

        cursor = db.execute(
            "INSERT INTO flashcard_sets (user_id, title, description) VALUES (?, ?, ?)",
            (user_id, title.strip(), description)
        )
        set_id = cursor.lastrowid
        db.commit()
        flash("Flashcard set created!", "success")

        for card in flashcards:
            term = card.get('term', '').strip()
            definition = card.get('definition', '').strip()
            if not term or not definition:
                continue
            db.execute(
            "INSERT INTO flashcards (set_id, question, answer) VALUES (?, ?, ?)",
            (set_id, term, definition)
            )

        db.commit()
        return redirect(url_for("home"))
    return render_template("create.html")

# ---------- Learn ----------
@app.route("/learn/<set_id>")
def learn(set_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    set_row = db.execute(
        "SELECT id FROM flashcard_sets WHERE id = ? AND user_id = ?",
        (set_id, session["user_id"]),
    ).fetchone()
    if set_row is None:
        flash("Set not found.", "error")
        return redirect(url_for("home"))

    session['study_mode'] = 'learn'
    session['active_set_id'] = int(set_id)
    session['test_queue_ids'] = []
    session['current_index'] = 0
    return render_template("learn.html")

# ---------- Test ----------
@app.route("/test/<set_id>")
def test(set_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    flashcards = _fetch_review_cards(
        db,
        session["user_id"],
        set_id,
        include_extra=session.get("review_extra_enabled", False),
    )

    session['study_mode'] = 'test'
    session['active_set_id'] = int(set_id)
    session['test_queue_ids'] = [int(card["id"]) for card in flashcards if card.get("id") is not None]
    session['current_index'] = 0
    return render_template("test.html", flashcards=flashcards)

@app.route("/start_test", methods=["POST"])
def start_test():
    session['current_index'] = 0
    return jsonify({"ok": True})

@app.route('/get_next_card', methods=['GET'])
def get_next_card():
    if 'current_index' not in session:
        session['current_index'] = 0
    idx = session['current_index']

    db = get_db()
    study_mode = session.get('study_mode')
    user_id = session.get('user_id')

    if study_mode == 'learn':
        set_id = session.get('active_set_id')
        if set_id is None or user_id is None:
            return jsonify({'question': None, 'answer': None, 'quiz_over': True})

        current_card = db.execute(
            """
            SELECT f.id, f.question, f.answer
            FROM flashcards f
            JOIN flashcard_sets s ON s.id = f.set_id
            WHERE f.set_id = ? AND s.user_id = ?
            ORDER BY f.id ASC
            LIMIT 1 OFFSET ?
            """,
            (set_id, user_id, idx),
        ).fetchone()

        if current_card is None:
            return jsonify({'question': None, 'answer': None, 'quiz_over': True})

        session['current_index'] = idx + 1
        return jsonify({
            'card_id': current_card['id'],
            'question': current_card['question'],
            'answer': current_card['answer']
        })

    if study_mode == 'test':
        queue_ids = session.get('test_queue_ids', [])
        if idx >= len(queue_ids):
            return jsonify({'question': None, 'answer': None, 'quiz_over': True})

        card_id = queue_ids[idx]
        current_card = db.execute(
            """
            SELECT f.id, f.question, f.answer
            FROM flashcards f
            JOIN flashcard_sets s ON s.id = f.set_id
            WHERE f.id = ? AND s.user_id = ?
            """,
            (card_id, user_id),
        ).fetchone()

        if current_card is None:
            return jsonify({'question': None, 'answer': None, 'quiz_over': True})

        session['current_index'] = idx + 1
        return jsonify({
            'card_id': current_card['id'],
            'question': current_card['question'],
            'answer': current_card['answer']
        })

    return jsonify({'question': None, 'answer': None, 'quiz_over': True})

@app.route('/submit_result', methods=['POST'])
def submit_result():
    data = request.get_json()
    if "user_id" not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    card_id = data.get('card_id')
    if card_id is None:
        return jsonify({'error': 'card_id is required'}), 400

    try:
        card_id = int(card_id)
        wpm = float(data.get('wpm', 0) or 0)
        similarity = float(data.get('similarity', 0) or 0)
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid payload values'}), 400

    is_correct = bool(data.get('is_correct', False))
    user_id = session['user_id']
    now = datetime.utcnow()
    db = get_db()

    card_exists = db.execute(
        """
        SELECT 1
        FROM flashcards f
        JOIN flashcard_sets s ON s.id = f.set_id
        WHERE f.id = ? AND s.user_id = ?
        """,
        (card_id, user_id),
    ).fetchone()

    if card_exists is None:
        return jsonify({'error': 'Card not found'}), 404

    progress = db.execute(
        "SELECT * FROM flashcard_progress WHERE user_id = ? AND card_id = ?",
        (user_id, card_id),
    ).fetchone()

    current_state = progress['learn_state'] if progress else 0
    previous_max_wpm = progress['max_wpm'] if progress else 0
    previous_streak = progress['correct_streak'] if progress else 0
    previous_review_count = progress['review_count'] if progress else 0
    previous_review_at = _parse_timestamp(progress['last_review_at']) if progress else None
    days_since_last_review = (now - previous_review_at).days if previous_review_at else 0

    if is_correct:
        if current_state == 0:
            next_state = 1
        elif current_state in (1, 2):
            next_state = 3
        else:
            next_state = 3
        correct_streak = previous_streak + 1
    else:
        if current_state == 3:
            next_state = 2
        elif current_state == 0:
            next_state = 1
        else:
            next_state = 2
        correct_streak = 0

    if is_correct:
        max_wpm = max(previous_max_wpm, wpm)
    else:
        max_wpm = previous_max_wpm

    normalized_wpm = 0.0
    if max_wpm > 0:
        normalized_wpm = min(max(wpm / max_wpm, 0.0), 1.0)

    interval_seconds, scheduling_source = _predict_next_interval_seconds(
        learn_state=next_state,
        normalized_wpm=normalized_wpm,
        days_since_last_review=days_since_last_review,
        is_correct=is_correct,
        similarity=similarity,
    )
    next_review_at = now + timedelta(seconds=interval_seconds)

    db.execute(
        """
        INSERT INTO flashcard_progress (
            user_id, card_id, learn_state, last_wpm, max_wpm, last_similarity,
            review_count, correct_streak, last_review_at, next_review_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, card_id) DO UPDATE SET
            learn_state = excluded.learn_state,
            last_wpm = excluded.last_wpm,
            max_wpm = excluded.max_wpm,
            last_similarity = excluded.last_similarity,
            review_count = excluded.review_count,
            correct_streak = excluded.correct_streak,
            last_review_at = excluded.last_review_at,
            next_review_at = excluded.next_review_at
        """,
        (
            user_id,
            card_id,
            next_state,
            wpm,
            max_wpm,
            similarity,
            previous_review_count + 1,
            correct_streak,
            now.isoformat(sep=' ', timespec='seconds'),
            next_review_at.isoformat(sep=' ', timespec='seconds'),
        ),
    )
    db.commit()

    print(
        f"Card {card_id} reviewed. WPM={wpm}, similarity={similarity}, "
        f"state={next_state}, next_review_in={interval_seconds}s"
    )
    return jsonify({
        'message': 'Results submitted successfully',
        'time_til_next_review': interval_seconds,
        'next_review_at': next_review_at.isoformat(sep=' ', timespec='seconds'),
        'learn_state': next_state,
        'scheduling_source': scheduling_source,
    })

# ---------- Auth ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        if not username or not password:
            flash("Username and password are required.", "error")
            return redirect(url_for("register"))

        hashed_pw = generate_password_hash(password)

        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
            db.commit()
            flash("✅ Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("⚠️ Username already taken. Try another.", "error")
            return redirect(url_for("register"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("✅ Logged in successfully!", "success")
            return redirect(url_for("home"))
        else:
            flash("❌ Invalid username or password.", "error")
            return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("👋 You have been logged out.", "info")
    return redirect(url_for("login"))


# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    if not os.path.exists(DATABASE):
        with app.app_context():
            init_db()
    else:
        with app.app_context():
            init_db()
    app.run(debug=True)
