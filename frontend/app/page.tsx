"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuthStore } from "@/lib/stores/auth";

export default function Home() {
  const router = useRouter();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  useEffect(() => {
    // Redirect authenticated users to dashboard
    if (isAuthenticated()) {
      router.replace("/documents");
    }
  }, [isAuthenticated, router]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="text-center space-y-8">
        <h1 className="text-5xl font-bold tracking-tight">
          Resume Crafter
        </h1>
        <p className="text-xl text-muted-foreground max-w-2xl">
          Craft the perfect resume for any job. Upload your experience,
          paste a job description, and let AI match your best qualifications.
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/login"
            className="inline-flex items-center justify-center rounded-md bg-primary px-8 py-3 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90"
          >
            Get Started
          </Link>
          <Link
            href="/register"
            className="inline-flex items-center justify-center rounded-md border border-input bg-background px-8 py-3 text-sm font-medium shadow-sm hover:bg-accent hover:text-accent-foreground"
          >
            Create Account
          </Link>
        </div>
      </div>
    </main>
  );
}
