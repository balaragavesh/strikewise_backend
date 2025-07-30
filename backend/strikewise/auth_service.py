# strikewise/auth_service.py
import os
from dotenv import load_dotenv
from pathlib import Path
from fastapi import HTTPException, status
from firebase_admin import auth
from firebase_admin.exceptions import FirebaseError
from strikewise.models import User, AuthResponse # Importing User model
from datetime import datetime, timedelta
from jose import jwt # For your own JWT

# Ensure Firebase Admin SDK is initialized by importing its config file.
# Corrected import path: Use absolute import from 'backend' package.
import firebase_admin_config # This import now directly runs the initialization when auth_service is loaded

# Load .env variables from the backend directory
# This path might need adjustment if your .env is not in the strikewise_backend root.
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# JWT secret for your backend's session token
# IMPORTANT: Change this to a strong, randomly generated secret for production!
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60 * 2 # Set to 2 hours (60 minutes * 2)

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is missing or empty in the .env file")

async def verify_firebase_id_token(id_token: str) -> User:
    """
    Verifies the Firebase ID Token using Firebase Admin SDK and returns the user information.
    """
    try:
        # Verify the ID token. Firebase Admin SDK handles signature verification,
        # expiration, audience, etc., automatically.
        decoded_token = auth.verify_id_token(id_token)

        # The 'decoded_token' contains user information like uid, email, name, picture
        user_id = decoded_token['uid']
        user_email = decoded_token.get('email')
        user_name = decoded_token.get('name')
        user_picture = decoded_token.get('picture')

        return User(
            id=user_id,
            email=user_email,
            name=user_name,
            picture=user_picture
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase ID token: {e}"
        )
    except FirebaseError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Firebase token verification failed: {e.code} - {e.args[0]}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during token verification: {e}"
        )

def create_backend_jwt(user: User) -> str:
    """
    Creates a custom JWT for your backend's session management,
    signed by your backend.
    """
    to_encode = {
        "sub": user.id, # Subject: Firebase User ID
        "email": user.email,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    }
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)