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
    <Card className="border-emerald-200 bg-emerald-50/50">
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
    <Card className="border-slate-200">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base">Ticket #{index + 1}</CardTitle>
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
            className="flex min-h-[80px] w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2"
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

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Submit tickets</h1>
      <p className="mt-1 text-sm text-slate-600">
        Add one or more tickets. Submit a single ticket or submit all at once for batch processing.
      </p>
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
    </div>
  );
}
