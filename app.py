from flask import Flask, render_template, request, redirect, url_for, session, g, flash, jsonify
from module.summarizer import summarize_text, docx_to_sentences
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from sentence_transformers import SentenceTransformer, util
import json

# Load model once (fast reuse)
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

app = Flask(__name__)
app.secret_key = "supersecretkey"  # change this in production

UPLOAD_FOLDER = "uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

is_test_mode = False
DATABASE = "database.db"

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
    db.commit()

# -------------------------
# Default flashcards (for testing)
# -------------------------
def default_flashcards():
    return [
        {"question": "What is the capital of France?", "answer": "Paris"},
        {"question": "What is 2 + 2?", "answer": "4"},
        {"question": "What is the largest ocean on Earth?", "answer": "Pacific Ocean"},
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

    return render_template("home.html", sets=sets, is_test_mode=is_test_mode)


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

# ---------- Create ----------
@app.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        user_id = session.get("user_id")
        if title and user_id:
            db = get_db()
            db.execute(
                "INSERT INTO flashcard_sets (user_id, title, description) VALUES (?, ?, ?)",
                (user_id, title, description)
            )
            db.commit()
            flash("Flashcard set created!", "success")
        
        flashcards_json = request.form.get('flashcards_data')
        if flashcards_json:
            flashcards = json.loads(flashcards_json)
        else:
            flashcards = []

        set_id = db.execute(
            "SELECT id FROM flashcard_sets WHERE user_id = ? AND title = ? ORDER BY id DESC LIMIT 1",
            (user_id, title)
        ).fetchone()["id"]

        for card in flashcards:
            db.execute(
            "INSERT INTO flashcards (set_id, question, answer) VALUES (?, ?, ?)",
            (set_id, card['term'], card['definition'])
            )

        db.commit()
        return redirect(url_for("home"))
    return render_template("create.html")

# ---------- Learn ----------
@app.route("/learn/<set_id>")
def learn(set_id):
    db = get_db()
    flashcards = db.execute("SELECT * FROM flashcards WHERE set_id = ?", (set_id,)).fetchall()
    flashcards = [dict(flashcard) for flashcard in flashcards]

    session['flashcards'] = flashcards
    session['current_index'] = 0
    return render_template("learn.html", flashcards=flashcards)

# ---------- Test ----------
@app.route("/test/<set_id>")
def test(set_id):
    db = get_db()
    flashcards = db.execute("SELECT * FROM flashcards WHERE set_id = ?", (set_id,)).fetchall()
    flashcards = [dict(flashcard) for flashcard in flashcards]

    session['flashcards'] = flashcards
    session['current_index'] = 0
    return render_template("test.html")

@app.route("/start_test", methods=["POST"])
def start_test():
    session['flashcards'] = default_flashcards()
    session['current_index'] = 0
    return jsonify({"ok": True})

@app.route('/get_next_card', methods=['GET'])
def get_next_card():
    if 'flashcards' not in session or not isinstance(session['flashcards'], list):
        session['flashcards'] = default_flashcards()
        session['current_index'] = 0

    if 'current_index' not in session:
        session['current_index'] = 0

    cards = session['flashcards']
    idx = session['current_index']

    if idx >= len(cards):
        return jsonify({'question': None, 'answer': None, 'quiz_over': True})

    current_card = cards[idx]
    session['current_index'] = idx + 1

    return jsonify({'question': current_card['question'], 'answer': current_card['answer']})

@app.route('/submit_result', methods=['POST'])
def submit_result():
    data = request.get_json()
    wpm = data.get('wpm')
    similarity = data.get('similarity')
    print(f"Quiz finished! WPM: {wpm}, Avg Similarity: {similarity}")
    return jsonify({'message': 'Results submitted successfully'})

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
