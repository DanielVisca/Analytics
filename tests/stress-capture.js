import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE = __ENV.CAPTURE_URL || 'http://localhost:8000';

export const options = {
  stages: [
    { duration: '1m', target: 100 },
    { duration: '2m', target: 500 },
    { duration: '2m', target: 1000 },
    { duration: '5m', target: 1000 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(99)<2000'],
    http_req_failed: ['rate<0.01'],
  },
};

function randomId() {
  return `user_${Math.floor(Math.random() * 1e6)}`;
}

export default function () {
  const payload = JSON.stringify({
    event: 'stress_test',
    distinct_id: randomId(),
    timestamp: new Date().toISOString(),
    properties: { source: 'k6', v: 1 },
    project_id: 'default',
  });
  const res = http.post(`${BASE}/capture`, payload, {
    headers: { 'Content-Type': 'application/json' },
  });
  check(res, { 'status 202': (r) => r.status === 202 });
  sleep(0.1);
}
