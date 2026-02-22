import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, type IncomingTicket, type TicketAccepted, type UrgencyTestResponse } from "@/api/client";
import { useToast } from "@/contexts/ToastContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const emptyForm: IncomingTicket = {
  ticket_id: "",
  subject: "",
  body: "",
  customer_id: "",
};

function AcceptedCard({ accepted }: { accepted: TicketAccepted }) {
  return (
    <Card className="card-hover border-l-4 border-l-emerald-500 border-emerald-100 bg-emerald-50/50">
      <CardContent className="pt-4">
        <p className="text-sm text-slate-600">
          <span className="font-medium">Ticket ID:</span> {accepted.ticket_id}
        </p>
        <p className="text-sm text-slate-600">
          <span className="font-medium">Job ID:</span>{" "}
          <code className="rounded bg-slate-200 px-1 text-xs">{accepted.job_id}</code>
        </p>
      </CardContent>
    </Card>
  );
}

function TicketFormRow({
  index,
  form,
  onChange,
  onRemove,
  canRemove,
}: {
  index: number;
  form: IncomingTicket;
  onChange: (f: IncomingTicket) => void;
  onRemove: () => void;
  canRemove: boolean;
}) {
  return (
    <Card className="card-hover border-slate-200">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base text-slate-800">Ticket #{index + 1}</CardTitle>
        {canRemove && (
          <Button type="button" variant="outline" size="sm" onClick={onRemove}>
            Remove
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Ticket ID *</Label>
          <Input
            value={form.ticket_id}
            onChange={(e) => onChange({ ...form, ticket_id: e.target.value })}
            placeholder="e.g. T-001"
            maxLength={100}
          />
        </div>
        <div className="space-y-2">
          <Label>Subject *</Label>
          <Input
            value={form.subject}
            onChange={(e) => onChange({ ...form, subject: e.target.value })}
            placeholder="Brief subject line"
            maxLength={200}
          />
        </div>
        <div className="space-y-2">
          <Label>Body *</Label>
          <textarea
            className="flex min-h-[80px] w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
            value={form.body}
            onChange={(e) => onChange({ ...form, body: e.target.value })}
            placeholder="Describe the issue..."
          />
        </div>
        <div className="space-y-2">
          <Label>Customer ID (optional)</Label>
          <Input
            value={form.customer_id ?? ""}
            onChange={(e) => onChange({ ...form, customer_id: e.target.value })}
            placeholder="e.g. C-123"
          />
        </div>
      </CardContent>
    </Card>
  );
}

export function SubmitTicketPage() {
  const [forms, setForms] = useState<IncomingTicket[]>([{ ...emptyForm }]);
  const [lastAccepted, setLastAccepted] = useState<TicketAccepted[]>([]);
  const { toast } = useToast();

  const submitSingleMutation = useMutation({
    mutationFn: api.submitTicket,
    onSuccess: (data) => {
      setLastAccepted([data]);
      toast("success", `Ticket ${data.ticket_id} accepted for processing.`);
      setForms([{ ...emptyForm }]);
    },
    onError: (err: Error) => {
      toast("error", err.message);
    },
  });

  const submitBatchMutation = useMutation({
    mutationFn: api.submitTicketsBatch,
    onSuccess: (data) => {
      setLastAccepted(data.accepted);
      const n = data.accepted.length;
      toast("success", `${n} ticket${n === 1 ? "" : "s"} accepted for processing.`);
      setForms([{ ...emptyForm }]);
    },
    onError: (err: Error) => {
      toast("error", err.message);
    },
  });

  const updateForm = (index: number, next: IncomingTicket) => {
    setForms((prev) => {
      const copy = [...prev];
      copy[index] = next;
      return copy;
    });
  };

  const addTicket = () => setForms((prev) => [...prev, { ...emptyForm }]);
  const removeTicket = (index: number) => {
    setForms((prev) => prev.filter((_, i) => i !== index));
  };

  const buildPayload = (form: IncomingTicket): IncomingTicket => ({
    ticket_id: form.ticket_id.trim(),
    subject: form.subject.trim(),
    body: form.body.trim(),
    customer_id: form.customer_id?.trim() || undefined,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const payloads = forms.map(buildPayload).filter((p) => p.ticket_id && p.subject && p.body);
    const invalid = forms.some(
      (f) =>
        !f.ticket_id.trim() ||
        !f.subject.trim() ||
        !f.body.trim()
    );
    if (forms.length > 1 && invalid) {
      toast("error", "Fill Ticket ID, Subject, and Body for every ticket, or remove empty rows.");
      return;
    }
    if (forms.length === 1) {
      const p = buildPayload(forms[0]);
      if (!p.ticket_id || !p.subject || !p.body) {
        toast("error", "Ticket ID, Subject, and Body are required.");
        return;
      }
      if (p.ticket_id.length > 100 || p.subject.length > 200) {
        toast("error", "Ticket ID or Subject too long.");
        return;
      }
      submitSingleMutation.mutate(p);
      return;
    }
    if (payloads.length === 0) {
      toast("error", "Add at least one ticket with Ticket ID, Subject, and Body.");
      return;
    }
    for (const p of payloads) {
      if (p.ticket_id.length > 100 || p.subject.length > 200) {
        toast("error", "Ticket ID or Subject too long in one of the tickets.");
        return;
      }
    }
    submitBatchMutation.mutate(payloads);
  };

  const isPending = submitSingleMutation.isPending || submitBatchMutation.isPending;

  const [urgencyTestText, setUrgencyTestText] = useState("");
  const [urgencyResult, setUrgencyResult] = useState<UrgencyTestResponse | null>(null);
  const urgencyMutation = useMutation({
    mutationFn: api.testUrgency,
    onSuccess: (data) => setUrgencyResult(data),
    onError: (err: Error) => toast("error", err.message),
  });

  return (
    <div>
      <header className="page-header">
        <h1 className="page-title border-b-2 border-indigo-500 w-fit pb-1">Submit tickets</h1>
        <p className="page-desc">
          Add one or more tickets. Submit a single ticket or submit all at once for batch processing.
        </p>
      </header>
      <form onSubmit={handleSubmit} className="mt-6 space-y-4 max-w-xl">
        <div className="space-y-4">
          {forms.map((form, index) => (
            <TicketFormRow
              key={index}
              index={index}
              form={form}
              onChange={(next) => updateForm(index, next)}
              onRemove={() => removeTicket(index)}
              canRemove={forms.length > 1}
            />
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" onClick={addTicket}>
            Add another ticket
          </Button>
          <Button type="submit" disabled={isPending}>
            {isPending ? "Submitting…" : forms.length === 1 ? "Submit ticket" : "Submit all tickets"}
          </Button>
        </div>
      </form>
      {lastAccepted.length > 0 && (
        <div className="mt-6 space-y-2">
          <h2 className="text-lg font-medium text-slate-900">
            Accepted for processing ({lastAccepted.length})
          </h2>
          <p className="text-xs text-slate-500">
            Tickets will be classified in the background. Check the Queue page once processed.
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            {lastAccepted.map((a) => (
              <AcceptedCard key={a.job_id} accepted={a} />
            ))}
          </div>
        </div>
      )}

      <Card className="mt-8 border-indigo-100 bg-indigo-50/30">
        <CardHeader>
          <CardTitle className="text-base text-slate-800">Test urgency score</CardTitle>
          <p className="text-sm text-slate-600">
            Backend urgency model (transformer/circuit breaker). Does not enqueue.
          </p>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <Input
              placeholder="Enter text to score urgency..."
              value={urgencyTestText}
              onChange={(e) => setUrgencyTestText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && urgencyMutation.mutate(urgencyTestText)}
            />
            <Button
              variant="secondary"
              onClick={() => urgencyMutation.mutate(urgencyTestText)}
              disabled={!urgencyTestText.trim() || urgencyMutation.isPending}
            >
              {urgencyMutation.isPending ? "…" : "Score"}
            </Button>
          </div>
          {urgencyResult != null && (
            <div className="flex flex-wrap items-center gap-2 rounded-lg bg-white px-3 py-2 text-sm shadow-inner border border-indigo-100">
              <span className="text-slate-700">S = {urgencyResult.urgency_score.toFixed(3)}</span>
              <Badge variant={urgencyResult.is_urgent ? "urgent" : "secondary"}>
                {urgencyResult.is_urgent ? "Urgent" : "Not urgent"}
              </Badge>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
