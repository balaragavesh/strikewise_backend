from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strikewise.router import router as strikewise_router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

origins = [
    "https://strikewise-frontend-cqge.vercel.app",
    "https://strikewise-frontend-cqge-git-main-balaragavesh-g-ms-projects.vercel.app",
    "https://strikewise-frontend-cqge-5er0i7u9h-balaragavesh-g-ms-projects.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or specify your frontend URL(s) instead of "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(strikewise_router, prefix="/api/strikewise")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
