"use client";

import { SessionProvider } from "next-auth/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { ToastProvider } from "@/components/ui/toast";
import { RealtimeProvider } from "@/components/realtime/realtime-provider";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 30_000, refetchOnWindowFocus: false },
        },
      }),
  );

  return (
    <SessionProvider>
      <QueryClientProvider client={queryClient}>
        {/* Inert until Supabase env is set (Phase 0) — no behavior change. */}
        <RealtimeProvider>
          <ToastProvider>{children}</ToastProvider>
        </RealtimeProvider>
      </QueryClientProvider>
    </SessionProvider>
  );
}
