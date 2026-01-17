"use client";

import { useState } from "react";
import Link from "next/link";
import { useLogin } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowRight } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useLogin();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    login.mutate({ email, password });
  };

  return (
    <div className="min-h-screen bg-background flex">
      {/* Decorative Left Panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-foreground text-background relative overflow-hidden">
        {/* Corner marks */}
        <div className="absolute top-8 left-8 w-6 h-6 border-l-2 border-t-2 border-background/30" aria-hidden="true" />
        <div className="absolute bottom-8 right-8 w-6 h-6 border-r-2 border-b-2 border-background/30" aria-hidden="true" />

        {/* Decorative lines */}
        <div className="absolute top-0 left-1/3 w-px h-full bg-background/10" aria-hidden="true" />
        <div className="absolute top-1/4 left-0 w-full h-px bg-background/10" aria-hidden="true" />

        {/* Content */}
        <div className="flex flex-col justify-between p-12 w-full">
          {/* Logo */}
          <div>
            <Link href="/" className="inline-block">
              <span className="font-display text-2xl tracking-wide">
                Resume Crafter
              </span>
            </Link>
          </div>

          {/* Quote */}
          <div className="max-w-md">
            <blockquote className="font-display text-4xl leading-tight tracking-tight">
              &ldquo;Craft the story of your career with precision and purpose.&rdquo;
            </blockquote>
            <div className="mt-8 h-1 w-16 bg-background/30" aria-hidden="true" />
            <p className="mt-6 font-body text-sm text-background/60 italic">
              Transform your experience into compelling narratives that resonate with employers.
            </p>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs uppercase tracking-widest text-background/40">
              Est. 2024
            </span>
            <span className="font-mono text-xs text-background/40">
              v1.0
            </span>
          </div>
        </div>
      </div>

      {/* Form Right Panel */}
      <div className="flex-1 flex flex-col justify-center px-8 py-12 lg:px-16">
        <div className="w-full max-w-md mx-auto">
          {/* Mobile Logo */}
          <div className="lg:hidden text-center mb-12">
            <Link href="/" className="inline-block">
              <span className="font-display text-2xl tracking-wide">
                Resume Crafter
              </span>
            </Link>
          </div>

          {/* Header */}
          <div className="mb-10">
            <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
              Welcome back
            </span>
            <h1 className="font-display text-4xl font-medium mt-2">
              Sign in
            </h1>
            <div className="mt-4 h-1 w-12 bg-foreground" aria-hidden="true" />
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-8">
            <div className="space-y-2">
              <Label htmlFor="email">Email address</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>

            <Button
              type="submit"
              className="w-full group"
              disabled={login.isPending}
            >
              {login.isPending ? (
                "Signing in..."
              ) : (
                <>
                  Sign in
                  <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" aria-hidden="true" />
                </>
              )}
            </Button>
          </form>

          {/* Error Display */}
          {login.isError && (
            <div className="mt-6 p-4 border-2 border-destructive bg-destructive/5">
              <p className="font-body text-sm text-destructive">
                {(login.error as Error)?.message || "Invalid email or password. Please try again."}
              </p>
            </div>
          )}

          {/* Divider */}
          <div className="mt-10 pt-8 border-t border-border">
            <p className="font-body text-sm text-muted-foreground">
              Don&apos;t have an account?{" "}
              <Link
                href="/register"
                className="font-medium text-foreground hover:text-primary transition-colors underline underline-offset-4"
              >
                Create one
              </Link>
            </p>
          </div>

          {/* Footer info */}
          <div className="mt-12 pt-8 border-t border-border">
            <p className="font-mono text-2xs uppercase tracking-widest text-muted-foreground">
              Secure authentication powered by modern standards
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
