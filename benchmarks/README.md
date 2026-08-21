# GateGuard Reverse Proxy Load Testing & Benchmarking Suite

This folder contains load testing tools designed to benchmark the **GateGuard Go Reverse Proxy** sitting in front of the FastAPI demo backend under high concurrency (50–100 users).

---

## 1. Locust Benchmark (`locustfile.py`) — Recommended

[Locust](https://locust.io/) simulates realistic user behavior (login once, execute multiple benign searches, mix in suspicious/attack payloads to trigger ML scoring).

### Installation
```bash
pip install locust
```

### One-Line Run Commands

#### Option A: Headless Mode (CLI with percentile output export)
Runs 50 concurrent users at a spawn rate of 10 users/sec for 30 seconds against the Go proxy at `http://localhost:8080`:

```bash
locust -f locustfile.py --host=http://localhost:8080 --users 50 --spawn-rate 10 --run-time 30s --headless --csv=report_gate_guard
```

#### Option B: Web UI Mode (Interactive Charts & Pitch Deck Reports)
Launches the Locust interactive Web UI at `http://localhost:8089`:

```bash
locust -f locustfile.py --host=http://localhost:8080
```

---

## 2. Zero-Dependency Fallback Script (`benchmark_fallback.py`)

If Locust is not installed or you need an instant benchmark using standard Python libraries:

### One-Line Command (50 Concurrent Users, 500 Total Requests)
```bash
python benchmark_fallback.py --url http://localhost:8080 --users 50 --requests 500
```

### Example Console Output
```text
======================================================================
🚀 GATEGUARD LOAD BENCHMARK (FALLBACK PYTHON RUNNER)
======================================================================
Target URL       : http://localhost:8080
Concurrent Users : 50
Total Requests   : 500
Requests / User  : 10
======================================================================

======================================================================
📊 GATEGUARD BENCHMARK RESULTS
======================================================================
Total Requests Executed : 500
Successful Responses   : 500
Failed / Error Responses: 0
Total Wall Time        : 1.42 s
Throughput (RPS)       : 352.11 req/sec
----------------------------------------------------------------------
LATENCY METRICS (Overall):
  Min Latency          : 1.12 ms
  Avg Latency          : 3.45 ms
  P50 (Median)         : 2.80 ms  <-- Pitch Deck Baseline
  P95 Percentile       : 6.90 ms  <-- Pitch Deck SLA
  P99 Percentile       : 11.40 ms <-- Tail Latency
  Max Latency          : 18.50 ms
----------------------------------------------------------------------
LATENCY BREAKDOWN (Traffic Categories):
  Benign Requests (P50): 2.40 ms | P95: 5.80 ms
  Attack Requests (P50): 3.20 ms | P95: 8.10 ms (Scored via ML)
======================================================================
```

---

## Pitch Deck Report Export Guide

When preparing slides or reports for pitch decks:

1. **Locust Web Dashboard**:
   - Open `http://localhost:8089` during or after a test run.
   - Go to the **Charts** tab to take screenshots of **Total Requests per Second (RPS)** and **Response Times (ms)** over time.
   - Go to the **Download Data** tab and click **"Download Response Time Percentiles CSV"**.
2. **Key Metrics to Highlight**:
   - **P50 Latency (Median)**: Demonstrates typical inline proxy delay under standard traffic (e.g. `< 3ms`).
   - **P95 Latency**: Demonstrates guaranteed Service Level Agreement (SLA) for 95% of users under high concurrency (e.g. `< 8ms`).
   - **P99 Latency**: Shows tail latency stability when ML feature extraction and ONNX model evaluation trigger on complex attack strings.
