"use client";

import { Upload, FileText, Brain, Sparkles, Check, Loader2, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ProcessingLog {
  step: string;
  status: "pending" | "processing" | "completed" | "failed";
  message: string;
}

interface ProcessingPipelineProps {
  status: "pending" | "processing" | "completed" | "failed";
  logs?: ProcessingLog[];
  compact?: boolean;
}

interface Stage {
  id: string;
  number: string;
  label: string;
  icon: React.ReactNode;
  keywords: string[];
}

const stages: Stage[] = [
  {
    id: "upload",
    number: "01",
    label: "Upload",
    icon: <Upload className="h-4 w-4" />,
    keywords: ["upload", "receive", "queue"],
  },
  {
    id: "parse",
    number: "02",
    label: "Parse",
    icon: <FileText className="h-4 w-4" />,
    keywords: ["extract", "parse", "read", "text"],
  },
  {
    id: "classify",
    number: "03",
    label: "Classify",
    icon: <Brain className="h-4 w-4" />,
    keywords: ["classify", "categorize", "analyze", "llm"],
  },
  {
    id: "extract",
    number: "04",
    label: "Extract",
    icon: <Sparkles className="h-4 w-4" />,
    keywords: ["extract", "entity", "structure", "data"],
  },
];

function getStageStatus(
  stageIndex: number,
  logs: ProcessingLog[],
  overallStatus: string
): "pending" | "processing" | "completed" | "failed" {
  const stage = stages[stageIndex];

  // Find logs matching this stage
  const matchingLogs = logs.filter((log) =>
    stage.keywords.some((kw) => log.step.toLowerCase().includes(kw) || log.message.toLowerCase().includes(kw))
  );

  if (matchingLogs.some((l) => l.status === "failed")) return "failed";
  if (matchingLogs.some((l) => l.status === "completed")) return "completed";
  if (matchingLogs.some((l) => l.status === "processing")) return "processing";

  // Infer status based on overall status and stage position
  if (overallStatus === "completed") return "completed";
  if (overallStatus === "failed") {
    const lastCompletedStageIndex = stages.findIndex((s, i) => {
      const stageLogs = logs.filter((log) =>
        s.keywords.some((kw) => log.step.toLowerCase().includes(kw) || log.message.toLowerCase().includes(kw))
      );
      return !stageLogs.some((l) => l.status === "completed");
    });
    if (stageIndex < lastCompletedStageIndex || lastCompletedStageIndex === -1) return "completed";
    if (stageIndex === lastCompletedStageIndex) return "failed";
    return "pending";
  }

  // If processing, estimate which stage we're on based on log count
  if (overallStatus === "processing") {
    const completedCount = logs.filter((l) => l.status === "completed").length;
    const estimatedStage = Math.min(Math.floor(completedCount / 2), stages.length - 1);
    if (stageIndex < estimatedStage) return "completed";
    if (stageIndex === estimatedStage) return "processing";
    return "pending";
  }

  // Upload complete for pending items
  if (stageIndex === 0 && overallStatus === "pending") return "completed";

  return "pending";
}

export function ProcessingPipeline({ status, logs = [], compact = false }: ProcessingPipelineProps) {
  // Compact mode - Editorial inline style
  if (compact) {
    return (
      <div className="flex items-center gap-2">
        {stages.map((stage, index) => {
          const stageStatus = getStageStatus(index, logs, status);
          return (
            <div key={stage.id} className="flex items-center gap-2">
              <div
                className={cn(
                  "flex items-center justify-center w-7 h-7 border transition-all",
                  stageStatus === "completed" && "border-success bg-success/10 text-success",
                  stageStatus === "processing" && "border-primary bg-primary/10 text-primary",
                  stageStatus === "failed" && "border-destructive bg-destructive/10 text-destructive",
                  stageStatus === "pending" && "border-border bg-muted/30 text-muted-foreground"
                )}
              >
                {stageStatus === "processing" ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : stageStatus === "completed" ? (
                  <Check className="h-3 w-3" />
                ) : stageStatus === "failed" ? (
                  <X className="h-3 w-3" />
                ) : (
                  <span className="font-mono text-2xs">{stage.number}</span>
                )}
              </div>
              {index < stages.length - 1 && (
                <div
                  className={cn(
                    "w-4 h-0.5 transition-colors",
                    stageStatus === "completed" ? "bg-success" : "bg-border"
                  )}
                  aria-hidden="true"
                />
              )}
            </div>
          );
        })}
      </div>
    );
  }

  // Full mode - Editorial vertical timeline
  const completedCount = stages.filter((_, i) => getStageStatus(i, logs, status) === "completed").length;

  return (
    <div className="border border-border bg-card p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
            Processing
          </span>
          <h3 className="font-display text-lg font-medium mt-1">
            Document Pipeline
          </h3>
        </div>
        <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
          {completedCount} / {stages.length}
        </span>
      </div>

      {/* Vertical Timeline */}
      <div className="relative" role="list" aria-label="Processing stages">
        {/* Connecting Line */}
        <div
          className="absolute left-[15px] top-6 bottom-6 w-[2px] bg-border"
          aria-hidden="true"
        />
        {/* Progress Line */}
        <div
          className="absolute left-[15px] top-6 w-[2px] bg-primary transition-all duration-500"
          style={{
            height: `calc(${(completedCount / stages.length) * 100}% - 24px)`,
          }}
          aria-hidden="true"
        />

        {/* Stages */}
        <div className="space-y-6">
          {stages.map((stage, index) => {
            const stageStatus = getStageStatus(index, logs, status);

            return (
              <div
                key={stage.id}
                className="relative flex items-start gap-4"
                role="listitem"
              >
                {/* Step Number / Status Icon */}
                <div
                  className={cn(
                    "relative z-10 flex items-center justify-center w-8 h-8 border-2 transition-all",
                    stageStatus === "completed" && "bg-success border-success text-background",
                    stageStatus === "processing" && "bg-background border-primary text-primary",
                    stageStatus === "failed" && "bg-destructive border-destructive text-background",
                    stageStatus === "pending" && "bg-background border-border text-muted-foreground"
                  )}
                >
                  {stageStatus === "processing" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : stageStatus === "completed" ? (
                    <Check className="h-4 w-4" aria-label="Completed" />
                  ) : stageStatus === "failed" ? (
                    <X className="h-4 w-4" aria-label="Failed" />
                  ) : (
                    <span className="font-mono text-xs">{stage.number}</span>
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 pt-1">
                  <div className="flex items-center gap-3">
                    <span
                      className={cn(
                        "font-mono text-xs uppercase tracking-widest transition-colors",
                        stageStatus === "completed" || stageStatus === "processing"
                          ? "text-foreground"
                          : "text-muted-foreground"
                      )}
                    >
                      {stage.label}
                    </span>
                    {stageStatus === "processing" && (
                      <span className="px-2 py-0.5 bg-primary/10 text-primary font-mono text-2xs uppercase tracking-widest">
                        Active
                      </span>
                    )}
                    {stageStatus === "completed" && (
                      <span className="px-2 py-0.5 bg-success/10 text-success font-mono text-2xs uppercase tracking-widest">
                        Done
                      </span>
                    )}
                    {stageStatus === "failed" && (
                      <span className="px-2 py-0.5 bg-destructive/10 text-destructive font-mono text-2xs uppercase tracking-widest">
                        Failed
                      </span>
                    )}
                  </div>
                </div>

                {/* Stage Icon */}
                <span
                  className={cn(
                    "text-muted-foreground transition-colors",
                    stageStatus === "processing" && "text-primary",
                    stageStatus === "completed" && "text-success"
                  )}
                >
                  {stage.icon}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Current Action */}
      {status === "processing" && (
        <div className="mt-6 pt-6 border-t border-border">
          <p className="font-body text-sm text-primary italic">
            {logs.length > 0
              ? logs[logs.length - 1].message
              : "Processing your document..."}
          </p>
        </div>
      )}

      {status === "failed" && (
        <div className="mt-6 p-4 border-2 border-destructive bg-destructive/5">
          <p className="font-body text-sm text-destructive">
            {logs.find((l) => l.status === "failed")?.message || "Processing failed"}
          </p>
        </div>
      )}

      {status === "completed" && (
        <div className="mt-6 pt-6 border-t border-border">
          <p className="font-body text-sm text-success italic">
            Document processed successfully
          </p>
        </div>
      )}
    </div>
  );
}
