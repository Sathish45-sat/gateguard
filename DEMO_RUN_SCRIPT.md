# 🛡️ GateGuard — 3-Minute Live Demo Run Script & Checklist (PowerShell)

A battle-tested, second-by-second demo guide for presenting GateGuard: the real-time AI security reverse proxy with ONNX threat scoring and two-strike session revocation. Tailored for **Windows PowerShell**.

---

## 📋 1. Pre-Flight Checklist (Run T-5 Minutes Before Demo)

Run these checks in PowerShell to ensure a flawless live demo environment:

- [ ] **1. Verify Backend is Running (`:8000`)**:
  ```powershell
  curl.exe -s http://127.0.0.1:8000/health
  # Expected: {"status":"ok"}
  ```
- [ ] **2. Verify Proxy is Healthy (`:9000`)**:
  ```powershell
  curl.exe -s http://127.0.0.1:9000/healthz
  # Expected: {"status":"ok"}
  ```
- [ ] **3. Flush Redis & Reset Log State**:
  ```powershell
  python -c "import redis; r = redis.Redis(host='127.0.0.1', port=6379); r.flushall(); print('Redis flushed!')"
  # Expected: Redis flushed!
  ```
- [ ] **4. Confirm `GATEGUARD_TEST_MODE` is Unset (Production ML Scoring Mode)**:
  ```powershell
  Remove-Item Env:GATEGUARD_TEST_MODE -ErrorAction SilentlyContinue
  Write-Output "Test Mode: '$env:GATEGUARD_TEST_MODE'"
  # Expected: Test Mode: ''
  ```
- [ ] **5. Confirm Dashboard is Connected (`:5173`)**:
  - Open `http://localhost:5173` in your browser.
  - Verify the green **"PROXY CONNECTED"** indicator is glowing in the header (no red disconnected banner).
  - Unmute / toggle Sound FX in the top header if audio demo is desired.

---

## ⏱️ 2. Step-by-Step 3-Minute Live Demo Script

```
Demo Session Token: demo-attacker-99
Target Proxy URL:   http://127.0.0.1:9000
Dashboard URL:      http://localhost:5173
```

### Part 1: Introduction & Baseline Clean Traffic (0:00 – 0:45)
**What to Say**:
> *"Modern web apps face credential stuffing, session hijacking, and evasive injection attacks that static WAF rules miss. GateGuard is an inline reverse proxy that embeds an ONNX ML model to score every HTTP request in single-digit milliseconds and actively revokes malicious user sessions at the network edge."*

**What to Do**:
1. Show the clean GateGuard SOC Dashboard at `http://localhost:5173` with 0 incidents.
2. Send 2 benign requests in PowerShell to demonstrate baseline traffic:
   ```powershell
   curl.exe -s -H "Authorization: Bearer user-alice-101" "http://127.0.0.1:9000/search?q=quarterly+financial+report"
   curl.exe -s -H "Authorization: Bearer user-bob-202" "http://127.0.0.1:9000/search?q=team+guidelines+2026"
   ```
3. Point to the dashboard:
   - Green **CLEAN** badges in the Live Traffic Table.
   - Gauge sits at **LOW RISK (Score: 0–1)**.
   - Forwarded HTTP **200 OK** from the backend.

---

### Part 2: Real Injection Attack & Strike 1 Suspicious Flag (0:45 – 1:30)
**What to Say**:
> *"Now an attacker with a valid session token attempts an obfuscated SQL injection using inline SQL comment evasion (`UN/**/ION SEL/**/ECT`). Watch how GateGuard's 4-feature ONNX model extracts entropy, keyword density, and special character ratios on the fly without brittle regexes."*

**What to Do**:
1. Fire **Attack Payload #1**:
   ```powershell
   curl.exe -i -s -H "Authorization: Bearer demo-attacker-99" "http://127.0.0.1:9000/search?q=1'%20UN/**/ION%20SEL/**/ECT%201,2,3--"
   ```
2. Point out the immediate result:
   - Terminal shows **HTTP 200** (Request forwarded, Strike 1 recorded in Redis).
   - Dashboard table lights up with an amber **SUSPICIOUS (STRIKE 1)** badge.
   - Risk score jumps to **100**.
   - Session `demo-attacker-99` is now placed on probation.

---

### Part 3: The Kill Moment — Two-Strike Revocation (1:30 – 2:15)
**What to Say**:
> *"The attacker tries a second attack with the same session token. GateGuard increments strikes to 2 in Redis, automatically kills the session, adds the token SHA256 hash to the global blocklist, and terminates the connection with a 403 Forbidden."*

**What to Do**:
1. Fire **Attack Payload #2** (Same token):
   ```powershell
   curl.exe -i -s -H "Authorization: Bearer demo-attacker-99" "http://127.0.0.1:9000/search?q=%3Cscript%3Ealert(document.cookie)%3C/script%3E"
   ```
2. Point out the **Money Shot**:
   - Terminal returns **HTTP 403 Forbidden** (`{"error":"session_killed"}`).
   - Dashboard triggers the **Kill Event**:
     - 🚨 Animated **Critical Block Toast** appears with audio cue.
     - 💀 **Killed & Blocked Sessions** panel glows red and increments count.
     - Traffic table highlights row as **JUST KILLED (403 Forbidden)** with token hash `b8ec2809`.

---

### Part 4: Replay Protection & Instant Pre-Check Block (2:15 – 2:45)
**What to Say**:
> *"Even if the attacker tries to send a completely benign search query or replay a cached request with that revoked token, GateGuard's pre-check middleware rejects it instantly at the Redis SET layer with zero ML overhead."*

**What to Do**:
1. Fire a **Benign Replay Request** with the revoked token:
   ```powershell
   curl.exe -i -s -H "Authorization: Bearer demo-attacker-99" "http://127.0.0.1:9000/search?q=normal+search+query"
   ```
2. Point out the efficiency:
   - Terminal returns **HTTP 403 Forbidden** (`{"error":"session_revoked"}`).
   - Dashboard displays purple **BLOCKLISTED (PRE-CHECK)** badge.
   - Risk score displays **N/A (Unscored)**, proving zero compute was wasted re-scoring a dead session.

---

### Part 5: Conclusion & Pitch Metrics (2:45 – 3:00)
**What to Say**:
> *"In our latency benchmarks, GateGuard sustains over 420 RPS with a median P50 latency of 76ms for full end-to-end ML inference, state tracking, and proxying. GateGuard stops automated account takeovers before they ever touch your application database."*

---

## ⚠️ 3. Known Failure Modes & One-Line Quick Fixes

| Failure Mode | Symptoms | PowerShell One-Line Fix |
| :--- | :--- | :--- |
| **File Lock on Binary** | Build or git checkout fails with `unlink failed`. | `Get-Process | Where-Object {$_.ProcessName -like "*gateguard*"} | Stop-Process -Force` |
| **Proxy Not Rebuilt** | Code changes in `main.go` not taking effect. | `go build -o gateguard-proxy.exe; .\gateguard-proxy.exe` |
| **Stale Blocklist Data** | New test requests immediately return 403. | `python -c "import redis; r = redis.Redis(host='127.0.0.1', port=6379); r.flushall(); print('Flushed')"` |
| **Proxy Accidentally Restarted** | Embedded miniredis state clears mid-demo. | **Avoid restarting proxy mid-demo** (miniredis is pure in-memory with no disk persistence). |
| **Wrong Dashboard Port** | Red "PROXY DISCONNECTED" banner. | Ensure `dashboard/.env` has `VITE_PROXY_URL=http://127.0.0.1:9000` and restart Vite. |
| **`GATEGUARD_TEST_MODE` Left Enabled** | Attack scoring overridden by test parameters. | `Remove-Item Env:GATEGUARD_TEST_MODE -ErrorAction SilentlyContinue` |

---

## 🎥 4. Offline Fallback Plan (Pre-Recorded Backup Sequence)

If live demo networking fails, have a 20-second MP4 recording ready on your Desktop.

### Sequence to Record in Advance:
1. **Right Window**: Browser at `http://localhost:5173` dashboard.
2. **Left Window**: PowerShell running the exact 4-curl sequence:
   - `curl.exe -s -H "Authorization: Bearer user-alice-101" "http://127.0.0.1:9000/search?q=quarterly+financial+report"` $\rightarrow$ Green Clean.
   - `curl.exe -i -s -H "Authorization: Bearer demo-attacker-99" "http://127.0.0.1:9000/search?q=1'%20UN/**/ION%20SEL/**/ECT%201,2,3--"` $\rightarrow$ Amber Suspicious (Strike 1).
   - `curl.exe -i -s -H "Authorization: Bearer demo-attacker-99" "http://127.0.0.1:9000/search?q=%3Cscript%3Ealert(document.cookie)%3C/script%3E"` $\rightarrow$ Red Killed (Strike 2 + Toast + Glow).
   - `curl.exe -i -s -H "Authorization: Bearer demo-attacker-99" "http://127.0.0.1:9000/search?q=normal+search+query"` $\rightarrow$ Purple Blocklisted (Instant pre-check reject).
3. Save video to Desktop as `gateguard_kill_flow_backup.mp4`.
