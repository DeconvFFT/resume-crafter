"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const routeLabels: Record<string, string> = {
  documents: "Documents",
  experiences: "Experiences",
  projects: "Projects",
  skills: "Skills",
  publications: "Publications",
  jobs: "Jobs",
  resume: "Resume",
  profile: "Profile",
};

const routeDescriptions: Record<string, string> = {
  "": "Your workspace overview",
  documents: "Upload and manage your files",
  experiences: "Work history and achievements",
  projects: "Portfolio and side projects",
  skills: "Technical and professional skills",
  publications: "Research papers and articles",
  jobs: "Target job descriptions",
  resume: "Generate tailored resumes",
  profile: "Account and settings",
};

export function Breadcrumbs() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);

  // Dashboard (root) breadcrumb
  if (segments.length === 0) {
    return (
      <nav className="flex flex-col gap-1" aria-label="Breadcrumb">
        <div className="flex items-center gap-3">
          <span className="font-mono text-xs text-primary uppercase tracking-widest">
            00
          </span>
          <h1 className="font-display text-2xl font-medium">Dashboard</h1>
        </div>
        <p className="font-body text-sm text-muted-foreground italic pl-8">
          {routeDescriptions[""]}
        </p>
      </nav>
    );
  }

  const currentSegment = segments[segments.length - 1];
  const currentLabel = routeLabels[currentSegment] || currentSegment;
  const currentDescription = routeDescriptions[currentSegment];

  return (
    <nav className="flex flex-col gap-2" aria-label="Breadcrumb">
      {/* Breadcrumb trail */}
      <div className="flex items-center gap-2 font-body text-sm">
        <Link
          href="/"
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          Dashboard
        </Link>
        {segments.map((segment, index) => {
          const path = "/" + segments.slice(0, index + 1).join("/");
          const isLast = index === segments.length - 1;
          const label = routeLabels[segment] || segment;

          return (
            <div key={path} className="flex items-center gap-2">
              <span className="text-muted-foreground" aria-hidden="true">
                /
              </span>
              {isLast ? (
                <span className="font-semibold text-foreground" aria-current="page">
                  {label}
                </span>
              ) : (
                <Link
                  href={path}
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  {label}
                </Link>
              )}
            </div>
          );
        })}
      </div>

      {/* Page title with editorial rule */}
      <div className="mt-2">
        <h1 className="font-display text-3xl font-medium tracking-tight">
          {currentLabel}
        </h1>
        <div className="editorial-rule" aria-hidden="true" />
        {currentDescription && (
          <p className="font-body text-base text-muted-foreground">
            {currentDescription}
          </p>
        )}
      </div>
    </nav>
  );
}
