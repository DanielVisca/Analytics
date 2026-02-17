(function (window) {
  "use strict";

  var DEFAULT_BATCH_SIZE = 10;
  var DEFAULT_FLUSH_INTERVAL_MS = 5000;
  var MAX_RETRIES = 3;
  var RETRY_BACKOFF_MS = 1000;

  function generateId() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      var v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  function nowIso() {
    return new Date().toISOString();
  }

  function Analytics(config) {
    config = config || {};
    this.host = config.host || "";
    this.apiKey = config.apiKey || null;
    this.projectId = config.projectId || null;
    this.batchSize = config.batchSize ?? DEFAULT_BATCH_SIZE;
    this.flushIntervalMs = config.flushIntervalMs ?? DEFAULT_FLUSH_INTERVAL_MS;
    this.autocapture = config.autocapture !== false;
    this._queue = [];
    this._flushTimer = null;
    this._inFlight = false;
    this._deviceId = config.deviceId || localStorage.getItem("_analytics_device_id") || generateId();
    localStorage.setItem("_analytics_device_id", this._deviceId);
  }

  Analytics.prototype.capture = function (eventName, properties) {
    if (!eventName || typeof eventName !== "string") return;
    var payload = {
      event: eventName,
      distinct_id: this._deviceId,
      timestamp: nowIso(),
      properties: typeof properties === "object" && properties !== null ? properties : {},
      uuid: generateId(),
      $lib: "web",
      $lib_version: "1.0.0",
      $device_id: this._deviceId,
    };
    if (this.projectId) payload.project_id = this.projectId;
    this._queue.push(payload);
    this._scheduleFlush();
  };

  Analytics.prototype._scheduleFlush = function () {
    var self = this;
    if (self._queue.length >= self.batchSize) {
      self._flush();
      return;
    }
    if (!self._flushTimer) {
      self._flushTimer = setTimeout(function () {
        self._flushTimer = null;
        self._flush();
      }, self.flushIntervalMs);
    }
  };

  Analytics.prototype._flush = function () {
    if (this._queue.length === 0 || this._inFlight) return;
    var batch = this._queue.splice(0, this.batchSize);
    var body = batch.length === 1 ? batch[0] : { batch: batch, project_id: this.projectId || undefined };
    this._send(body);
  };

  Analytics.prototype._send = function (body, retryCount) {
    var self = this;
    retryCount = retryCount || 0;
    self._inFlight = true;
    var url = (self.host.replace(/\/$/, "") || window.location.origin) + "/capture";
    var headers = { "Content-Type": "application/json" };
    if (self.apiKey) headers["X-API-Key"] = self.apiKey;
    fetch(url, {
      method: "POST",
      headers: headers,
      body: JSON.stringify(body),
      keepalive: true,
    })
      .then(function (res) {
        if (res.status === 202 || res.status === 200) {
          return;
        }
        throw new Error("Capture failed: " + res.status);
      })
      .catch(function (err) {
        if (retryCount < MAX_RETRIES) {
          setTimeout(function () {
            self._send(body, retryCount + 1);
          }, RETRY_BACKOFF_MS * (retryCount + 1));
        }
      })
      .finally(function () {
        self._inFlight = false;
        if (self._queue.length > 0) self._scheduleFlush();
      });
  };

  Analytics.prototype._onClick = function (e) {
    var target = e.target;
    if (!target || !target.tagName) return;
    var tag = target.tagName.toLowerCase();
    var text = (target.innerText || target.textContent || "").slice(0, 200);
    this.capture("$autocapture_click", {
      $tag: tag,
      $text: text,
      $href: target.href || undefined,
    });
  };

  Analytics.prototype._onPageview = function () {
    this.capture("$pageview", {
      $path: window.location.pathname,
      $url: window.location.href,
      $title: document.title,
    });
  };

  Analytics.prototype.start = function () {
    if (this.autocapture) {
      if (typeof document !== "undefined" && document.addEventListener) {
        document.addEventListener("click", this._onClick.bind(this), true);
        if (typeof history !== "undefined" && history.pushState) {
          var pushState = history.pushState;
          history.pushState = function () {
            pushState.apply(this, arguments);
            this._onPageview();
          }.bind(this);
        }
        this._onPageview();
      }
    }
    return this;
  };

  window.Analytics = Analytics;
  if (typeof module !== "undefined" && module.exports) module.exports = Analytics;
})(typeof window !== "undefined" ? window : global);
