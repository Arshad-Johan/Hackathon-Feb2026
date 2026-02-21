import { Link, Outlet, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/", label: "Submit ticket" },
  { to: "/queue", label: "Queue" },
  { to: "/activity", label: "Activity" },
];

export function Layout() {
  const location = useLocation();
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-14 max-w-4xl items-center justify-between px-4">
          <Link to="/" className="text-lg font-semibold text-slate-900">
            Ticket Routing Engine
          </Link>
          <nav className="flex gap-6">
            {nav.map(({ to, label }) => (
              <Link
                key={to}
                to={to}
                className={cn(
                  "text-sm font-medium text-slate-600 hover:text-slate-900",
                  location.pathname === to && "text-slate-900"
                )}
              >
                {label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="flex-1 mx-auto w-full max-w-4xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
