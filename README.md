MiniMemory API

Tiny FastAPI service to store & retrieve short “memories”, protected by JWT auth and per-owner API keys.
	•	Live: https://minimemory-api.onrender.com
	•	Docs (Swagger): https://minimemory-api.onrender.com/docs
	•	OpenAPI JSON: https://minimemory-api.onrender.com/openapi.json

⚠️ First request can be slow (free tier cold start).


Features
	•	🔐 Email/password login (JWT bearer tokens)
	•	🔑 Per-user API keys for calling protected endpoints
	•	🧠 CRUD for memories (title, content, tags, long/short term)
	•	📥 CSV import (background job)
	•	📘 Interactive docs via Swagger UI


Quickstart (2 minutes)

Option A — Swagger UI (no CLI needed)
	1.	Open Docs → https://minimemory-api.onrender.com/docs
	2.	POST /auth/register → create an account (email + password).
	3.	POST /auth/login → copy the access_token.
	4.	Click Authorize → paste Bearer <access_token>.
	5.	POST /keys → create an API key → copy api_key.
	6.	Call /memories with both headers:
	•	Authorization: Bearer <JWT>
	•	X-API-Key: <your key>

Option B — cURL walkthrough
# 0) Base URL
export BASE="https://minimemory-api.onrender.com"

# 1) Health
curl -s "$BASE/"            # -> {"message":"🚀 MiniMemory API is running!"}

# 2) Register
curl -s -X POST "$BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"me+demo@example.com","password":"test12345"}'

# 3) Login → JWT
TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "username=me+demo@example.com" \
  --data-urlencode "password=test12345" \
  --data-urlencode "grant_type=password" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

# 4) Create API key
APIKEY=$(curl -s -X POST "$BASE/keys" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["api_key"])')

# 5) Create a memory
curl -s -X POST "$BASE/memories/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-API-Key: $APIKEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"Prefers dark mode","content":"Rounak prefers dark mode.","tags":["preference","theme"],"is_long_term":true}'

# 6) List memories
curl -s "$BASE/memories/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-API-Key: $APIKEY"




Endpoints (high level)
	•	GET / – Health message
	•	POST /auth/register – Create user: { email, password }
	•	POST /auth/login – Get { access_token, token_type }
	•	POST /keys – Create API key (JWT required) → { api_key }
	•	GET /memories – List (JWT + API key)
	•	POST /memories – Create (JWT + API key)
	•	GET /memories/{id} / PUT / DELETE – Manage (JWT + API key)
	•	POST /memories/import – CSV import (multipart file=@mems.csv)
	•	GET /memories/import/{job_id} – Import job status

Headers for protected routes
Authorization: Bearer <JWT from /auth/login>
X-API-Key: <from /keys>


Data model (example)
{
  "id": 1,
  "title": "Prefers dark mode",
  "content": "Rounak prefers dark mode.",
  "tags": ["preference", "theme"],
  "is_long_term": true,
  "created_at": "2025-08-16T14:10:00Z",
  "owner_id": 123
}









CSV import

POST /memories/import accepts a CSV file with headers like:
title,content,tags,is_long_term
Prefers dark mode,Rounak prefers dark mode.,"preference;theme",true



	tags may be comma or semicolon separated.
	•	Response returns a job_id. Poll: GET /memories/import/{job_id}.

Example:
curl -s -X POST "$BASE/memories/import" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-API-Key: $APIKEY" \
  -F "file=@mems.csv"



