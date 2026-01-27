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
  // Use store-level tracking instead of component-level ref
  // This persists across navigation/component remounts
  const hasVerifiedAuth = useAuthStore((state) => state._hasVerifiedAuth);
  const setHasVerifiedAuth = useAuthStore((state) => state.setHasVerifiedAuth);

  useEffect(() => {
    // Wait for Zustand to hydrate from localStorage
    if (!hasHydrated) {
      return;
    }

    // Check auth inline to avoid function reference issues
    const isValid = accessToken && expiresAt && Date.now() < expiresAt;

    if (!isValid) {
      // Only redirect if we haven't successfully authenticated before in this session
      // This prevents false logouts during navigation when state might briefly be stale
      // The hasVerifiedAuth is stored in Zustand (in memory), so it persists across
      // component remounts during navigation
      if (!hasVerifiedAuth) {
        const loginUrl = `/login?callbackUrl=${encodeURIComponent(pathname)}`;
        router.replace(loginUrl);
      }
      return;
    }

    // Mark that we've successfully authenticated at least once in this session
    // This is stored in Zustand (in memory, not persisted to localStorage)
    if (!hasVerifiedAuth) {
      setHasVerifiedAuth(true);
    }
    setIsChecking(false);
  }, [hasHydrated, accessToken, expiresAt, pathname, router, hasVerifiedAuth, setHasVerifiedAuth]);

  // Also check if the token has actually expired (not just null from a race condition)
  useEffect(() => {
    if (!hasHydrated || !hasVerifiedAuth) return;

    // If we've previously authenticated but now the token is truly expired, redirect
    const isExpired = expiresAt && Date.now() >= expiresAt;
    if (isExpired) {
      const loginUrl = `/login?callbackUrl=${encodeURIComponent(pathname)}`;
      router.replace(loginUrl);
    }
  }, [hasHydrated, expiresAt, pathname, router, hasVerifiedAuth]);

  // If we've already verified auth in this session, don't show loading state
  // This allows instant navigation between authenticated pages
  if (hasVerifiedAuth && hasHydrated) {
    return <>{children}</>;
  }

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
