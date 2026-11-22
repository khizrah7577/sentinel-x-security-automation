/**
 * API service and types for SENTINEL X.
 * Configured to work with local dev proxy, relative paths, or remote Railway backend via VITE_API_BASE_URL.
 */

function resolveApiBase(): string {
  const envUrl = (import.meta.env.VITE_API_BASE_URL || "").trim().replace(/\/+$/, "");
  if (!envUrl) {
    return "/api/v1";
  }
  if (envUrl.endsWith("/api/v1")) {
    return envUrl;
  }
  return `${envUrl}/api/v1`;
}

export const API_BASE = resolveApiBase();

/**
 * Builds the full endpoint URL.
 * Handles paths starting with or without /api/v1 and prevents duplicate prefixes.
 */
export function buildApiUrl(path: string): string {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  if (cleanPath.startsWith("/api/v1/")) {
    const baseWithoutPrefix = API_BASE.replace(/\/api\/v1$/, "");
    return `${baseWithoutPrefix}${cleanPath}`;
  }
  return `${API_BASE}${cleanPath}`;
}

/**
 * Builds a WebSocket URL for backend real-time endpoints (e.g. notifications).
 * Converts http(s) -> ws(s) pointing directly to Railway host or local host.
 */
export function getWebSocketUrl(path: string, token?: string | null): string {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const fullApiPath = cleanPath.startsWith("/api/v1") ? cleanPath : `/api/v1${cleanPath}`;

  let wsUrl: string;
  if (API_BASE.startsWith("http://") || API_BASE.startsWith("https://")) {
    const parsed = new URL(API_BASE);
    const wsProto = parsed.protocol === "https:" ? "wss:" : "ws:";
    wsUrl = `${wsProto}//${parsed.host}${fullApiPath}`;
  } else {
    const proto = typeof window !== "undefined" && window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = typeof window !== "undefined" ? window.location.host : "127.0.0.1:8000";
    wsUrl = `${proto}://${host}${fullApiPath}`;
  }

  if (token) {
    const sep = wsUrl.includes("?") ? "&" : "?";
    wsUrl += `${sep}token=${encodeURIComponent(token)}`;
  }
  return wsUrl;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  return localStorage.getItem("csfyp_token");
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem("csfyp_token", token);
  else localStorage.removeItem("csfyp_token");
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = buildApiUrl(path);
  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    let detail: string = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      detail = data.detail || detail;
      if (Array.isArray(detail)) {
        detail = detail.map((d: { msg?: string }) => d.msg || d).join(", ");
      }
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, String(detail));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export type User = {
  id: number;
  email: string;
  full_name: string;
  role: "admin" | "analyst";
  is_active: boolean;
};

export type DashboardStats = {
  total_network_events: number;
  normal_traffic: number;
  suspicious_traffic: number;
  detected_attacks: number;
  critical_incidents: number;
  pending_approvals: number;
  ml_models: number;
  active_model: string | null;
  ai_configured: boolean;
  monitoring_mode: string;
};

export type Health = {
  status: string;
  database: { status: string; error?: string };
  ai_configured: boolean;
  phase: number;
  monitoring_mode: string;
  response_mode?: string;
  app?: string;
  env?: string;
};

export type AnalyticsOverview = {
  range: string;
  start: string;
  end: string;
  bucket_seconds: number;
  counts: {
    events: number;
    traffic_flows: number;
    predictions: number;
    attack_predictions: number;
    incidents: number;
    investigations_total: number;
    investigations_running: number;
    pending_responses: number;
  };
  time_series: { t: string; events: number; normal: number; malicious: number }[];
  incident_series: { t: string; count: number }[];
  severity_distribution: { name: string; value: number }[];
  attack_categories: { name: string; value: number }[];
  protocol_distribution: { name: string; value: number }[];
  top_source_ips: { ip: string; count: number }[];
  top_dest_ports: { port: number; count: number }[];
  heatmap: { day: number; hour: number; count: number }[];
  detection_timeline: {
    id: number;
    t: string;
    label: string;
    severity: string;
    category: string;
    confidence: number;
  }[];
  model_performance: {
    id: number;
    name: string;
    model_type: string;
    is_active: boolean;
    accuracy: number | null;
    precision: number | null;
    recall: number | null;
    f1_score: number | null;
  }[];
  has_heatmap_data: boolean;
  has_time_series: boolean;
};

export type LabTopology = {
  mode: string;
  disclaimer: string;
  nodes: {
    id: string;
    label: string;
    role: string;
    ips: string[];
    description: string;
    observed: boolean;
    flow_count: number;
    suspicious_count: number;
    last_seen: string | null;
    observed_ips: string[];
  }[];
  edges: {
    source: string;
    target: string;
    count: number;
    suspicious_count: number;
    bytes: number;
    top_protocol: string | null;
    observed: boolean;
  }[];
  observed_edge_count: number;
  total_traffic_records: number;
  total_network_events: number;
};

export const AuthApi = {
  login: (email: string, password: string) =>
    api<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (data: { email: string; full_name: string; password: string; role?: "admin" | "analyst" }) =>
    api<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  me: () => api<User>("/auth/me"),
  logout: () => api<{ message: string }>("/auth/logout", { method: "POST" }),
};

export const DashboardApi = {
  stats: () => api<DashboardStats>("/dashboard/stats"),
};

export const HealthApi = {
  get: () => api<Health>("/health"),
};

export const AnalyticsApi = {
  overview: (range = "24h", start?: string, end?: string) => {
    const q = new URLSearchParams({ range });
    if (start) q.set("start", start);
    if (end) q.set("end", end);
    return api<AnalyticsOverview>(`/analytics/overview?${q}`);
  },
};

export const NetworkApi = {
  labTopology: () => api<LabTopology>("/network/lab-topology"),
  stats: () => api<Record<string, unknown>>("/network/stats"),
  status: () => api<Record<string, unknown>>("/network/status"),
  events: (limit = 50) => api<unknown[]>(`/network/events?limit=${limit}`),
  pcaps: () => api<unknown[]>("/network/pcaps"),
};
