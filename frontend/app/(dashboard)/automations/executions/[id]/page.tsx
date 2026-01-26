"use client";

import { useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
// ScrollArea component not available - using div with overflow
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ArrowLeft,
  Play,
  Pause,
  XCircle,
  CheckCircle2,
  Clock,
  AlertCircle,
  RefreshCw,
  Activity,
  Terminal,
  Info,
  AlertTriangle,
  Bug,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useExecution, useCancelExecution } from "@/hooks/useExecutions";
import { useExecutionStream } from "@/hooks/useExecutionStream";
import { useAuthStore } from "@/lib/stores/auth";
import type { ExecutionStatus, LogLevel, ExecutionStepStatus } from "@/lib/types/api";

// ============================================================================
// Configuration
// ============================================================================

const statusConfig: Record<ExecutionStatus, { label: string; icon: typeof Clock; className: string }> = {
  pending: {
    label: "Pending",
    icon: Clock,
    className: "bg-slate-500/10 text-slate-600 dark:text-slate-400",
  },
  running: {
    label: "Running",
    icon: Play,
    className: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  },
  paused: {
    label: "Paused",
    icon: Pause,
    className: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  },
  completed: {
    label: "Completed",
    icon: CheckCircle2,
    className: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  },
  failed: {
    label: "Failed",
    icon: AlertCircle,
    className: "bg-red-500/10 text-red-600 dark:text-red-400",
  },
  cancelled: {
    label: "Cancelled",
    icon: XCircle,
    className: "bg-gray-500/10 text-gray-600 dark:text-gray-400",
  },
};

const stepStatusConfig: Record<ExecutionStepStatus, { className: string; icon: typeof Clock }> = {
  pending: { className: "text-muted-foreground", icon: Clock },
  running: { className: "text-blue-500", icon: Play },
  completed: { className: "text-emerald-500", icon: CheckCircle2 },
  failed: { className: "text-red-500", icon: AlertCircle },
  skipped: { className: "text-gray-400", icon: XCircle },
};

const logLevelConfig: Record<LogLevel, { icon: typeof Info; className: string }> = {
  debug: { icon: Bug, className: "text-gray-400" },
  info: { icon: Info, className: "text-blue-400" },
  warning: { icon: AlertTriangle, className: "text-amber-400" },
  error: { icon: AlertCircle, className: "text-red-400" },
};

// ============================================================================
// Helpers
// ============================================================================

const formatDate = (dateStr: string | null): string => {
  if (!dateStr) return "-";
  try {
    return new Date(dateStr).toLocaleString();
  } catch {
    return dateStr;
  }
};

const formatDuration = (ms: number | null): string => {
  if (!ms) return "-";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
};

// ============================================================================
// Component
// ============================================================================

export default function ExecutionDetailPage() {
  const params = useParams();
  const executionId = params.id as string;
  const accessToken = useAuthStore((state) => state.accessToken);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Fetch execution details
  const {
    data: execution,
    isLoading,
    refetch,
  } = useExecution(executionId, {
    refetchInterval: 5000, // Poll every 5 seconds as fallback
  });

  // SSE stream for real-time updates
  const isActiveExecution = execution?.status === "running" || execution?.status === "pending";
  const executionStream = useExecutionStream({
    executionId: isActiveExecution ? executionId : null,
    accessToken,
    enabled: isActiveExecution,
    onComplete: () => {
      toast.success("Execution completed");
      refetch();
    },
    onError: (message) => {
      toast.error(`Execution failed: ${message}`);
      refetch();
    },
  });

  // Cancel mutation
  const cancelMutation = useCancelExecution();

  const handleCancel = async () => {
    try {
      await cancelMutation.mutateAsync({ executionId, reason: "Cancelled by user" });
      toast.success("Execution cancelled");
    } catch {
      toast.error("Failed to cancel execution");
    }
  };

  // Auto-scroll logs
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [executionStream.logs]);

  // Use stream data when available, otherwise fall back to API data
  const currentStatus = executionStream.status || execution?.status;
  const currentProgress = executionStream.progress || execution?.progress || 0;
  const currentLogs = executionStream.logs.length > 0 
    ? executionStream.logs 
    : execution?.recent_logs || [];
  const currentSteps = executionStream.steps.length > 0
    ? executionStream.steps
    : execution?.steps || [];

  if (isLoading) {
    return (
      <div className="space-y-8">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10" />
          <div className="space-y-2">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-4 w-40" />
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Skeleton className="h-[400px] lg:col-span-2" />
          <Skeleton className="h-[400px]" />
        </div>
      </div>
    );
  }

  if (!execution) {
    return (
      <div className="text-center py-16">
        <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
        <h2 className="text-xl font-semibold mb-2">Execution not found</h2>
        <p className="text-muted-foreground mb-6">
          The execution you are looking for does not exist or has been deleted.
        </p>
        <Button asChild>
          <Link href="/automations/executions">Back to Executions</Link>
        </Button>
      </div>
    );
  }

  const StatusIcon = statusConfig[currentStatus || "pending"].icon;
  const canCancel = currentStatus === "running" || currentStatus === "pending";

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/automations/executions">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight">
                Execution Details
              </h1>
              <Badge
                variant="outline"
                className={cn(
                  "gap-1",
                  statusConfig[currentStatus || "pending"].className
                )}
              >
                <StatusIcon className="h-3 w-3" />
                {statusConfig[currentStatus || "pending"].label}
              </Badge>
              {executionStream.isConnected && (
                <Badge variant="outline" className="gap-1 bg-emerald-500/10 text-emerald-600">
                  <Activity className="h-3 w-3 animate-pulse" />
                  Live
                </Badge>
              )}
            </div>
            <p className="text-muted-foreground mt-1">
              {execution.workflow_type.replace(/_/g, " ")} - Started{" "}
              {formatDate(execution.started_at)}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          {canCancel && (
            <Button
              variant="destructive"
              size="sm"
              onClick={handleCancel}
              disabled={cancelMutation.isPending}
            >
              <XCircle className="h-4 w-4 mr-2" />
              Cancel
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Progress</span>
          <span className="font-medium">{currentProgress}%</span>
        </div>
        <div className="h-3 bg-muted rounded-full overflow-hidden">
          <div
            className={cn(
              "h-full transition-all duration-500",
              currentStatus === "completed"
                ? "bg-emerald-500"
                : currentStatus === "failed"
                ? "bg-red-500"
                : "bg-blue-500"
            )}
            style={{ width: `${currentProgress}%` }}
          />
        </div>
      </div>

      {/* Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Steps */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg">Steps</CardTitle>
            <CardDescription>
              {execution.completed_steps} of {execution.total_steps} completed
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {currentSteps.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No steps recorded yet
                </p>
              ) : (
                currentSteps.map((step, idx) => {
                  const config = stepStatusConfig[step.status];
                  const StepIcon = config.icon;
                  return (
                    <div
                      key={step.id}
                      className="flex items-start gap-3 p-3 rounded-lg bg-muted/50"
                    >
                      <div className={cn("mt-0.5", config.className)}>
                        <StepIcon className="h-4 w-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm">{step.name}</p>
                        {step.description && (
                          <p className="text-xs text-muted-foreground truncate">
                            {step.description}
                          </p>
                        )}
                        {step.duration_ms && (
                          <p className="text-xs text-muted-foreground mt-1">
                            {formatDuration(step.duration_ms)}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </CardContent>
        </Card>

        {/* Logs */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Terminal className="h-5 w-5" />
              Logs
            </CardTitle>
            <CardDescription>
              Real-time execution logs
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[400px] overflow-auto rounded-lg bg-slate-950 p-4">
              <div className="font-mono text-xs space-y-1">
                {currentLogs.length === 0 ? (
                  <p className="text-slate-500">Waiting for logs...</p>
                ) : (
                  currentLogs.map((log, idx) => {
                    const config = logLevelConfig[log.level];
                    const LogIcon = config.icon;
                    return (
                      <div
                        key={log.id || idx}
                        className="flex items-start gap-2 text-slate-300"
                      >
                        <span className="text-slate-600 select-none">
                          {new Date(log.timestamp).toLocaleTimeString()}
                        </span>
                        <LogIcon className={cn("h-3 w-3 mt-0.5 shrink-0", config.className)} />
                        <span className={log.level === "error" ? "text-red-400" : ""}>
                          {log.message}
                        </span>
                      </div>
                    );
                  })
                )}
                <div ref={logsEndRef} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Metadata */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Details</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <dt className="text-muted-foreground">Execution ID</dt>
              <dd className="font-mono text-xs mt-1">{execution.id}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Workflow Type</dt>
              <dd className="mt-1 capitalize">
                {execution.workflow_type.replace(/_/g, " ")}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Started At</dt>
              <dd className="mt-1">{formatDate(execution.started_at)}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Duration</dt>
              <dd className="mt-1">{formatDuration(execution.duration_ms)}</dd>
            </div>
            {execution.campaign_id && (
              <div>
                <dt className="text-muted-foreground">Campaign</dt>
                <dd className="mt-1">
                  <Link
                    href={`/automations/${execution.campaign_id}`}
                    className="text-primary hover:underline"
                  >
                    View Campaign
                  </Link>
                </dd>
              </div>
            )}
            {execution.error_message && (
              <div className="col-span-2 md:col-span-4">
                <dt className="text-muted-foreground">Error</dt>
                <dd className="mt-1 text-red-500">{execution.error_message}</dd>
              </div>
            )}
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
