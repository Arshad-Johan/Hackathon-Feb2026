import { Link, Outlet, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/", label: "Dashboard" },
  { to: "/submit", label: "Submit" },
  { to: "/queue", label: "Queue" },
  { to: "/activity", label: "Activity" },
  { to: "/incidents", label: "Incidents" },
  { to: "/agents", label: "Agents" },
];

export function Layout() {
  const location = useLocation();
  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4">
          <Link
            to="/"
            className="flex items-center gap-2 text-xl font-bold tracking-tight text-slate-900"
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white shadow-sm">
              T
            </span>
            Ticket Routing
          </Link>
          <nav className="flex flex-wrap items-center gap-1 sm:gap-1">
            {nav.map(({ to, label }) => (
              <Link
                key={to}
                to={to}
                className={cn(
                  "rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200",
                  location.pathname === to
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-600 hover:bg-indigo-50 hover:text-indigo-700"
                )}
              >
                {label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="flex-1 mx-auto w-full max-w-5xl px-4 py-8">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 bg-white py-4">
        <div className="mx-auto max-w-5xl px-4 text-center text-xs text-slate-500">
          Ticket Routing Engine · Async broker with ML-based urgency &amp; skill routing
        </div>
      </footer>
    </div>
  );
}
