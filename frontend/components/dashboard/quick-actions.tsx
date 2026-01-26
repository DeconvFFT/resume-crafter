"use client";

import Link from "next/link";
import {
  FileUp,
  Target,
  FileOutput,
  Briefcase,
  FolderKanban,
  ArrowRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface QuickActionsPanelProps {
  documentsCount: number;
  experiencesCount: number;
  projectsCount: number;
  jobsCount: number;
  matchesCount: number;
}

interface Action {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  href: string;
  variant: "primary" | "secondary" | "outline";
  show: (props: QuickActionsPanelProps) => boolean;
}

const actions: Action[] = [
  // Primary actions based on workflow state
  {
    id: "upload-first",
    label: "Upload your first document",
    description: "Get started by uploading your resume or CV",
    icon: <FileUp className="h-5 w-5" />,
    href: "/documents",
    variant: "primary",
    show: (p) => p.documentsCount === 0,
  },
  {
    id: "add-experience",
    label: "Add work experience",
    description: "Add your professional history manually",
    icon: <Briefcase className="h-5 w-5" />,
    href: "/experiences",
    variant: "primary",
    show: (p) => p.documentsCount > 0 && p.experiencesCount === 0,
  },
  {
    id: "add-project",
    label: "Add a project",
    description: "Showcase your portfolio and side projects",
    icon: <FolderKanban className="h-5 w-5" />,
    href: "/projects",
    variant: "primary",
    show: (p) => p.experiencesCount > 0 && p.projectsCount === 0,
  },
  {
    id: "add-job",
    label: "Add a target job",
    description: "Analyze a job posting to match against",
    icon: <Target className="h-5 w-5" />,
    href: "/jobs",
    variant: "primary",
    show: (p) => (p.experiencesCount > 0 || p.projectsCount > 0) && p.jobsCount === 0,
  },
  {
    id: "generate-resume",
    label: "Generate your resume",
    description: "Create a tailored resume for a job",
    icon: <FileOutput className="h-5 w-5" />,
    href: "/resume",
    variant: "primary",
    show: (p) => p.jobsCount > 0 && p.matchesCount === 0,
  },
  // Secondary actions (always available when applicable)
  {
    id: "upload-more",
    label: "Upload document",
    description: "Add another file",
    icon: <FileUp className="h-4 w-4" />,
    href: "/documents",
    variant: "secondary",
    show: (p) => p.documentsCount > 0,
  },
  {
    id: "add-more-experience",
    label: "Add experience",
    description: "Add more work history",
    icon: <Briefcase className="h-4 w-4" />,
    href: "/experiences",
    variant: "secondary",
    show: (p) => p.experiencesCount > 0,
  },
  {
    id: "add-more-job",
    label: "Add job",
    description: "Analyze another posting",
    icon: <Target className="h-4 w-4" />,
    href: "/jobs",
    variant: "secondary",
    show: (p) => p.jobsCount > 0,
  },
];

export function QuickActionsPanel(props: QuickActionsPanelProps) {
  const primaryAction = actions.find(
    (a) => a.variant === "primary" && a.show(props)
  );
  const secondaryActions = actions.filter(
    (a) => a.variant === "secondary" && a.show(props)
  );

  return (
    <div className="space-y-6">
      {/* Primary Action - Editorial card style */}
      {primaryAction && (
        <Link
          href={primaryAction.href}
          className="block border-2 border-primary bg-card hover:bg-primary/5 transition-colors group relative"
        >
          {/* Corner marks */}
          <div className="absolute -top-2 -left-2 w-4 h-4 border-l-2 border-t-2 border-primary" aria-hidden="true" />
          <div className="absolute -bottom-2 -right-2 w-4 h-4 border-r-2 border-b-2 border-primary" aria-hidden="true" />

          <div className="flex items-start gap-6 p-6">
            <div className="flex items-center justify-center w-12 h-12 text-primary">
              {primaryAction.icon}
            </div>
            <div className="flex-1 min-w-0">
              <span className="font-mono text-xs uppercase tracking-widest text-primary">
                Recommended
              </span>
              <h3 className="font-semibold text-lg mt-1 group-hover:text-primary transition-colors">
                {primaryAction.label}
              </h3>
              <p className="text-sm text-muted-foreground mt-2">
                {primaryAction.description}
              </p>
            </div>
            <ArrowRight className="h-5 w-5 text-primary group-hover:translate-x-1 transition-transform mt-1" aria-hidden="true" />
          </div>
        </Link>
      )}

      {/* Secondary Actions - Editorial grid */}
      {secondaryActions.length > 0 && (
        <div>
          <h4 className="font-mono text-xs uppercase tracking-widest text-muted-foreground mb-4">
            Quick Actions
          </h4>
          <div className="grid grid-cols-3 gap-4">
            {secondaryActions.slice(0, 3).map((action) => (
              <Link
                key={action.id}
                href={action.href}
                className={cn(
                  "flex flex-col items-center justify-center p-6 border border-border",
                  "bg-background hover:border-foreground hover:bg-muted/30",
                  "transition-all group text-center"
                )}
              >
                <span className="text-muted-foreground group-hover:text-foreground transition-colors">
                  {action.icon}
                </span>
                <span className="text-sm font-medium mt-3 group-hover:text-foreground transition-colors">
                  {action.label}
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Empty State - Editorial style */}
      {!primaryAction && secondaryActions.length === 0 && (
        <div className="border border-border bg-card p-8 text-center">
          <FileOutput className="h-8 w-8 mx-auto text-muted-foreground mb-4" aria-hidden="true" />
          <p className="font-semibold text-lg">
            All caught up
          </p>
          <p className="text-sm text-muted-foreground mt-2">
            Generate more resumes or update your content.
          </p>
          <div className="flex justify-center gap-6 mt-6">
            <Link
              href="/resume"
              className="text-sm text-primary hover:underline underline-offset-4"
            >
              Generate resume
            </Link>
            <Link
              href="/documents"
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              Manage documents
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
