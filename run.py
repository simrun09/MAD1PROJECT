
from app import create_app, db
from config import Config  # Import the Config class
from app.models import Users   # <-- Make sure Users is imported

# Create the Flask app instance using the factory and pass the config
app = create_app(Config)

if __name__ == '__main__':
    app.run(debug=True)

# --- Custom CLI Commands ---
@app.cli.command("generate-keys")
def generate_api_keys():
    """Generates API keys for all users who don't have one."""
    users = Users.query.filter_by(api_key=None).all()
    if not users:
        print("All users already have API keys.")
        return

    for user in users:
        key = user.generate_api_key()
        print(f"Generated key for {user.username}: {key}")
    
    db.session.commit()
    print("API keys generated and saved.")