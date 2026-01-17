"use client";

import { useState } from "react";
import Link from "next/link";
import { useRegister } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowRight, Check } from "lucide-react";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const register = useRegister();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    register.mutate({ email, password, fullName: fullName || undefined });
  };

  // Password validation states
  const hasMinLength = password.length >= 8;
  const hasUppercase = /[A-Z]/.test(password);
  const hasLowercase = /[a-z]/.test(password);
  const hasNumber = /[0-9]/.test(password);

  return (
    <div className="min-h-screen bg-background flex">
      {/* Decorative Left Panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-foreground text-background relative overflow-hidden">
        {/* Corner marks */}
        <div className="absolute top-8 left-8 w-6 h-6 border-l-2 border-t-2 border-background/30" aria-hidden="true" />
        <div className="absolute bottom-8 right-8 w-6 h-6 border-r-2 border-b-2 border-background/30" aria-hidden="true" />

        {/* Decorative lines */}
        <div className="absolute top-0 left-2/3 w-px h-full bg-background/10" aria-hidden="true" />
        <div className="absolute top-3/4 left-0 w-full h-px bg-background/10" aria-hidden="true" />

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

          {/* Features list */}
          <div className="max-w-md">
            <span className="font-mono text-xs uppercase tracking-widest text-background/50">
              What you&apos;ll get
            </span>
            <h2 className="font-display text-3xl mt-4 mb-8">
              Everything you need to land your next role
            </h2>
            <div className="h-1 w-16 bg-background/30 mb-8" aria-hidden="true" />

            <ul className="space-y-4">
              {[
                "AI-powered resume tailoring",
                "Job description analysis",
                "Skills gap identification",
                "Multiple export formats",
              ].map((feature, index) => (
                <li key={index} className="flex items-start gap-3">
                  <span className="flex items-center justify-center w-5 h-5 border border-background/30 mt-0.5">
                    <Check className="h-3 w-3" aria-hidden="true" />
                  </span>
                  <span className="font-body text-sm text-background/80">
                    {feature}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs uppercase tracking-widest text-background/40">
              Est. 2024
            </span>
            <span className="font-mono text-xs text-background/40">
              Free to start
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
              Get started
            </span>
            <h1 className="font-display text-4xl font-medium mt-2">
              Create account
            </h1>
            <div className="mt-4 h-1 w-12 bg-foreground" aria-hidden="true" />
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="fullName">Full name</Label>
              <Input
                id="fullName"
                type="text"
                placeholder="John Doe"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                autoComplete="name"
                aria-describedby="fullName-description"
              />
              <p id="fullName-description" className="font-body text-xs text-muted-foreground italic">
                Optional - used for your resume
              </p>
            </div>

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
                placeholder="Create a strong password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
                aria-describedby="password-requirements"
              />

              {/* Password requirements */}
              <div id="password-requirements" className="pt-2 space-y-1.5">
                <p className="font-mono text-2xs uppercase tracking-widest text-muted-foreground mb-2">
                  Requirements
                </p>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { met: hasMinLength, label: "8+ characters" },
                    { met: hasUppercase, label: "Uppercase letter" },
                    { met: hasLowercase, label: "Lowercase letter" },
                    { met: hasNumber, label: "Number" },
                  ].map((req, index) => (
                    <div
                      key={index}
                      className={`flex items-center gap-2 font-body text-xs ${
                        req.met ? "text-success" : "text-muted-foreground"
                      }`}
                    >
                      <span
                        className={`flex items-center justify-center w-4 h-4 border ${
                          req.met
                            ? "border-success bg-success/10"
                            : "border-border"
                        }`}
                      >
                        {req.met && <Check className="h-2.5 w-2.5" aria-hidden="true" />}
                      </span>
                      {req.label}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <Button
              type="submit"
              className="w-full group mt-8"
              disabled={register.isPending || !hasMinLength || !hasUppercase || !hasLowercase || !hasNumber}
            >
              {register.isPending ? (
                "Creating account..."
              ) : (
                <>
                  Create account
                  <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" aria-hidden="true" />
                </>
              )}
            </Button>
          </form>

          {/* Error Display */}
          {register.isError && (
            <div className="mt-6 p-4 border-2 border-destructive bg-destructive/5">
              <p className="font-body text-sm text-destructive">
                {(register.error as Error)?.message || "Failed to create account. Please try again."}
              </p>
            </div>
          )}

          {/* Divider */}
          <div className="mt-10 pt-8 border-t border-border">
            <p className="font-body text-sm text-muted-foreground">
              Already have an account?{" "}
              <Link
                href="/login"
                className="font-medium text-foreground hover:text-primary transition-colors underline underline-offset-4"
              >
                Sign in
              </Link>
            </p>
          </div>

          {/* Terms */}
          <div className="mt-8">
            <p className="font-body text-xs text-muted-foreground leading-relaxed">
              By creating an account, you agree to our{" "}
              <Link href="/terms" className="underline underline-offset-2 hover:text-foreground transition-colors">
                Terms of Service
              </Link>{" "}
              and{" "}
              <Link href="/privacy" className="underline underline-offset-2 hover:text-foreground transition-colors">
                Privacy Policy
              </Link>
              .
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
