import * as React from "react";

export type Role = "user" | "admin";

export interface User {
  id: string;
  name: string;
  role: Role;
}

interface AuthContextValue {
  user: User | null;
  setUser: (user: User | null) => void;
  getToken: () => string | null;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<User | null>(null);
  const getToken = React.useCallback(() => {
    return null;
  }, []);
  const value = React.useMemo(
    () => ({ user, setUser, getToken }),
    [user, getToken]
  );
  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
