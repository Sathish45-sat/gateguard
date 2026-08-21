# GateGuard Demo Backend

A minimal Python (FastAPI) demo backend application designed to generate realistic login and search traffic for testing security reverse proxies and request-scoring ML engines.

---

## Features

- **`POST /login`**: Accepts `username` and `password` in JSON format, generates a random UUID4 session token, stores it in an in-memory dictionary, and returns it to the caller.
- **`GET /search?q=...`**: Accepts a search query string `q` and requires a valid session token. Filters a pre-populated fake dataset and returns matching results.
- **Request Logging**: Prints request timestamp, HTTP method, route, query parameters, and session token to `stdout` for visual traffic inspection.
- **Go Proxy Compatible**: Simple token extraction from HTTP headers (`Authorization: Bearer <token>`, `X-Session-Token: <token>`) or query parameters (`token=<token>`) without intrusive global middleware that could interfere with upstream reverse proxies.

---

## Local Setup & Running

### 1. Install Dependencies

Ensure Python 3.8+ is installed. Navigate to the `demo_backend/` directory and install the required dependencies:

```bash
cd demo_backend
pip install -r requirements.txt
```

### 2. Run Server with Uvicorn

Launch the FastAPI application:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The application will start at `http://localhost:8000`. Access the interactive API docs at `http://localhost:8000/docs`.

---

## Example Usage & `curl` Commands

### 1. Authenticate / Login (`POST /login`)

Send a `POST` request with JSON credentials:

```bash
curl -X POST "http://localhost:8000/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "admin_user", "password": "securepassword123"}'
```

**Example Response:**
```json
{
  "token": "4f5e8b21-9a7c-48d3-b10e-8f2c6114a90d",
  "token_type": "bearer",
  "username": "admin_user",
  "message": "Login successful"
}
```

---

### 2. Search (`GET /search?q=...`)

Include the session token obtained from `/login` using one of the supported methods:

#### Option A: Bearer Token Header (Recommended)
```bash
curl -X GET "http://localhost:8000/search?q=security" \
     -H "Authorization: Bearer 4f5e8b21-9a7c-48d3-b10e-8f2c6114a90d"
```

#### Option B: Custom Header (`X-Session-Token`)
```bash
curl -X GET "http://localhost:8000/search?q=audit" \
     -H "X-Session-Token: 4f5e8b21-9a7c-48d3-b10e-8f2c6114a90d"
```

#### Option C: Query Parameter (`token=...`)
```bash
curl -X GET "http://localhost:8000/search?q=policy&token=4f5e8b21-9a7c-48d3-b10e-8f2c6114a90d"
```

**Example Search Response:**
```json
{
  "query": "security",
  "user": "admin_user",
  "count": 3,
  "results": [
    {
      "id": 1,
      "title": "System Audit Log - Security Overview",
      "category": "audit",
      "content": "Quarterly security audit report for internal auth services. All systems pass compliance requirements.",
      "tags": ["security", "audit", "compliance", "logs"]
    },
    {
      "id": 2,
      "title": "User Authentication & Credential Policy",
      "category": "policy",
      "content": "Guidelines for password complexity, session expiry, MFA enforcement, and API key management.",
      "tags": ["auth", "security", "policy", "user"]
    },
    {
      "id": 5,
      "title": "Security Incident Response #1042",
      "category": "incidents",
      "content": "Investigated anomalous traffic spikes on login route. IP ranges quarantined successfully.",
      "tags": ["incident", "login", "threat", "security"]
    }
  ]
}
```

---

### 3. Unauthorized Request (Missing/Invalid Token)

```bash
curl -X GET "http://localhost:8000/search?q=security"
```

**Response (`401 Unauthorized`):**
```json
{
  "detail": "Invalid or missing session token. Please login at POST /login first."
}
```

---

## Console Log Sample

When requests arrive, human-readable traffic logs are printed to `stdout`:

```text
2026-08-20 16:49:15,123 [INFO] [2026-08-20 16:49:15 UTC] POST /login | QueryParams: {} | Token: N/A
2026-08-20 16:49:15,125 [INFO] New session created for user 'admin_user' -> Token: 4f5e8b21-9a7c-48d3-b10e-8f2c6114a90d
2026-08-20 16:49:20,456 [INFO] [2026-08-20 16:49:20 UTC] GET /search | QueryParams: {'q': 'security'} | Token: 4f5e8b21-9a7c-48d3-b10e-8f2c6114a90d
```
