import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)

con = sqlite3.connect("tutorial.db")
cur = con.cursor()
cur.execute("CREATE TABLE movie(title, year, score)")


is_test_mode = False

@app.route('/')
def home():
    card_sets = [
        {"title": "Biology", "description": "Description 1"},
        {"title": "Psychology", "description": "Description 2"},
        {"title": "Economics", "description": "Description 3"}
    ]

    # TODO: use SQLite to store and retrieve card sets
    return render_template('index.html', card_sets=card_sets)


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

# Home page is the landing page
# @app.route("/")
# def home():
#     # Fake sets for now (no DB)
#     sets = [
#         {"title": "Example Set 1", "description": "This is a sample set"},
#         {"title": "Example Set 2", "description": "Another sample set"}
#     ]
#     return render_template("home.html", sets=sets)

# Create flashcards page
@app.route("/create")
def create():
    return render_template("index.html")

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