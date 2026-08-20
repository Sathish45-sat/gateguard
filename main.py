import uuid
from typing import Optional
from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="GateGuard Demo Target")

# In-memory store for issued tokens
issued_tokens = {}

class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""

@app.middleware("http")
async def log_requests(request: Request, call_next):
    body = await request.body()
    body_str = body.decode("utf-8", errors="replace") if body else ""
    query_str = str(request.query_params)
    
    print(
        f"[REQUEST LOG] {request.method} {request.url.path} | Query: {query_str} | Body: {body_str}",
        flush=True,
    )

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    request_with_body = Request(request.scope, receive=receive)
    response = await call_next(request_with_body)
    return response

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/login")
def login(creds: LoginRequest):
    token = str(uuid.uuid4())
    issued_tokens[token] = {"username": creds.username}
    return {"token": token}

@app.get("/search")
def search(q: str = ""):
    return {
        "results": [
            f"fake result 1 matching {q}",
            f"fake result 2 matching {q}",
        ]
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
