import { useAuth } from "@/contexts/AuthContext";
import type { Role } from "@/contexts/AuthContext";

interface RequireAuthProps {
  children: React.ReactNode;
  roles?: Role[];
}

/**
 * Protects routes by requiring auth (and optionally a role).
 * When auth is added: redirect to /login if !user; show Unauthorized if role mismatch.
 */
export function RequireAuth({ children, roles }: RequireAuthProps) {
  const { user } = useAuth();

  if (user != null && roles?.length && !roles.includes(user.role)) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <p className="text-lg text-slate-600">Unauthorized.</p>
      </div>
    );
  }

  return <>{children}</>;
}
