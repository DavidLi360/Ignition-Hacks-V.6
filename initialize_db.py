from app import app, init_db
# Push app context manually
with app.app_context():
    init_db()
    print("Database initialized successfully!")