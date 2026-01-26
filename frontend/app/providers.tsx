"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { initializeTheme } from "@/lib/stores/theme";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  // Initialize theme on mount (with error handling for privacy mode)
  useEffect(() => {
    try {
      const cleanup = initializeTheme();
      return cleanup;
    } catch (error) {
      console.error('Failed to initialize theme:', error);
    }
  }, []);

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
