const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  token = null;
  setToken(token) {
    this.token = token;
    if (typeof window !== "undefined") {
      if (token) localStorage.setItem("api_token", token);
      else localStorage.removeItem("api_token");
    }
  }
  loadToken() {
    if (typeof window !== "undefined") {
      this.token = localStorage.getItem("api_token");
    }
    return this.token;
  }
  headers(extra = {}) {
    const h = { "Content-Type": "application/json", ...extra };
    if (this.token) h["Authorization"] = `Bearer ${this.token}`;
    return h;
  }
  async request(method, path, body, init) {
    const res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: this.headers(init?.headers),
      body: body !== void 0 ? JSON.stringify(body) : void 0,
      ...init
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const data = await res.json();
        if (data?.detail) detail = data.detail;
      } catch {
      }
      throw new Error(`${method} ${path} failed (${res.status}): ${detail}`);
    }
    if (res.status === 204) return void 0;
    return await res.json();
  }
  get(path) {
    return this.request("GET", path);
  }
  post(path, body) {
    return this.request("POST", path, body);
  }
  delete(path) {
    return this.request("DELETE", path);
  }
  /** Build the WebSocket URL with the token as a query param. */
  wsUrl(path) {
    const base = (process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000").replace(/^http/, "ws");
    const q = this.token ? `?token=${encodeURIComponent(this.token)}` : "";
    return `${base}${path}${q}`;
  }
}
const api = new ApiClient();
const endpoints = {
  health: () => api.get("/health"),
  startInterview: (payload) => api.post("/start-interview", payload),
  sessionStatus: (id) => api.get(`/session-status/${id}`),
  activeSessions: () => api.get("/active-sessions"),
  completedSessions: (limit = 50) => api.get(`/completed-sessions?limit=${limit}`),
  failedSessions: (limit = 50) => api.get(`/failed-sessions?limit=${limit}`),
  sessionStatistics: () => api.get("/session-statistics"),
  highRiskSessions: (threshold = 0.8) => api.get(`/high-risk-sessions?threshold=${threshold}`),
  // Coaching portal: reuses the existing final-report payload
  // (see docs/interview_report_api.md) as the source of coaching content
  // (strengths / improvements / detailed_feedback / per-question scoring).
  // TODO(Harsha): swap/extend this once a dedicated coaching response
  // structure lands — see CoachingReport's normalizeCoachingData().
  interviewReport: (sessionId) => api.get(`/interviews/${sessionId}/report`),
  candidateHistory: (candidateId) => api.get(`/candidates/${candidateId}/history`),
  workers: () => api.get("/workers"),
  workerStats: () => api.get("/worker-statistics"),
  registerWorker: (worker_id, capacity = 4) => api.post("/register-worker", { worker_id, capacity }),
  deregisterWorker: (worker_id) => api.delete(`/deregister-worker/${worker_id}`),
  sendHeartbeat: (worker_id, active_tasks) => api.post("/worker/heartbeat", { worker_id, active_tasks }),
  systemHealth: () => api.get("/system-health"),
  workerHealth: () => api.get("/worker-health"),
  schedulingStatus: () => api.get("/scheduling-status"),
  switchStrategy: (strategy) => api.post("/switch-strategy", strategy),
  faultStatistics: () => api.get("/fault-statistics"),
  failureLog: (limit = 50) => api.get(`/failure-log?limit=${limit}`),
  deadLetterQueue: (limit = 50) => api.get(`/dead-letter-queue?limit=${limit}`),
  retrySession: (session_id) => api.post(`/retry-session/${session_id}`),
  detectFailures: () => api.post("/detect-failures"),
  reportWebVitals: (payload) => api.post("/metrics/web-vitals", payload)
};
export {
  ApiClient,
  api,
  endpoints
};