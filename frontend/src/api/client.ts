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
};

export interface ActivityEvent {
  ts: number;
  type: string;
  data: Record<string, unknown>;
}
