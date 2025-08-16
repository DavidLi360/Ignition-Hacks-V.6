# This is just a placeholder for now
# Later we'll add SQLAlchemy models for Users, Flashcards, etc.

class User:
    def __init__(self, username, password_hash):
        self.username = username
        self.password_hash = password_hash
