import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'hi there my friend can i get a cookie'

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