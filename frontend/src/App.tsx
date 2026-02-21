import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { setAuthTokenGetter } from "@/api/client";
import { ToastProvider } from "@/contexts/ToastContext";
import { Layout } from "@/components/Layout";
import { RequireAuth } from "@/components/RequireAuth";
import { SubmitTicketPage } from "@/pages/SubmitTicketPage";
import { QueuePage } from "@/pages/QueuePage";
import { ActivityPage } from "@/pages/ActivityPage";
import { LoginPage } from "@/pages/LoginPage";
import { useEffect } from "react";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
});

function AuthTokenSync() {
  const { getToken } = useAuth();
  useEffect(() => {
    setAuthTokenGetter(getToken);
  }, [getToken]);
  return null;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<SubmitTicketPage />} />
        <Route
          path="queue"
          element={
            <RequireAuth>
              <QueuePage />
            </RequireAuth>
          }
        />
        <Route path="activity" element={<ActivityPage />} />
        <Route path="login" element={<LoginPage />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AuthTokenSync />
        <ToastProvider>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
