import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type MasterIncident } from "@/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

function formatTime(ts: number) {
  return new Date(ts * 1000).toLocaleString(undefined, {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function IncidentCard({
  incident,
  onClose,
}: {
  incident: MasterIncident;
  onClose: (incidentId: string) => void;
}) {
  const isResolved = incident.status === "resolved";
  return (
    <Card className={`card-hover ${isResolved ? "border-slate-200 opacity-90" : "border-l-4 border-l-amber-500 border-amber-100 bg-amber-50/30"}`}>
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <CardTitle className="text-base">
          <Link to={`/incidents/${incident.incident_id}`} className="hover:underline">
            {incident.summary}
          </Link>
        </CardTitle>
        <div className="flex items-center gap-2">
          <Badge variant={isResolved ? "secondary" : "urgent"}>{incident.status}</Badge>
          {!isResolved && (
            <Button variant="outline" size="sm" onClick={() => onClose(incident.incident_id)}>
              Close incident
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p className="text-slate-600">
          <span className="font-medium text-slate-700">ID:</span>{" "}
          <code className="rounded bg-slate-100 px-1">{incident.incident_id}</code>
        </p>
        <p className="text-slate-600">
          <span className="font-medium text-slate-700">Root ticket:</span>{" "}
          <code className="rounded bg-slate-100 px-1">{incident.root_ticket_id}</code>
        </p>
        <p className="text-slate-600">
          <span className="font-medium text-slate-700">Tickets:</span> {incident.ticket_ids.length}
        </p>
        <p className="text-slate-500 text-xs">{formatTime(incident.created_at)}</p>
      </CardContent>
    </Card>
  );
}

export function IncidentsPage() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const queryClient = useQueryClient();
  const { data: incidents = [], isLoading, error } = useQuery({
    queryKey: ["incidents", statusFilter],
    queryFn: () => api.getIncidents(50, statusFilter),
    refetchInterval: 10000,
  });
  const closeMutation = useMutation({
    mutationFn: (incidentId: string) => api.closeIncident(incidentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
    },
  });
  const handleCloseIncident = (incidentId: string) => {
    closeMutation.mutate(incidentId);
  };

  return (
    <div>
      <header className="page-header">
        <h1 className="page-title border-b-2 border-indigo-500 w-fit pb-1">Master incidents</h1>
        <p className="page-desc">
          Semantic deduplication: similar tickets grouped into incidents (flash-flood suppression).
        </p>
      </header>

      <div className="flex flex-wrap gap-2">
        <Button
          variant={statusFilter === undefined ? "default" : "outline"}
          size="sm"
          onClick={() => setStatusFilter(undefined)}
        >
          All
        </Button>
        <Button
          variant={statusFilter === "open" ? "default" : "outline"}
          size="sm"
          onClick={() => setStatusFilter("open")}
        >
          Open
        </Button>
        <Button
          variant={statusFilter === "resolved" ? "default" : "outline"}
          size="sm"
          onClick={() => setStatusFilter("resolved")}
        >
          Resolved
        </Button>
      </div>

      <div className="mt-6">
        {error && (
          <p className="text-sm text-red-600">Failed to load incidents: {(error as Error).message}</p>
        )}
        {isLoading && (
          <div className="py-12 text-center text-slate-500">Loading…</div>
        )}
        {!error && !isLoading && incidents.length === 0 && (
          <Card>
            <CardContent className="py-12 text-center text-slate-500">
              No incidents found. Submit tickets to see semantic groupings.
            </CardContent>
          </Card>
        )}
        {!error && !isLoading && incidents.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2">
            {incidents.map((inc) => (
              <IncidentCard
                key={inc.incident_id}
                incident={inc}
                onClose={handleCloseIncident}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
