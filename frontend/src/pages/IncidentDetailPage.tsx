import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "@/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

function formatTime(ts: number) {
  return new Date(ts * 1000).toLocaleString(undefined, {
    dateStyle: "short",
    timeStyle: "short",
  });
}

export function IncidentDetailPage() {
  const { incidentId } = useParams<{ incidentId: string }>();
  const queryClient = useQueryClient();
  const { data: incident, isLoading, error } = useQuery({
    queryKey: ["incident", incidentId],
    queryFn: () => api.getIncident(incidentId!),
    enabled: !!incidentId,
  });
  const closeMutation = useMutation({
    mutationFn: () => api.closeIncident(incidentId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incident", incidentId] });
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
    },
  });

  if (!incidentId) {
    return (
      <div>
        <p className="text-sm text-red-600">Missing incident ID.</p>
        <Link to="/incidents" className="text-indigo-600 hover:underline">Back to incidents</Link>
      </div>
    );
  }
  if (error) {
    return (
      <div>
        <p className="text-sm text-red-600">Failed to load incident: {(error as Error).message}</p>
        <Link to="/incidents" className="text-indigo-600 hover:underline">Back to incidents</Link>
      </div>
    );
  }
  if (isLoading || !incident) {
    return <div className="py-12 text-center text-slate-500">Loading…</div>;
  }

  const isResolved = incident.status === "resolved";

  return (
    <div>
      <header className="page-header">
        <div className="flex items-center gap-3">
          <Link to="/incidents" className="text-slate-500 hover:text-slate-700 text-sm">← Incidents</Link>
        </div>
        <h1 className="page-title border-b-2 border-indigo-500 w-fit pb-1">Incident {incident.incident_id}</h1>
        <p className="page-desc">{incident.summary}</p>
      </header>

      <Card className={`mt-6 ${isResolved ? "border-slate-200" : "border-l-4 border-l-amber-500 border-amber-100 bg-amber-50/30"}`}>
        <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
          <CardTitle className="text-base">Details</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant={isResolved ? "secondary" : "urgent"}>{incident.status}</Badge>
            {!isResolved && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => closeMutation.mutate()}
                disabled={closeMutation.isPending}
              >
                {closeMutation.isPending ? "Closing…" : "Close incident"}
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p className="text-slate-600">
            <span className="font-medium text-slate-700">Root ticket:</span>{" "}
            <code className="rounded bg-slate-100 px-1">{incident.root_ticket_id}</code>
          </p>
          <p className="text-slate-600">
            <span className="font-medium text-slate-700">Tickets in this incident:</span> {incident.ticket_ids.length}
          </p>
          <p className="text-slate-500 text-xs">{formatTime(incident.created_at)}</p>
          {incident.ticket_ids.length > 0 && (
            <div className="mt-3">
              <span className="font-medium text-slate-700">Ticket IDs:</span>
              <ul className="mt-1 list-inside list-disc text-slate-600">
                {incident.ticket_ids.map((tid) => (
                  <li key={tid}><code className="rounded bg-slate-100 px-1">{tid}</code></li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
