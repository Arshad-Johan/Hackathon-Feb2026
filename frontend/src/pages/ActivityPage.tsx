import { useQuery } from "@tanstack/react-query";
import { api, type ActivityEvent } from "@/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const EVENT_LABELS: Record<string, { label: string; variant?: "default" | "secondary" | "outline" }> = {
  ticket_accepted: { label: "Accepted", variant: "secondary" },
  ticket_processed: { label: "Processed", variant: "default" },
  ticket_popped: { label: "Popped", variant: "outline" },
  queue_cleared: { label: "Queue cleared", variant: "outline" },
};

function formatTime(ts: number) {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString(undefined, { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function EventRow({ event }: { event: ActivityEvent }) {
  const { label, variant = "secondary" } = EVENT_LABELS[event.type] ?? { label: event.type };
  const data = event.data as Record<string, unknown>;
  return (
    <div className="flex flex-wrap items-start gap-2 border-b border-slate-100 py-3 last:border-0">
      <span className="text-slate-500 text-sm tabular-nums shrink-0">{formatTime(event.ts)}</span>
      <Badge variant={variant}>{label}</Badge>
      <span className="text-sm text-slate-700">
        {event.type === "ticket_accepted" && (
          <>Ticket <code className="rounded bg-slate-100 px-1">{String(data.ticket_id)}</code> → job <code className="rounded bg-slate-100 px-1 text-xs">{String(data.job_id)}</code></>
        )}
        {event.type === "ticket_processed" && (
          <>Ticket <code className="rounded bg-slate-100 px-1">{String(data.ticket_id)}</code> → <code>{String(data.category)}</code> · S={typeof data.urgency_score === "number" ? data.urgency_score.toFixed(2) : data.urgency_score}{data.is_urgent ? " (urgent)" : ""}</>
        )}
        {event.type === "ticket_popped" && (
          <>Popped <code className="rounded bg-slate-100 px-1">{String(data.ticket_id)}</code> (S={typeof data.urgency_score === "number" ? data.urgency_score.toFixed(2) : data.urgency_score})</>
        )}
        {event.type === "queue_cleared" && <>Processed queue cleared.</>}
        {!["ticket_accepted", "ticket_processed", "ticket_popped", "queue_cleared"].includes(event.type) && (
          <code className="text-xs">{JSON.stringify(data)}</code>
        )}
      </span>
    </div>
  );
}

export function ActivityPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["activity"],
    queryFn: () => api.getActivity(150),
    refetchInterval: 2000,
  });

  const events = data?.events ?? [];

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Backend activity</h1>
      <p className="mt-1 text-sm text-slate-600">
        Live view of ticket submissions, worker processing, queue pops, and queue clears. Updates every 2s.
      </p>
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-lg">Event log</CardTitle>
        </CardHeader>
        <CardContent>
          {error && (
            <p className="text-sm text-red-600">Failed to load activity: {(error as Error).message}</p>
          )}
          {isLoading && events.length === 0 && (
            <p className="text-sm text-slate-500">Loading…</p>
          )}
          {!error && events.length === 0 && !isLoading && (
            <p className="text-sm text-slate-500">No events yet. Submit a ticket to see activity.</p>
          )}
          {events.length > 0 && (
            <div className="divide-y divide-slate-100">
              {[...events].reverse().map((evt, i) => (
                <EventRow key={`${evt.ts}-${i}`} event={evt} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
