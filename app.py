from flask import Flask, render_template, request, redirect, url_for, session, g, flash, jsonify 
from module.summarizer import summarize_text, docx_to_sentences
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"  # change this in production

UPLOAD_FOLDER = "uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# con = sqlite3.connect("BOOM.db")
# cur = con.cursor()
# cur.execute("CREATE TABLE flashcard_set(title, description)")

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
        """CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )"""
    )
    db.commit()

# -------------------------
# Routes
# -------------------------
@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    sets = db.execute("SELECT * FROM flashcards WHERE user_id = ?", (session["user_id"],)).fetchall()
    return render_template("home.html", sets=sets)



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

    # Convert DOCX → sentences
    sentences = docx_to_sentences(file_path)

    # Optional: summarize
    summary = summarize_text(" ".join(sentences))
    return jsonify(summary)

@app.route('/toggle', methods=['POST'])
def handle_toggle():
    """Toggle between TEST mode and LEARN mode"""
    global is_test_mode

    # Ensure the request is JSON
    if not request.json:
        return jsonify({'error': 'Invalid request'}), 400

    # Get the status from the JSON data
    status = request.json.get('status')
    
    # Process the status (e.g., control a device, save to a database)
    if status is True:
        is_test_mode = True
        print('hi')
    else:
        is_test_mode = False
        print('hello')

    # Send a response back to the client
    return jsonify({'message': 'Status received successfully', 'current_status': status})


# Create flashcards page
@app.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        user_id = session.get("user_id")
        if title and user_id:
            db = get_db()
            db.execute(
                "INSERT INTO flashcards (user_id, title, description) VALUES (?, ?, ?)",
                (user_id, title, description)
            )
            db.commit()
            flash("Flashcard set created!", "success")
        return redirect(url_for("home"))
    return render_template("create.html")

@app.route("/learn/<set_id>")
def learn(set_id):
    # TODO: get the flashcards from the database
    flashcards = [
        {"question": "What is the capital of France?", "answer": "Paris"},
        {"question": "What is 2 + 2?", "answer": "4"},
        {"question": "What is the largest ocean on Earth?", "answer": "Pacific Ocean"},
        # {"question": "BIG BOY QUESTION", "answer": "Photosynthesis is the process that plants use to make their own food. It happens mainly in the leaves. Plants take in sunlight, carbon dioxide from the air, and water from the soil. Using the energy from sunlight, they turn these into glucose (a kind of sugar) and oxygen. The oxygen is released into the air, and the glucose is used by the plant for energy and growth. This process is important because it gives us the oxygen we breathe and helps keep the planet healthy."}
    ]

    session['flashcards'] = flashcards
    session['current_index'] = 0

    return render_template("learn.html", flashcards=flashcards)

@app.route("/test/<set_id>")
def test(set_id):
    # TODO: implement the test route
    return render_template("test.html")

@app.route('/get_next_card', methods=['GET'])
def get_next_card():
    # Check if we're out of cards
    if session['current_index'] >= len(session['flashcards']):
        return jsonify({'question': None, 'answer': None, 'quiz_over': True})
    
    # Get the current card and increment the index
    current_card = session['flashcards'][session['current_index']]
    session['current_index'] += 1
    
    return jsonify({
        'question': current_card['question'],
        'answer': current_card['answer']
    })

@app.route('/submit_result', methods=['POST'])
def submit_result():
    data = request.get_json()
    accuracy = data.get('accuracy')
    wpm = data.get('wpm')
    
    # Here you can save the results to a database or a file
    print(f"Quiz finished! Accuracy: {accuracy}%, WPM: {wpm}")
    
    return jsonify({'message': 'Results submitted successfully'})

  
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_pw = generate_password_hash(password)

        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
            db.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already taken.", "error")
            return redirect(url_for("register"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("home"))
        else:
            flash("Invalid username or password.", "error")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
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
            init_db()  # ensure flashcards table exists
    app.run(debug=True)