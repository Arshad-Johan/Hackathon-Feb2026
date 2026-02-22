import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, type MetricsResponse } from "@/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const metricAccents: Record<string, string> = {
  default: "border-l-4 border-l-indigo-500",
  success: "border-l-4 border-l-emerald-500",
  warning: "border-l-4 border-l-amber-500",
  muted: "border-l-4 border-l-slate-300",
};

function MetricCard({
  title,
  value,
  sub,
  accent = "default",
}: {
  title: string;
  value: string | number;
  sub?: string;
  accent?: keyof typeof metricAccents;
}) {
  return (
    <Card className={`card-hover ${metricAccents[accent] ?? metricAccents.default} bg-white`}>
      <CardHeader className="pb-1">
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <span className="text-2xl font-bold text-slate-900">{value}</span>
        {sub != null && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
      </CardContent>
    </Card>
  );
}

export function DashboardPage() {
  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 10000,
  });
  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ["metrics"],
    queryFn: api.getMetrics,
    refetchInterval: 10000,
  });
  const { data: queueSize } = useQuery({
    queryKey: ["queue", "size"],
    queryFn: api.getQueueSize,
    refetchInterval: 5000,
  });

  const circuitState = (health?.circuit_breaker ?? metrics?.circuit_breaker) as { state?: string } | undefined;
  const state = circuitState?.state ?? "—";
  const incidentsCount = (metrics as MetricsResponse)?.master_incidents_count ?? "—";
  const agentsCount = (metrics as MetricsResponse)?.online_agents_count ?? "—";

  return (
    <div>
      <header className="page-header">
        <h1 className="page-title border-b-2 border-indigo-500 w-fit pb-1">Dashboard</h1>
        <p className="page-desc">
          System health, metrics, and quick links. Backend connected when status is OK.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="API status"
          value={health?.status ?? "…"}
          sub={health?.status === "ok" ? "Backend connected" : undefined}
          accent={health?.status === "ok" ? "success" : "default"}
        />
        <MetricCard
          title="Circuit breaker"
          value={metricsLoading ? "…" : state}
          sub="Transformer / fallback"
          accent="default"
        />
        <MetricCard
          title="Master incidents"
          value={metricsLoading ? "…" : incidentsCount}
          sub="Semantic dedup groups"
          accent="default"
        />
        <MetricCard
          title="Online agents"
          value={metricsLoading ? "…" : agentsCount}
          sub="Available for routing"
          accent="default"
        />
        <MetricCard
          title="Queue size"
          value={queueSize?.size ?? "…"}
          sub="Processed tickets ready"
          accent="muted"
        />
      </div>

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-slate-800">Quick actions</h2>
        <div className="mt-3 flex flex-wrap gap-3">
          <Button asChild variant="default">
            <Link to="/submit">Submit ticket</Link>
          </Button>
          <Button asChild variant="outline">
            <Link to="/queue">View queue</Link>
          </Button>
          <Button asChild variant="outline">
            <Link to="/activity">Activity log</Link>
          </Button>
          <Button asChild variant="outline">
            <Link to="/incidents">Incidents</Link>
          </Button>
          <Button asChild variant="outline">
            <Link to="/agents">Agents</Link>
          </Button>
        </div>
      </section>

      {health?.status === "ok" && (
        <Card className="mt-8 border-emerald-200 bg-emerald-50/50 shadow-sm">
          <CardContent className="pt-5">
            <p className="text-sm text-slate-700">
              <Badge variant="secondary" className="mr-2 bg-emerald-100 text-emerald-800">Connected</Badge>
              Backend is reachable at <code className="rounded bg-white px-1.5 py-0.5 text-xs font-medium text-slate-600 shadow-sm">{import.meta.env.VITE_API_URL ?? "http://localhost:8000"}</code>
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
