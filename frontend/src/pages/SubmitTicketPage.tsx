import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, type IncomingTicket, type TicketAccepted } from "@/api/client";
import { useToast } from "@/contexts/ToastContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const emptyForm: IncomingTicket = {
  ticket_id: "",
  subject: "",
  body: "",
  customer_id: "",
};

function AcceptedCard({ accepted }: { accepted: TicketAccepted }) {
  return (
    <Card className="mt-6 border-emerald-200 bg-emerald-50/50">
      <CardHeader>
        <CardTitle className="text-lg">Accepted for processing</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <p className="text-sm text-slate-600">
          <span className="font-medium">Ticket ID:</span> {accepted.ticket_id}
        </p>
        <p className="text-sm text-slate-600">
          <span className="font-medium">Job ID:</span>{" "}
          <code className="rounded bg-slate-200 px-1 text-xs">{accepted.job_id}</code>
        </p>
        <p className="text-sm text-slate-600">{accepted.message}</p>
        <p className="mt-2 text-xs text-slate-500">
          The ticket will be classified in the background. Check the Queue page to see it once
          processed.
        </p>
      </CardContent>
    </Card>
  );
}

export function SubmitTicketPage() {
  const [form, setForm] = useState<IncomingTicket>(emptyForm);
  const [lastAccepted, setLastAccepted] = useState<TicketAccepted | null>(null);
  const { toast } = useToast();

  const submitMutation = useMutation({
    mutationFn: api.submitTicket,
    onSuccess: (data) => {
      setLastAccepted(data);
      toast("success", `Ticket ${data.ticket_id} accepted for processing.`);
      setForm(emptyForm);
    },
    onError: (err: Error) => {
      toast("error", err.message);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload: IncomingTicket = {
      ticket_id: form.ticket_id.trim(),
      subject: form.subject.trim(),
      body: form.body.trim(),
      customer_id: form.customer_id?.trim() || undefined,
    };
    if (!payload.ticket_id || !payload.subject || !payload.body) {
      toast("error", "Ticket ID, Subject, and Body are required.");
      return;
    }
    if (payload.ticket_id.length > 100 || payload.subject.length > 200) {
      toast("error", "Ticket ID or Subject too long.");
      return;
    }
    submitMutation.mutate(payload);
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Submit a ticket</h1>
      <p className="mt-1 text-sm text-slate-600">
        Enter ticket details. The engine will classify and prioritize it.
      </p>
      <form onSubmit={handleSubmit} className="mt-6 space-y-4 max-w-xl">
        <div className="space-y-2">
          <Label htmlFor="ticket_id">Ticket ID *</Label>
          <Input
            id="ticket_id"
            value={form.ticket_id}
            onChange={(e) => setForm((f) => ({ ...f, ticket_id: e.target.value }))}
            placeholder="e.g. T-001"
            maxLength={100}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="subject">Subject *</Label>
          <Input
            id="subject"
            value={form.subject}
            onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))}
            placeholder="Brief subject line"
            maxLength={200}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="body">Body *</Label>
          <textarea
            id="body"
            className="flex min-h-[120px] w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2"
            value={form.body}
            onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
            placeholder="Describe the issue..."
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="customer_id">Customer ID (optional)</Label>
          <Input
            id="customer_id"
            value={form.customer_id ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, customer_id: e.target.value }))}
            placeholder="e.g. C-123"
          />
        </div>
        <Button type="submit" disabled={submitMutation.isPending}>
          {submitMutation.isPending ? "Submitting…" : "Submit ticket"}
        </Button>
      </form>
      {lastAccepted && <AcceptedCard accepted={lastAccepted} />}
    </div>
  );
}
