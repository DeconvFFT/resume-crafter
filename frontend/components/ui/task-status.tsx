"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { api } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth";
import { CheckCircle, Clock, AlertCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

type TaskStatus = "pending" | "processing" | "completed" | "failed";

interface TaskStatusProps {
  taskId: string;
  onComplete?: () => void;
  onFailed?: (error: string) => void;
  showLabel?: boolean;
  className?: string;
}

const statusConfig: Record<TaskStatus, { icon: typeof Clock; color: string; bgColor: string; label: string }> = {
  pending: { icon: Clock, color: "text-warning", bgColor: "bg-warning/10", label: "Pending" },
  processing: { icon: Loader2, color: "text-primary", bgColor: "bg-primary/10", label: "Processing" },
  completed: { icon: CheckCircle, color: "text-success", bgColor: "bg-success/10", label: "Completed" },
  failed: { icon: AlertCircle, color: "text-destructive", bgColor: "bg-destructive/10", label: "Failed" },
};

export function TaskStatus({
  taskId,
  onComplete,
  onFailed,
  showLabel = true,
  className,
}: TaskStatusProps) {
  const accessToken = useAuthStore((state) => state.accessToken);

  const { data: task } = useQuery({
    queryKey: ["task", taskId],
    queryFn: () => api.tasks.getStatus(accessToken!, taskId),
    enabled: !!accessToken && !!taskId,
    refetchInterval: (query) => {
      const status = query.state.data?.status as TaskStatus | undefined;
      // Stop polling when task is completed or failed
      if (status === "completed" || status === "failed") {
        return false;
      }
      // Poll every 2 seconds while processing
      return 2000;
    },
  });

  useEffect(() => {
    if (task?.status === "completed" && onComplete) {
      onComplete();
    }
    if (task?.status === "failed" && onFailed) {
      onFailed(task.error_message || "Task failed");
    }
  }, [task?.status, task?.error_message, onComplete, onFailed]);

  if (!task) {
    return null;
  }

  const status = task.status as TaskStatus;
  const config = statusConfig[status] || statusConfig.pending;
  const Icon = config.icon;

  return (
    <div className={cn(
      "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
      config.bgColor,
      className
    )}>
      <Icon
        className={cn(
          "h-3.5 w-3.5",
          config.color,
          status === "processing" && "animate-spin"
        )}
      />
      {showLabel && (
        <span className={cn("text-sm font-medium", config.color)}>{config.label}</span>
      )}
    </div>
  );
}

interface TaskProgressProps {
  taskId: string;
  title?: string;
  onComplete?: () => void;
  onFailed?: (error: string) => void;
}

export function TaskProgress({
  taskId,
  title,
  onComplete,
  onFailed,
}: TaskProgressProps) {
  const accessToken = useAuthStore((state) => state.accessToken);

  const { data: task } = useQuery({
    queryKey: ["task", taskId],
    queryFn: () => api.tasks.getStatus(accessToken!, taskId),
    enabled: !!accessToken && !!taskId,
    refetchInterval: (query) => {
      const status = query.state.data?.status as TaskStatus | undefined;
      if (status === "completed" || status === "failed") {
        return false;
      }
      return 2000;
    },
  });

  useEffect(() => {
    if (task?.status === "completed" && onComplete) {
      onComplete();
    }
    if (task?.status === "failed" && onFailed) {
      onFailed(task.error_message || "Task failed");
    }
  }, [task?.status, task?.error_message, onComplete, onFailed]);

  if (!task) {
    return null;
  }

  const status = task.status as TaskStatus;
  const config = statusConfig[status] || statusConfig.pending;
  const Icon = config.icon;
  const progress = task.progress || 0;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon
            className={cn(
              "h-4 w-4",
              config.color,
              status === "processing" && "animate-spin"
            )}
          />
          <span className="text-sm font-medium">{title || config.label}</span>
        </div>
        {status === "processing" && (
          <span className="text-xs font-medium text-muted-foreground">
            {Math.round(progress * 100)}%
          </span>
        )}
      </div>
      {status === "processing" && (
        <div className="h-2 w-full rounded-full bg-primary/20 overflow-hidden">
          <div
            className="h-full rounded-full bg-primary transition-all duration-300"
            style={{ width: `${progress * 100}%` }}
          />
        </div>
      )}
      {status === "failed" && task.error_message && (
        <p className="text-sm text-destructive">{task.error_message}</p>
      )}
    </div>
  );
}
