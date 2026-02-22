/**
 * Typed API client for the Ticket Routing Engine.
 * Set getToken() when adding auth to attach Authorization header.
 */

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type TicketCategory = "Billing" | "Technical" | "Legal";

export interface IncomingTicket {
  ticket_id: string;
  subject: string;
  body: string;
  customer_id?: string | null;
}

export interface TicketAccepted {
  ticket_id: string;
  job_id: string;
  message: string;
}

export interface RoutedTicket {
  ticket_id: string;
  subject: string;
  body: string;
  customer_id: string | null;
  category: TicketCategory;
  is_urgent: boolean;
  priority_score: number;
  urgency_score: number;
}

export interface QueueSizeResponse {
  size: number;
}

// --- Milestone 3: Incidents (semantic deduplication) ---
export interface MasterIncident {
  incident_id: string;
  summary: string;
  root_ticket_id: string;
  ticket_ids: string[];
  created_at: number;
  status: string;
}

// --- Milestone 3: Agents (skill-based routing) ---
export interface SkillVector {
  tech: number;
  billing: number;
  legal: number;
}

export interface Agent {
  agent_id: string;
  display_name: string;
  skill_vector: SkillVector;
  max_concurrent_tickets: number;
  current_load: number;
  status: string;
}

export interface AssignmentsResponse {
  assignments: Array<{ ticket_id: string; agent_id: string }>;
}

export interface AgentTicketsResponse {
  agent_id: string;
  ticket_ids: string[];
}

// --- Urgency test (transformer/circuit breaker) ---
export interface UrgencyTestResponse {
  urgency_score: number;
  is_urgent: boolean;
}

// --- Metrics ---
export interface MetricsResponse {
  circuit_breaker?: { state: string; [k: string]: unknown };
  master_incidents_count?: number;
  online_agents_count?: number;
  error?: string;
}

export interface HealthResponse {
  status: string;
  circuit_breaker?: { state: string; [k: string]: unknown };
}

let getToken: (() => string | null) | null = null;

export function setAuthTokenGetter(fn: () => string | null) {
  getToken = fn;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (getToken) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((detail as { detail?: string }).detail ?? res.statusText);
  }
  if (res.status === 204) return undefined as T;
  if (res.status === 202) return res.json() as Promise<T>;
  return res.json() as Promise<T>;
}

export interface BatchTicketsAccepted {
  accepted: TicketAccepted[];
}

export const api = {
  submitTicket(payload: IncomingTicket) {
    return request<TicketAccepted>("/tickets", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  /** Submit multiple tickets in one request; returns 202 with list of accepted tickets. */
  submitTicketsBatch(payloads: IncomingTicket[]) {
    return request<BatchTicketsAccepted>("/tickets/batch", {
      method: "POST",
      body: JSON.stringify(payloads),
    });
  },
  getNextTicket() {
    return request<RoutedTicket>("/tickets/next");
  },
  peekNextTicket() {
    return request<RoutedTicket>("/tickets/peek");
  },
  getQueueSize() {
    return request<QueueSizeResponse>("/queue/size");
  },
  listQueue() {
    return request<RoutedTicket[]>("/queue");
  },
  clearQueue() {
    return request<{ status: string }>("/queue", { method: "DELETE" });
  },
  health() {
    return request<{ status: string }>("/health");
  },
  /** Recent backend activity (ticket accepted, processed, popped, queue cleared). */
  getActivity(limit = 100) {
    return request<{ events: ActivityEvent[] }>(`/activity?limit=${limit}`);
  },
  /** Test urgency score for text (transformer/circuit breaker); does not enqueue. */
  testUrgency(text: string) {
    return request<UrgencyTestResponse>("/urgency-score", {
      method: "POST",
      body: JSON.stringify({ text }),
    });
  },
  // --- Incidents ---
  getIncidents(limit = 50, status?: string) {
    const params = new URLSearchParams({ limit: String(limit) });
    if (status) params.set("status", status);
    return request<MasterIncident[]>(`/incidents?${params}`);
  },
  getIncident(incidentId: string) {
    return request<MasterIncident>(`/incidents/${incidentId}`);
  },
  // --- Agents ---
  listAgents(onlineOnly = false) {
    return request<Agent[]>(`/agents?online_only=${onlineOnly}`);
  },
  getAgent(agentId: string) {
    return request<Agent>(`/agents/${agentId}`);
  },
  registerAgent(agent: Agent) {
    return request<Agent>("/agents", {
      method: "POST",
      body: JSON.stringify(agent),
    });
  },
  getAssignments(limit = 100) {
    return request<AssignmentsResponse>(`/assignments?limit=${limit}`);
  },
  getAgentTickets(agentId: string) {
    return request<AgentTicketsResponse>(`/agents/${agentId}/tickets`);
  },
  // --- Health & metrics ---
  getMetrics() {
    return request<MetricsResponse>("/metrics");
  },
};

export interface ActivityEvent {
  ts: number;
  type: string;
  data: Record<string, unknown>;
}
