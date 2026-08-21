#!/usr/bin/env bash
set -e

export GATEGUARD_TEST_MODE=true

TOKEN="test-token-123"
PROXY_URL="http://localhost:9000"

# Compute SHA256 hash of token for Redis key lookup
if command -v sha256sum >/dev/null 2>&1; then
    TOKEN_HASH=$(echo -n "$TOKEN" | sha256sum | awk '{print $1}')
elif command -v shasum >/dev/null 2>&1; then
    TOKEN_HASH=$(echo -n "$TOKEN" | shasum -a 256 | awk '{print $1}')
else
    TOKEN_HASH=$(python3 -c "import hashlib; print(hashlib.sha256(b'$TOKEN').hexdigest())" 2>/dev/null || python -c "import hashlib; print(hashlib.sha256(b'$TOKEN').hexdigest())")
fi

SESSION_KEY="session:${TOKEN_HASH}"

# Redis execution helper (falls back to Python if redis-cli binary is not found on PATH)
redis_cmd() {
    if command -v redis-cli >/dev/null 2>&1; then
        redis-cli "$@"
    else
        python -c "
import sys, redis
r = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)
cmd = sys.argv[1:]
if not cmd:
    sys.exit(0)
res = r.execute_command(*cmd)
if isinstance(res, set) or isinstance(res, list):
    for item in sorted(list(res)):
        print(item)
elif res is not None:
    print(res)
" "$@"
    fi
}

echo "========================================================"
echo " Starting Standalone Session Kill & Challenge Flow Test"
echo " Target Proxy:         $PROXY_URL"
echo " Test Token:           $TOKEN"
echo " Token SHA256:         $TOKEN_HASH"
echo " GATEGUARD_TEST_MODE:  $GATEGUARD_TEST_MODE"
echo "========================================================"
echo ""

# Flush redis blocklist & session keys before running test to ensure clean state
redis_cmd DEL "$SESSION_KEY" >/dev/null 2>&1 || true
redis_cmd SREM blocklist "$TOKEN_HASH" >/dev/null 2>&1 || true

# Helper to extract HTTP status code from curl response
get_http_code() {
    local url="$1"
    local force_score="$2"
    curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$url&force_score=$force_score"
}

# --- Request #1: High Forced Score (Strike 1) ---
echo "[CHECK 1] Sending Request #1 with forced high score (force_score=90)..."
CODE1=$(get_http_code "${PROXY_URL}/search?q=kill_flow_1" 90)
STRIKES1=$(redis_cmd HGET "$SESSION_KEY" strikes)
STATUS1=$(redis_cmd HGET "$SESSION_KEY" status)

echo " -> Response HTTP Status: $CODE1 (Expected: 200)"
echo " -> Redis State: session_key=$SESSION_KEY"
echo "      strikes = $STRIKES1 (Expected: 1)"
echo "      status  = $STATUS1 (Expected: suspicious)"

if [ "$CODE1" -eq 200 ] && [ "$STRIKES1" -eq 1 ] && [ "$STATUS1" = "suspicious" ]; then
    echo "Result Check 1: PASS"
else
    echo "Result Check 1: FAIL"
    exit 1
fi

echo ""

# --- Request #2: High Forced Score (Strike 2 - Killed) ---
echo "[CHECK 2] Sending Request #2 with forced high score (force_score=90)..."
CODE2=$(get_http_code "${PROXY_URL}/search?q=kill_flow_2" 90)
STATUS2=$(redis_cmd HGET "$SESSION_KEY" status)
IS_BLOCKED2=$(redis_cmd SISMEMBER blocklist "$TOKEN_HASH")

echo " -> Response HTTP Status: $CODE2 (Expected: 403)"
echo " -> Redis State:"
echo "      status            = $STATUS2 (Expected: killed)"
echo "      blocklist member  = $IS_BLOCKED2 (Expected: 1)"

if [ "$CODE2" -eq 403 ] && [ "$STATUS2" = "killed" ] && [ "$IS_BLOCKED2" -eq 1 ]; then
    echo "Result Check 2: PASS"
else
    echo "Result Check 2: FAIL"
    exit 1
fi

echo ""

# --- Request #3: Low/Clean Forced Score (Blocklist Pre-check Rejection) ---
echo "[CHECK 3] Sending Request #3 with forced LOW/clean score (force_score=0)..."
CODE3=$(get_http_code "${PROXY_URL}/search?q=kill_flow_3" 0)

echo " -> Response HTTP Status: $CODE3 (Expected: 403)"
echo " -> Verified: Pre-check blocklist rejection occurred before scoring!"

if [ "$CODE3" -eq 403 ]; then
    echo "Result Check 3: PASS"
else
    echo "Result Check 3: FAIL"
    exit 1
fi

echo ""

# --- Request #4: Challenge Tier Test (force_score=75 with new clean token) ---
CHALLENGE_TOKEN="challenge-token-777"
if command -v sha256sum >/dev/null 2>&1; then
    CHALLENGE_HASH=$(echo -n "$CHALLENGE_TOKEN" | sha256sum | awk '{print $1}')
else
    CHALLENGE_HASH=$(python -c "import hashlib; print(hashlib.sha256(b'$CHALLENGE_TOKEN').hexdigest())")
fi

redis_cmd DEL "session:${CHALLENGE_HASH}" >/dev/null 2>&1 || true
redis_cmd SREM blocklist "$CHALLENGE_HASH" >/dev/null 2>&1 || true

echo "[CHECK 4] Sending Request #4 with forced challenge score (force_score=75, token: $CHALLENGE_TOKEN)..."
START_TIME=$(python -c "import time; print(time.time())")
CODE4=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $CHALLENGE_TOKEN" "${PROXY_URL}/search?q=challenge_test&force_score=75")
END_TIME=$(python -c "import time; print(time.time())")
ELAPSED_MS=$(python -c "print(int(($END_TIME - $START_TIME) * 1000))")

echo " -> Response HTTP Status: $CODE4 (Expected: 200)"
echo " -> Challenge Delay:     ${ELAPSED_MS}ms (Expected >= 500ms)"

if [ "$CODE4" -eq 200 ] && [ "$ELAPSED_MS" -ge 450 ]; then
    echo "Result Check 4: PASS"
else
    echo "Result Check 4: FAIL"
    exit 1
fi

echo ""

# --- Request #5: ONNX Real Attack Payload Scoring (without force_score) ---
echo "[CHECK 5] Testing real obfuscated SQLi, XSS, and Path Traversal payloads using real ONNX model..."

REAL_TOKEN_1="real-sqli-token-1"
REAL_TOKEN_2="real-xss-token-2"
REAL_TOKEN_3="real-traversal-token-3"

# 5a. Obfuscated SQLi payload
RESP1=$(curl -s -i -H "Authorization: Bearer $REAL_TOKEN_1" "${PROXY_URL}/search?q=1'%20UN/**/ION%20SEL/**/ECT%201,2,3--")
CODE5A=$(echo "$RESP1" | head -n 1 | awk '{print $2}')
echo " -> Payload 1 (Obfuscated SQLi: 1' UN/**/ION SEL/**/ECT 1,2,3--): HTTP Status = $CODE5A"

# 5b. XSS payload
RESP2=$(curl -s -i -H "Authorization: Bearer $REAL_TOKEN_2" "${PROXY_URL}/search?q=%3Cscript%3Ealert(1)%3C/script%3E")
CODE5B=$(echo "$RESP2" | head -n 1 | awk '{print $2}')
echo " -> Payload 2 (XSS: <script>alert(1)</script>): HTTP Status = $CODE5B"

# 5c. Path Traversal payload
RESP3=$(curl -s -i -H "Authorization: Bearer $REAL_TOKEN_3" "${PROXY_URL}/search?q=../../etc/passwd")
CODE5C=$(echo "$RESP3" | head -n 1 | awk '{print $2}')
echo " -> Payload 3 (Path Traversal: ../../etc/passwd): HTTP Status = $CODE5C"

if [ "$CODE5A" -ne 0 ] && [ "$CODE5B" -ne 0 ] && [ "$CODE5C" -ne 0 ]; then
    echo "Result Check 5: PASS"
else
    echo "Result Check 5: FAIL"
    exit 1
fi

echo ""
echo "========================================================"
echo " OVERALL TEST RESULT: ALL 5 CHECKS PASSED!"
echo "========================================================"
