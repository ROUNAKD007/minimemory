from fastapi import FastAPI
from .database import engine
from .models import Base
from .routers import auth, memories, keys

tags_metadata = [
  {"name":"auth","description":"Register & login"},
  {"name":"memories","description":"CRUD, search, import/export"},
  {"name":"api-keys","description":"Create & manage API keys"},
]

app = FastAPI(
    title="MiniMemory API",
    description="Persistent, searchable memory for AI agents.",
    version="1.0.0",
    openapi_tags=tags_metadata,
)

# Include routers
app.include_router(auth.router, prefix="/auth")
app.include_router(memories.router, prefix="/memories")
app.include_router(keys.router, prefix="/keys")

# Create tables on startup (safe if tables already exist)
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

@app.get("/health", tags=["internal"])
def health():
    return {"ok": True}

@app.get("/", tags=["health"])
def root():
    return {"message": "🚀 MiniMemory API is running!"}
