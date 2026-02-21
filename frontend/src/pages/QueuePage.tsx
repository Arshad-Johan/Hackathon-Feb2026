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
  return (
    <tr className="border-b border-slate-100 hover:bg-slate-50/50">
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
        {ticket.priority_score}
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
      <h1 className="text-2xl font-semibold text-slate-900">Queue</h1>
      <p className="mt-1 text-sm text-slate-600">
        View waiting tickets and pop the next one by priority.
      </p>

      <div className="mt-6 flex flex-wrap items-center gap-4">
        <Card className="min-w-[140px]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-600">
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

      <Card className="mt-6 overflow-hidden">
        <CardHeader>
          <CardTitle className="text-lg">Waiting tickets</CardTitle>
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
                  <tr className="border-b border-slate-200 bg-slate-50/80">
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
                      Priority
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
