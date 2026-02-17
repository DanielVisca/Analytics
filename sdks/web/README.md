# Web SDK

Lightweight JS SDK: `capture(event, properties)`, batching (default 10 events or 5s), retries (3x with backoff).

## Usage

```html
<script src="analytics.js"></script>
<script>
  var analytics = new Analytics({
    host: "http://localhost:8000",
    apiKey: "optional",
    projectId: "my-project",
    batchSize: 10,
    flushIntervalMs: 5000,
    autocapture: true
  }).start();
  analytics.capture("button_click", { button_id: "signup" });
</script>
```

- **host**: Capture API base URL.
- **autocapture**: Clicks and pageviews when true.
- Events are batched and sent to `POST {host}/capture`.
