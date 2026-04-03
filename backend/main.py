from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from routes import tools, categories, search

load_dotenv()

app = FastAPI(
    title="AI Tools Hub API",
    description="Unbiased directory of AI tools with search, filtering, and API key reference",
    version="1.0.0",
)

# CORS: Allow frontend origins (local + production)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
origins = [origin.strip() for origin in allowed_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tools.router, prefix="/tools", tags=["Tools"])
app.include_router(categories.router, prefix="/categories", tags=["Categories"])
app.include_router(search.router, prefix="/search", tags=["Search"])


@app.get("/", tags=["Health"])
def root():
    return {
        "status": "ok",
        "message": "AI Tools Hub API is running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}