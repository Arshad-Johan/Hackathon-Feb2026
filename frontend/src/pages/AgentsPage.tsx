import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type Agent, type SkillVector } from "@/api/client";
import { useToast } from "@/contexts/ToastContext";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const defaultSkillVector: SkillVector = { tech: 0.34, billing: 0.33, legal: 0.33 };

function AgentCard({ agent }: { agent: Agent }) {
  const sv = agent.skill_vector;
  const isOnline = agent.status === "online";
  return (
    <Card className={`card-hover ${isOnline ? "border-l-4 border-l-emerald-500 border-emerald-100 bg-emerald-50/20" : "border-slate-200"}`}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base">{agent.display_name || agent.agent_id}</CardTitle>
        <Badge variant={isOnline ? "secondary" : "outline"}>{agent.status}</Badge>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p className="text-slate-600">
          <span className="font-medium text-slate-700">ID:</span>{" "}
          <code className="rounded bg-slate-100 px-1">{agent.agent_id}</code>
        </p>
        <p className="text-slate-600">
          Load: {agent.current_load} / {agent.max_concurrent_tickets}
        </p>
        <p className="text-slate-600">
          Skills: T={sv.tech.toFixed(2)} B={sv.billing.toFixed(2)} L={sv.legal.toFixed(2)}
        </p>
      </CardContent>
    </Card>
  );
}

export function AgentsPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [onlineOnly, setOnlineOnly] = useState(false);
  const [form, setForm] = useState<Partial<Agent>>({
    agent_id: "",
    display_name: "",
    skill_vector: { ...defaultSkillVector },
    max_concurrent_tickets: 10,
    status: "online",
  });

  const { data: agents = [], isLoading, error } = useQuery({
    queryKey: ["agents", onlineOnly],
    queryFn: () => api.listAgents(onlineOnly),
    refetchInterval: 10000,
  });

  const registerMutation = useMutation({
    mutationFn: api.registerAgent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      toast("success", "Agent registered.");
      setForm({
        agent_id: "",
        display_name: "",
        skill_vector: { ...defaultSkillVector },
        max_concurrent_tickets: 10,
        status: "online",
      });
    },
    onError: (err: Error) => toast("error", err.message),
  });

  const handleRegister = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.agent_id?.trim()) {
      toast("error", "Agent ID is required.");
      return;
    }
    registerMutation.mutate({
      agent_id: form.agent_id.trim(),
      display_name: (form.display_name ?? "").trim() || form.agent_id.trim(),
      skill_vector: form.skill_vector ?? defaultSkillVector,
      max_concurrent_tickets: form.max_concurrent_tickets ?? 10,
      current_load: 0,
      status: form.status ?? "online",
    });
  };

  return (
    <div>
      <header className="page-header">
        <h1 className="page-title border-b-2 border-indigo-500 w-fit pb-1">Agents</h1>
        <p className="page-desc">
          Skill-based routing: register agents and view assignments. Toggle online-only to see available capacity.
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant={onlineOnly ? "default" : "outline"}
          size="sm"
          onClick={() => setOnlineOnly(true)}
        >
          Online only
        </Button>
        <Button
          variant={!onlineOnly ? "default" : "outline"}
          size="sm"
          onClick={() => setOnlineOnly(false)}
        >
          All agents
        </Button>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {error && (
            <p className="text-sm text-red-600">Failed to load agents: {(error as Error).message}</p>
          )}
          {isLoading && (
            <div className="py-12 text-center text-slate-500">Loading…</div>
          )}
          {!error && !isLoading && agents.length === 0 && (
            <Card>
              <CardContent className="py-12 text-center text-slate-500">
                No agents found. Register one below (or ensure backend has seeded mock agents).
              </CardContent>
            </Card>
          )}
          {!error && !isLoading && agents.length > 0 && (
            <div className="grid gap-4 sm:grid-cols-2">
              {agents.map((a) => (
                <AgentCard key={a.agent_id} agent={a} />
              ))}
            </div>
          )}
        </div>

        <Card className="card-hover border-indigo-100 bg-indigo-50/20">
          <CardHeader>
            <CardTitle className="text-lg text-slate-800">Register agent</CardTitle>
            <p className="text-sm text-slate-600">Add or update an agent for skill-based routing.</p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleRegister} className="space-y-4">
              <div className="space-y-2">
                <Label>Agent ID *</Label>
                <Input
                  value={form.agent_id ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, agent_id: e.target.value }))}
                  placeholder="e.g. agent-1"
                />
              </div>
              <div className="space-y-2">
                <Label>Display name</Label>
                <Input
                  value={form.display_name ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
                  placeholder="Optional"
                />
              </div>
              <div className="space-y-2">
                <Label>Max concurrent tickets</Label>
                <Input
                  type="number"
                  min={1}
                  value={form.max_concurrent_tickets ?? 10}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, max_concurrent_tickets: parseInt(e.target.value, 10) || 10 }))
                  }
                />
              </div>
              <Button type="submit" disabled={registerMutation.isPending}>
                {registerMutation.isPending ? "Registering…" : "Register"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
