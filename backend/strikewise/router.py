# strikewise/router.py
from fastapi import APIRouter, HTTPException, status, Header, Depends
from strikewise.models import AnalysisRequest, AnalysisResponse, AuthResponse, User # Import User model
from strikewise.service import run_option_analysis
from strikewise.auth_service import verify_firebase_id_token, create_backend_jwt # Import the new functions

router = APIRouter()

# Dependency to get current authenticated user from backend JWT (optional, but good for protected routes)
async def get_current_user(x_access_token: str = Header(..., alias="Authorization")):
    # Extract the actual token string (remove "Bearer ")
    token = x_access_token.replace("Bearer ", "")
    
    # This is a basic example. In a real app, you'd verify this backend JWT here.
    # For now, we'll assume a valid Firebase token means the user is authenticated.
    # Later, you'd add jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    # to verify your *own* backend's JWT.
    
    # For now, we just return a dummy user if a token is present.
    # A full implementation would involve decoding and validating the backend JWT here.
    # If using just the Firebase token for all calls, you'd verify it on every protected route.
    # Since you want your own JWT, you'd verify your JWT here.
    
    try:
        from jose import jwt
        from datetime import datetime
        import os
        from dotenv import load_dotenv
        from pathlib import Path

        # Load .env variables for JWT_SECRET_KEY within this function
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        load_dotenv(dotenv_path=env_path)
        JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
        JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256") # Ensure algorithm is correct

        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        user_email = payload.get("email")
        
        if user_id is None or user_email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        
        # Check token expiration
        expiration = payload.get("exp")
        if expiration and datetime.fromtimestamp(expiration) < datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

        return User(id=user_id, email=user_email, name=payload.get("name")) # Reconstruct user from payload
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")


# Existing route for option analysis (now protected)
@router.post("/analyze", response_model=AnalysisResponse)
def analyze(request: AnalysisRequest, current_user: User = Depends(get_current_user)):
    # The current_user object will contain the authenticated user's details
    print(f"Analysis requested by user: {current_user.email} (UID: {current_user.id})")
    return run_option_analysis(request)

# --- New Endpoint for Firebase ID Token Verification ---

@router.post("/auth/login/firebase", response_model=AuthResponse)
async def login_with_firebase(x_firebase_id_token: str = Header(..., alias="X-Firebase-ID-Token")):
    """
    Receives a Firebase ID Token from the frontend, verifies it using Firebase Admin SDK,
    and returns your application's custom JWT.
    """
    try:
        # 1. Verify the Firebase ID Token
        firebase_user = await verify_firebase_id_token(x_firebase_id_token)

        # 2. Create your backend's custom JWT for this user
        backend_jwt = create_backend_jwt(firebase_user)

        # 3. Return the backend's JWT and user info to the frontend
        return AuthResponse(access_token=backend_jwt, user=firebase_user)
    except HTTPException as e:
        raise e # Re-raise FastAPI HTTPExceptions (e.g., 401 Unauthorized from verify_firebase_id_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {e}"
        )