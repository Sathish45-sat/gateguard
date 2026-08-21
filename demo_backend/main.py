import datetime
import logging
import sys
import uuid
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("demo_backend")

app = FastAPI(
    title="GateGuard Demo Backend",
    description="Minimal backend application to generate realistic traffic for GateGuard security demo.",
    version="1.0.0"
)

# In-memory session store mapping session_token -> user info dict
SESSIONS: Dict[str, Dict] = {}

# Pre-populated fake dataset for search testing
MOCK_DATA: List[Dict] = [
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
        "id": 3,
        "title": "Database Cluster Maintenance Plan",
        "category": "engineering",
        "content": "Scheduled maintenance for primary PostgreSQL database cluster v15 and session cache nodes.",
        "tags": ["database", "postgres", "infra", "config"]
    },
    {
        "id": 4,
        "title": "API Gateway & Reverse Proxy Setup",
        "category": "network",
        "content": "Go reverse proxy routing, rate limiting thresholds, and security scoring integration details.",
        "tags": ["proxy", "gateway", "network", "config"]
    },
    {
        "id": 5,
        "title": "Security Incident Response #1042",
        "category": "incidents",
        "content": "Investigated anomalous traffic spikes on login route. IP ranges quarantined successfully.",
        "tags": ["incident", "login", "threat", "security"]
    },
    {
        "id": 6,
        "title": "Admin Dashboard User Guide",
        "category": "documentation",
        "content": "Instructions for administrators managing user roles, permissions, and security monitoring views.",
        "tags": ["admin", "user", "docs", "guide"]
    }
]


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    username: str
    message: str


def extract_token(request: Request) -> Optional[str]:
    """Helper to extract token from Authorization header, X-Session-Token header, or query param."""
    # Check Authorization header (Bearer <token>)
    auth_header = request.headers.get("authorization")
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        elif len(parts) == 1:
            return parts[0]

    # Check X-Session-Token header
    session_header = request.headers.get("x-session-token")
    if session_header:
        return session_header

    # Check query parameter 'token'
    token_query = request.query_params.get("token")
    if token_query:
        return token_query

    return None


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Request logging middleware printing timestamp, method, route, query params, and token to stdout."""
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    token = extract_token(request) or "N/A"
    query_params = dict(request.query_params)
    
    # Log request arrival
    logger.info(
        f"[{timestamp}] {request.method} {request.url.path} | QueryParams: {query_params} | Token: {token}"
    )
    
    response: Response = await call_next(request)
    return response


@app.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """
    POST /login route.
    Accepts username and password, generates an opaque session token (UUID4),
    stores it in the in-memory dict, and returns it.
    """
    if not credentials.username or not credentials.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required"
        )
    
    # Generate opaque session token
    session_token = str(uuid.uuid4())
    SESSIONS[session_token] = {
        "username": credentials.username,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    logger.info(f"New session created for user '{credentials.username}' -> Token: {session_token}")
    
    return LoginResponse(
        token=session_token,
        token_type="bearer",
        username=credentials.username,
        message="Login successful"
    )


@app.get("/search")
async def search(q: str, request: Request):
    """
    GET /search?q=... route.
    Requires a valid session token (via Bearer header, X-Session-Token header, or token query param).
    Returns fake mock results matching query string `q`.
    """
    token = extract_token(request)
    if not token or token not in SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing session token. Please login at POST /login first."
        )

    user_info = SESSIONS[token]
    query_str = q.strip().lower()

    # Filter mock entries by query string matching title, category, content, or tags
    matching_results = []
    for item in MOCK_DATA:
        if (
            query_str in item["title"].lower()
            or query_str in item["category"].lower()
            or query_str in item["content"].lower()
            or any(query_str in tag.lower() for tag in item["tags"])
        ):
            matching_results.append(item)

    return {
        "query": q,
        "user": user_info["username"],
        "count": len(matching_results),
        "results": matching_results
    }


@app.get("/health")
@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "app": "GateGuard Demo Backend", "active_sessions": len(SESSIONS)}
