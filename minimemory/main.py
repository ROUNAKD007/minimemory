from fastapi import FastAPI
from .database import Base, engine
from .routers import auth, memories, keys

# create tables
Base.metadata.create_all(bind=engine)

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

app.include_router(auth.router)
app.include_router(memories.router)
app.include_router(keys.router)

@app.get("/", tags=["health"])
def root():
    return {"message": "🚀 MiniMemory API is running!"}
