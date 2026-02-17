# Analytics Dashboard

Simple React app to view analytics: connect to your Query API, then view trends and funnels.

## Run

```bash
cd services/dashboard
npm install
npm run dev
```

Open http://localhost:3000.

## Usage

1. **Connect** — Enter Query API URL (default `http://localhost:8001`) and Project ID (default `default`). Click "Connect & go to Dashboard". Settings are stored in localStorage.
2. **Dashboard** — Use **Trends**: pick an event name (e.g. `$pageview`, `feature_click`), date range, then "Load". Use **Funnel**: enter comma-separated event steps and date range, then "Load". Click "Disconnect" to clear settings and return to Connect.

Requires the Query API to be running and CORS enabled (already configured for `*`).
