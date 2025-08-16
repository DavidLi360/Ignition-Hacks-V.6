from flask import Flask, render_template, redirect, url_for

app = Flask(__name__)

# Home page is the landing page
@app.route("/")
def home():
    # Fake sets for now (no DB)
    sets = [
        {"title": "Example Set 1", "description": "This is a sample set"},
        {"title": "Example Set 2", "description": "Another sample set"}
    ]
    return render_template("home.html", sets=sets)

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