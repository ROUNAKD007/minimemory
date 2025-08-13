# minimemory/main.py
from fastapi import FastAPI
from .database import Base, engine
from .routers import auth, memories, keys

# Tags for the OpenAPI docs
tags_metadata = [
    {"name": "auth", "description": "Register & login"},
    {"name": "memories", "description": "CRUD, search, import/export"},
    {"name": "api-keys", "description": "Create & manage API keys"},
    {"name": "internal", "description": "Internal/health endpoints"},
]

app = FastAPI(
    title="MiniMemory API",
    description="Persistent, searchable memory for AI agents.",
    version="1.0.0",
    openapi_tags=tags_metadata,
)

# --- Health & root -----------------------------------------------------------
@app.get("/health", tags=["internal"])
def health():
    return {"ok": True}

@app.get("/", tags=["internal"])
def root():
    return {
        "message": "🚀 MiniMemory API is running!",
        "docs": "/docs",
        "health": "/health",
    }

# --- Routers -----------------------------------------------------------------
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(memories.router, prefix="/memories", tags=["memories"])
app.include_router(keys.router, prefix="/keys", tags=["api-keys"])

# --- DB init at startup ------------------------------------------------------
@app.on_event("startup")
def init_db():
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
