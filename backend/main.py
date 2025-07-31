from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strikewise.router import router as strikewise_router
from dotenv import load_dotenv
# Import firebase_admin_config to ensure the Firebase Admin SDK is initialized
import firebase_admin_config #

load_dotenv()

app = FastAPI()

# Make sure to include your frontend origins here
origins = [
    "https://strikewise-frontend.vercel.app",
    "https://strikewise-frontend-git-main-balaragavesh-g-ms-projects.vercel.app",
    "https://strikewise-frontend-r1rhp31gv-balaragavesh-g-ms-projects.vercel.app",
    "http://localhost:3000", # Add your local frontend development URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(strikewise_router, prefix="/api/strikewise")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)