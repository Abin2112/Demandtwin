let refreshing: Promise<boolean> | null = null;

export async function api<T>(path: string, method = "GET", body?: unknown, participant?: string): Promise<T> {
  const url = "/api/v1" + path;
  const headers: Record<string, string> = {};
  if (body instanceof Blob) headers["Content-Type"] = body.type;
  else if (body !== undefined) headers["Content-Type"] = "application/json";
  if (participant) headers["X-Participant-Key"] = participant;
  const options = { method, headers, body: body instanceof Blob ? body : body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store" as const, signal: AbortSignal.timeout(path === "/demo" || path.includes("/models/") ? 120000 : 20000) };
  let response = await fetch(url, options);
  if (response.status === 401 && !participant && (!path.startsWith("/auth/") || path === "/auth/me")) {
    refreshing ??= fetch("/api/v1/auth/refresh", { method: "POST" })
      .then((result) => result.ok)
      .finally(() => { refreshing = null; });
    if (await refreshing) response = await fetch(url, options);
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail;
    const message = Array.isArray(detail)
      ? detail.map(({ loc, msg }: { loc: string[]; msg: string }) => loc.slice(1).join(".") + " " + msg).join(" · ")
      : typeof detail === "string" ? detail : "Request failed (" + response.status + ")";
    throw Object.assign(new Error(message), { status: response.status });
  }
  return response.status === 204 ? undefined as T : response.json();
}

export type User = { id: string; email: string; role: string };
export type Project = { id: string; name: string; description: string; is_owner: boolean };
export type Segment = "value" | "balanced" | "premium";
export type Alternative = {
  name: string; price: number; grams: number; flavour: "classic" | "spicy";
  packaging: "standard" | "resealable"; positioning: "standard" | "premium";
};
export type Product = Alternative & {
  id: string; project_id: string; parent_id: string | null; category: string; location: string;
  segment: Segment; description: string; ingredients: string; features: string;
  packaging_image: string | null; cost: number | null; competitors: Alternative[];
};
export type Study = {
  id: string; name: string; status: string; synthetic: boolean; project_id: string; designs: Alternative[][];
  task_count: number; policy: { strategy: string; task_limit: number; segment_quotas: Record<string, number> };
};
export type StudyResults = {
  participants: number; complete: number; responses: number; choices: Record<string, number>; synthetic: boolean;
};
export type Calibration = { confidence: number; accuracy: number; n: number };
export type Score = { accuracy: number; brier: number; log_loss: number; rows: number; calibration: Calibration[] };
export type Parameters = { mean: number[]; covariance: number[][]; rows: number };
export type Model = {
  id: string; status: string; synthetic: boolean; error?: string; evidence_quality?: string; feature_version?: string;
  experiment_id: string; project_id: string; test_rows?: number; metrics?: Record<string, Score>;
  preferences?: { global: Parameters; features: string[]; segments: Record<string, Parameters> };
};
export type Simulation = {
  id: string; name: string; model_id: string;
  inputs: { product: Alternative; competitors: Alternative[]; opportunities: number };
  result: {
    synthetic: boolean; evidence_quality: string; choice: number[]; labels: string[]; abstain: boolean;
    interval_90: [number, number][]; expected_units: number[]; units_interval_90: [number, number][];
    warnings: string[]; elasticity: number | null; interpretation: string;
    segments: Record<string, { weight: number; choice: number[]; price_coefficient: number; utility_contributions: number[] }>;
  };
};
export type Report = { id: string; simulation_id: string; created: string };
export const money = (value: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(value);
export const percent = (value: number) => new Intl.NumberFormat("en-IN", { style: "percent", maximumFractionDigits: 1 }).format(value);
export const number = (value: number) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 1 }).format(value);
