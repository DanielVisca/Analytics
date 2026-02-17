import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE = __ENV.QUERY_URL || 'http://localhost:8001';

const dateFrom = '2024-01-01';
const dateTo = '2024-01-31';

export const options = {
  stages: [
    { duration: '1m', target: 10 },
    { duration: '2m', target: 20 },
    { duration: '3m', target: 20 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    'http_req_duration{name:trend}': ['p(95)<5000'],
    'http_req_duration{name:funnel}': ['p(95)<15000'],
    http_req_failed: ['rate<0.05'],
  },
};

export default function () {
  const trendRes = http.get(
    `${BASE}/api/trends?project_id=default&event=$pageview&date_from=${dateFrom}&date_to=${dateTo}&interval=day`,
    { tags: { name: 'trend' } }
  );
  check(trendRes, { 'trend 200': (r) => r.status === 200 });

  const funnelRes = http.post(
    `${BASE}/api/funnels`,
    JSON.stringify({
      project_id: 'default',
      steps: ['$pageview', 'button_click', 'signup'],
      date_from: dateFrom,
      date_to: dateTo,
    }),
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { name: 'funnel' },
    }
  );
  check(funnelRes, { 'funnel 200': (r) => r.status === 200 });

  sleep(0.5);
}
