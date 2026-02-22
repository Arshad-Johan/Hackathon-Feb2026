import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type RoutedTicket } from "@/api/client";
import { useToast } from "@/contexts/ToastContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

function TicketRow({ ticket }: { ticket: RoutedTicket }) {
  const categoryVariant =
    ticket.category === "Technical"
      ? "technical"
      : ticket.category === "Billing"
        ? "billing"
        : "legal";
  const urgencyScore = typeof ticket.urgency_score === "number" ? ticket.urgency_score : null;
  const highUrgency = urgencyScore != null && urgencyScore > 0.8;
  return (
    <tr className="border-b border-slate-100 hover:bg-indigo-50/30 transition-colors">
      <td className="py-3 px-4 text-sm font-medium text-slate-900">
        {ticket.ticket_id}
      </td>
      <td className="py-3 px-4 text-sm text-slate-700">{ticket.subject}</td>
      <td className="py-3 px-4">
        <Badge variant={categoryVariant}>{ticket.category}</Badge>
      </td>
      <td className="py-3 px-4">
        {ticket.is_urgent ? (
          <Badge variant="urgent">Urgent</Badge>
        ) : (
          <span className="text-slate-500 text-sm">—</span>
        )}
      </td>
      <td className="py-3 px-4 text-sm font-medium text-slate-700">
        {urgencyScore != null ? urgencyScore.toFixed(2) : ticket.priority_score}
      </td>
      <td className="py-3 px-4">
        {highUrgency ? (
          <Badge variant="urgent" className="text-xs">S&gt;0.8</Badge>
        ) : (
          <span className="text-slate-400 text-sm">—</span>
        )}
      </td>
    </tr>
  );
}

export function QueuePage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data: sizeData, isLoading: sizeLoading } = useQuery({
    queryKey: ["queue", "size"],
    queryFn: api.getQueueSize,
    refetchInterval: 5000,
  });

  const { data: list = [], isLoading: listLoading } = useQuery({
    queryKey: ["queue", "list"],
    queryFn: api.listQueue,
    refetchInterval: 3000,
  });

  const popMutation = useMutation({
    mutationFn: api.getNextTicket,
    onSuccess: (ticket) => {
      queryClient.invalidateQueries({ queryKey: ["queue"] });
      toast("success", `Popped: ${ticket.ticket_id}`);
    },
    onError: (err: Error) => {
      toast("error", err.message);
    },
  });

  const clearMutation = useMutation({
    mutationFn: api.clearQueue,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["queue"] });
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      toast("success", "Queue cleared.");
    },
    onError: (err: Error) => {
      toast("error", err.message);
    },
  });

  const size = sizeData?.size ?? 0;
  const isLoading = sizeLoading || listLoading;

  return (
    <div>
      <header className="page-header">
        <h1 className="page-title border-b-2 border-indigo-500 w-fit pb-1">Queue</h1>
        <p className="page-desc">
          View waiting tickets and pop the next one by priority.
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-4">
        <Card className="card-hover min-w-[160px] border-l-4 border-l-indigo-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Queue size
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-2xl font-bold text-slate-900">
              {isLoading ? "—" : size}
            </span>
          </CardContent>
        </Card>
        <div className="flex gap-2">
          <Button
            variant="default"
            onClick={() => popMutation.mutate()}
            disabled={size === 0 || popMutation.isPending}
          >
            {popMutation.isPending ? "Popping…" : "Pop next"}
          </Button>
          <Button
            variant="destructive"
            onClick={() => clearMutation.mutate()}
            disabled={size === 0 || clearMutation.isPending}
          >
            {clearMutation.isPending ? "Clearing…" : "Clear queue"}
          </Button>
        </div>
      </div>

      <Card className="mt-6 overflow-hidden card-hover">
        <CardHeader className="bg-slate-50/80 border-b border-slate-100">
          <CardTitle className="text-lg text-slate-800">Waiting tickets</CardTitle>
          <p className="text-sm text-slate-600">
            Ordered by priority (highest first).
          </p>
        </CardHeader>
        <CardContent className="p-0">
          {listLoading ? (
            <div className="py-12 text-center text-slate-500">
              Loading…
            </div>
          ) : list.length === 0 ? (
            <div className="py-12 text-center text-slate-500">
              No tickets in queue.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200 bg-indigo-50/50">
                    <th className="py-3 px-4 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                      Ticket ID
                    </th>
                    <th className="py-3 px-4 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                      Subject
                    </th>
                    <th className="py-3 px-4 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                      Category
                    </th>
                    <th className="py-3 px-4 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                      Urgent
                    </th>
                    <th className="py-3 px-4 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                      Urgency S
                    </th>
                    <th className="py-3 px-4 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                      High (webhook)
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {list.map((ticket) => (
                    <TicketRow key={ticket.ticket_id} ticket={ticket} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
