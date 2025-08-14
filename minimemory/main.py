from fastapi import FastAPI
from .database import engine
from .models import Base
from .routers import auth, memories, keys

# OpenAPI tags
tags_metadata = [
    {"name": "auth", "description": "Register & login"},
    {"name": "memories", "description": "CRUD, search, import/export"},
    {"name": "api-keys", "description": "Create & manage API keys"},
    {"name": "internal", "description": "Internal health checks"}
]

app = FastAPI(
    title="MiniMemory API",
    description="Persistent, searchable memory for AI agents.",
    version="1.0.0",
    openapi_tags=tags_metadata,
)

# Routers
app.include_router(auth.router)
app.include_router(memories.router)
app.include_router(keys.router)

# Create DB tables
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

@app.get("/health", tags=["internal"])
def health():
    return {"ok": True}

@app.get("/", tags=["internal"])
def root():
    return {"message": "🚀 MiniMemory API is running!"}
