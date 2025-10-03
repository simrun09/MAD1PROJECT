import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

class Config:
    """Base configuration class."""
    # Get the secret key from an environment variable.
    # The second argument is a default value if the variable is not set.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess-this-default-key'

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False