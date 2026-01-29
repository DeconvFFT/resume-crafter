"use client";

import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

export interface WorkflowCanvasSkeletonProps {
  className?: string;
}

/**
 * Loading skeleton for the WorkflowCanvas component.
 * Displays a placeholder that matches the workflow canvas layout
 * while ReactFlow (~150KB) is being dynamically loaded.
 */
export function WorkflowCanvasSkeleton({ className }: WorkflowCanvasSkeletonProps) {
  return (
    <div
      className={cn(
        "w-full h-full bg-background rounded-lg border border-border overflow-hidden relative",
        className
      )}
    >
      {/* Background dots pattern simulation */}
      <div
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: `radial-gradient(circle, hsl(var(--muted-foreground)) 1px, transparent 1px)`,
          backgroundSize: '16px 16px',
        }}
      />

      {/* Skeleton nodes to simulate workflow layout */}
      <div className="relative z-10 p-8">
        {/* Trigger node skeleton */}
        <div className="absolute left-[100px] top-[150px]">
          <SkeletonNode variant="trigger" />
        </div>

        {/* Connection line skeleton */}
        <Skeleton className="absolute left-[280px] top-[175px] w-[100px] h-[2px]" />

        {/* Action node skeleton */}
        <div className="absolute left-[400px] top-[120px]">
          <SkeletonNode variant="action" />
        </div>

        {/* Connection line skeleton */}
        <Skeleton className="absolute left-[580px] top-[145px] w-[100px] h-[2px]" />

        {/* Output node skeleton */}
        <div className="absolute left-[700px] top-[100px]">
          <SkeletonNode variant="output" />
        </div>
      </div>

      {/* Controls skeleton (bottom left) */}
      <div className="absolute bottom-4 left-4 flex flex-col gap-1">
        <Skeleton className="w-8 h-8 rounded-md" />
        <Skeleton className="w-8 h-8 rounded-md" />
        <Skeleton className="w-8 h-8 rounded-md" />
      </div>

      {/* MiniMap skeleton (bottom right) */}
      <div className="absolute bottom-4 right-4">
        <Skeleton className="w-[150px] h-[100px] rounded-lg" />
      </div>

      {/* Loading indicator */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 bg-background/80 px-6 py-4 rounded-lg border border-border shadow-sm">
          <div className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-muted-foreground">Loading workflow editor...</span>
        </div>
      </div>
    </div>
  );
}

interface SkeletonNodeProps {
  variant: "trigger" | "action" | "condition" | "output";
}

function SkeletonNode({ variant }: SkeletonNodeProps) {
  const variantColors: Record<string, string> = {
    trigger: "border-l-amber-500",
    action: "border-l-teal-500",
    condition: "border-l-cyan-500",
    output: "border-l-emerald-500",
  };

  return (
    <div
      className={cn(
        "w-[160px] bg-card border border-border rounded-lg shadow-sm overflow-hidden",
        "border-l-4",
        variantColors[variant]
      )}
    >
      <div className="p-3 space-y-2">
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-5 rounded" />
          <Skeleton className="h-4 w-20" />
        </div>
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-2/3" />
      </div>
    </div>
  );
}

export default WorkflowCanvasSkeleton;
