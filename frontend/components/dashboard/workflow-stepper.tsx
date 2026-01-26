"use client";

import Link from "next/link";
import { FileUp, Cpu, Target, FileOutput, Check, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface WorkflowStepperProps {
  documentsCount: number;
  experiencesCount: number;
  projectsCount: number;
  jobsCount: number;
  matchesCount: number;
}

interface Step {
  id: string;
  number: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  href: string;
  isComplete: (props: WorkflowStepperProps) => boolean;
  isActive: (props: WorkflowStepperProps) => boolean;
}

const steps: Step[] = [
  {
    id: "upload",
    number: "01",
    label: "Upload",
    description: "Add your source documents",
    icon: <FileUp className="h-5 w-5" />,
    href: "/documents",
    isComplete: (p) => p.documentsCount > 0,
    isActive: (p) => p.documentsCount === 0,
  },
  {
    id: "extract",
    number: "02",
    label: "Extract",
    description: "Parse experiences & projects",
    icon: <Cpu className="h-5 w-5" />,
    href: "/experiences",
    isComplete: (p) => p.experiencesCount > 0 || p.projectsCount > 0,
    isActive: (p) => p.documentsCount > 0 && p.experiencesCount === 0 && p.projectsCount === 0,
  },
  {
    id: "match",
    number: "03",
    label: "Match",
    description: "Analyze target job requirements",
    icon: <Target className="h-5 w-5" />,
    href: "/jobs",
    isComplete: (p) => p.jobsCount > 0,
    isActive: (p) => (p.experiencesCount > 0 || p.projectsCount > 0) && p.jobsCount === 0,
  },
  {
    id: "generate",
    number: "04",
    label: "Generate",
    description: "Create your tailored resume",
    icon: <FileOutput className="h-5 w-5" />,
    href: "/resume",
    isComplete: (p) => p.matchesCount > 0,
    isActive: (p) => p.jobsCount > 0,
  },
];

export function WorkflowStepper(props: WorkflowStepperProps) {
  const completedCount = steps.filter((s) => s.isComplete(props)).length;
  const activeStep = steps.find((s) => s.isActive(props));

  return (
    <div className="border border-border bg-card p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h3 className="font-semibold text-xl">Workflow</h3>
          <div className="w-10 h-1 bg-foreground mt-3" aria-hidden="true" />
        </div>
        <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
          {completedCount} / {steps.length}
        </span>
      </div>

      {/* Vertical Timeline */}
      <div className="relative" role="list" aria-label="Workflow steps">
        {/* Connecting Line */}
        <div
          className="absolute left-[19px] top-8 bottom-8 w-[2px] bg-border"
          aria-hidden="true"
        />
        {/* Progress Line */}
        <div
          className="absolute left-[19px] top-8 w-[2px] bg-primary transition-all duration-500"
          style={{
            height: `calc(${(completedCount / steps.length) * 100}% - 32px)`,
          }}
          aria-hidden="true"
        />

        {/* Steps */}
        <div className="space-y-6">
          {steps.map((step) => {
            const complete = step.isComplete(props);
            const active = step.isActive(props);

            return (
              <Link
                key={step.id}
                href={step.href}
                className="group relative flex items-start gap-6 pl-0"
                role="listitem"
                aria-current={active ? "step" : undefined}
              >
                {/* Step Number / Check */}
                <div
                  className={cn(
                    "relative z-10 flex items-center justify-center w-10 h-10 border-2 transition-all",
                    complete
                      ? "bg-primary border-primary text-primary-foreground"
                      : active
                      ? "bg-background border-primary text-primary"
                      : "bg-background border-border text-muted-foreground"
                  )}
                >
                  {complete ? (
                    <Check className="h-5 w-5" aria-label="Completed" />
                  ) : (
                    <span className="font-semibold text-lg">
                      {step.number}
                    </span>
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 pt-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "font-mono text-xs uppercase tracking-widest transition-colors",
                        complete || active ? "text-foreground" : "text-muted-foreground"
                      )}
                    >
                      {step.label}
                    </span>
                    {active && (
                      <span className="px-2 py-0.5 bg-primary/10 text-primary font-mono text-2xs uppercase tracking-widest">
                        Current
                      </span>
                    )}
                    {complete && (
                      <span className="px-2 py-0.5 bg-success/10 text-success font-mono text-2xs uppercase tracking-widest">
                        Done
                      </span>
                    )}
                  </div>
                  <p
                    className={cn(
                      "text-sm mt-1 transition-colors",
                      complete || active ? "text-muted-foreground" : "text-muted-foreground"
                    )}
                  >
                    {step.description}
                  </p>
                </div>

                {/* Arrow on hover */}
                <ArrowRight
                  className={cn(
                    "h-4 w-4 mt-2 opacity-0 -translate-x-2 transition-all",
                    "group-hover:opacity-100 group-hover:translate-x-0",
                    active ? "text-primary" : "text-muted-foreground"
                  )}
                  aria-hidden="true"
                />
              </Link>
            );
          })}
        </div>
      </div>

      {/* Active Step CTA */}
      {activeStep && (
        <Link
          href={activeStep.href}
          className="mt-8 flex items-center justify-between w-full p-4 border-2 border-primary bg-primary/5 hover:bg-primary/10 transition-colors group"
        >
          <div className="flex items-center gap-4">
            <span className="text-primary">{activeStep.icon}</span>
            <div>
              <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
                Next step
              </span>
              <p className="text-sm font-medium text-foreground">
                {activeStep.description}
              </p>
            </div>
          </div>
          <ArrowRight className="h-5 w-5 text-primary group-hover:translate-x-1 transition-transform" aria-hidden="true" />
        </Link>
      )}
    </div>
  );
}
