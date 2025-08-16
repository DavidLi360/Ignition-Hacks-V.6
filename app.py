from flask import Flask, render_template, request, jsonify, redirect, url_for
from module.summarizer import summarize_text, docx_to_sentences
from werkzeug.utils import secure_filename
import os
import sqlite3

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# con = sqlite3.connect("BOOM.db")
# cur = con.cursor()
# cur.execute("CREATE TABLE flashcard_set(title, description)")


is_test_mode = False

# Home page is the landing page
@app.route("/")
def home():
    # Fake sets for now (no DB)
    sets = [
        {"title": "Example Set 1", "description": "This is a sample set"},
        {"title": "Example Set 2", "description": "Another sample set"}
    ]
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
@app.route("/create")
def create():
    return render_template("create.html")

# Login page
@app.route("/login", methods=["GET", "POST"])
def login():
    # For now, just render the login form
    return render_template("login.html")

# Register page
@app.route("/register", methods=["GET", "POST"])
def register():
    # For now, just render the register form
    return render_template("register.html")

# Logout route (no auth yet)
@app.route("/logout")
def logout():
    # Just redirect to home for now
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)