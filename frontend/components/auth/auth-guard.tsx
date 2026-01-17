"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth";

interface AuthGuardProps {
  children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [isChecking, setIsChecking] = useState(true);

  // Get store values directly to avoid function reference issues
  const accessToken = useAuthStore((state) => state.accessToken);
  const expiresAt = useAuthStore((state) => state.expiresAt);
  const hasHydrated = useAuthStore((state) => state._hasHydrated);

  useEffect(() => {
    // Wait for Zustand to hydrate from localStorage
    if (!hasHydrated) {
      return;
    }

    // Check auth inline to avoid function reference issues
    const isValid = accessToken && expiresAt && Date.now() < expiresAt;

    if (!isValid) {
      const loginUrl = `/login?callbackUrl=${encodeURIComponent(pathname)}`;
      router.replace(loginUrl);
      return;
    }

    setIsChecking(false);
  }, [hasHydrated, accessToken, expiresAt, pathname, router]);

  // Show loading state while checking authentication
  if (isChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse">
          <div className="h-8 w-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
