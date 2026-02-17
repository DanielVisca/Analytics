# Stress tests (k6)

- **stress-capture.js** — POST /capture at ramping RPS (100 → 500 → 1000). Success: status 202, p99 &lt; 2s, failure rate &lt; 1%.
- **stress-query.js** — GET /api/trends and POST /api/funnels. Success: p95 trend &lt; 5s, funnel &lt; 15s, failure rate &lt; 5%.

Run with Capture API and Query API up. For capture, run consumer and ClickHouse so events are consumed (lag check). For query, ensure ClickHouse has some data or accept empty results.

```bash
make stress-capture   # CAPTURE_URL=http://localhost:8000
make stress-query    # QUERY_URL=http://localhost:8001
```

Or: `k6 run tests/stress-capture.js`, `k6 run tests/stress-query.js`.
