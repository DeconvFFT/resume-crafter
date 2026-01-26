"use client";

import * as React from "react";
import { useState, useMemo } from "react";
import {
  Play,
  Pause,
  Square,
  ChevronUp,
  ChevronDown,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2,
  Circle,
  ChevronRight,
  Copy,
  ExternalLink,
  RefreshCw,
  XCircle,
  LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

// Execution status types
export type ExecutionStatus = "idle" | "running" | "paused" | "completed" | "failed" | "cancelled";
export type NodeExecutionStatus = "pending" | "running" | "completed" | "failed" | "skipped";

// Node execution data
export interface NodeExecution {
  nodeId: string;
  nodeName: string;
  nodeType: string;
  status: NodeExecutionStatus;
  startedAt?: Date;
  completedAt?: Date;
  duration?: number; // milliseconds
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
  error?: {
    message: string;
    stack?: string;
    code?: string;
  };
  retryCount?: number;
  logs?: ExecutionLog[];
}

// Execution log entry
export interface ExecutionLog {
  timestamp: Date;
  level: "info" | "warn" | "error" | "debug";
  message: string;
  data?: Record<string, unknown>;
}

// Overall execution data
export interface WorkflowExecution {
  id: string;
  workflowId: string;
  workflowName: string;
  status: ExecutionStatus;
  startedAt: Date;
  completedAt?: Date;
  duration?: number;
  progress: number; // 0-100
  nodes: NodeExecution[];
  currentNodeIndex: number;
  totalNodes: number;
}

// Status configuration
interface StatusConfig {
  icon: LucideIcon;
  color: string;
  bgColor: string;
  label: string;
  animate?: boolean;
}

const nodeStatusConfig: Record<NodeExecutionStatus, StatusConfig> = {
  pending: {
    icon: Circle,
    color: "text-muted-foreground",
    bgColor: "bg-muted",
    label: "Pending",
  },
  running: {
    icon: Loader2,
    color: "text-primary",
    bgColor: "bg-primary/10",
    label: "Running",
    animate: true,
  },
  completed: {
    icon: CheckCircle,
    color: "text-success",
    bgColor: "bg-success/10",
    label: "Completed",
  },
  failed: {
    icon: XCircle,
    color: "text-destructive",
    bgColor: "bg-destructive/10",
    label: "Failed",
  },
  skipped: {
    icon: Circle,
    color: "text-muted-foreground",
    bgColor: "bg-muted",
    label: "Skipped",
  },
};

const executionStatusConfig: Record<ExecutionStatus, StatusConfig> = {
  idle: {
    icon: Circle,
    color: "text-muted-foreground",
    bgColor: "bg-muted",
    label: "Idle",
  },
  running: {
    icon: Loader2,
    color: "text-primary",
    bgColor: "bg-primary/10",
    label: "Running",
    animate: true,
  },
  paused: {
    icon: Pause,
    color: "text-warning",
    bgColor: "bg-warning/10",
    label: "Paused",
  },
  completed: {
    icon: CheckCircle,
    color: "text-success",
    bgColor: "bg-success/10",
    label: "Completed",
  },
  failed: {
    icon: AlertCircle,
    color: "text-destructive",
    bgColor: "bg-destructive/10",
    label: "Failed",
  },
  cancelled: {
    icon: XCircle,
    color: "text-muted-foreground",
    bgColor: "bg-muted",
    label: "Cancelled",
  },
};

// Format duration
function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${ms}ms`;
  }
  if (ms < 60000) {
    return `${(ms / 1000).toFixed(1)}s`;
  }
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return `${minutes}m ${seconds}s`;
}

// Format timestamp
function formatTimestamp(date: Date): string {
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

// Data preview component
interface DataPreviewProps {
  data: Record<string, unknown>;
  title: string;
  maxHeight?: string;
}

function DataPreview({ data, title, maxHeight = "150px" }: DataPreviewProps) {
  const [copied, setCopied] = useState(false);

  const jsonString = useMemo(() => JSON.stringify(data, null, 2), [data]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-md border border-border overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 bg-muted/50 border-b border-border">
        <span className="text-2xs font-medium text-muted-foreground uppercase tracking-wider">
          {title}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 px-2 text-2xs"
          onClick={handleCopy}
        >
          {copied ? (
            <>
              <CheckCircle className="h-3 w-3 mr-1" />
              Copied
            </>
          ) : (
            <>
              <Copy className="h-3 w-3 mr-1" />
              Copy
            </>
          )}
        </Button>
      </div>
      <pre
        className="p-3 text-2xs font-mono overflow-auto bg-muted/30"
        style={{ maxHeight }}
      >
        {jsonString}
      </pre>
    </div>
  );
}

// Error display component
interface ErrorDisplayProps {
  error: NodeExecution["error"];
}

function ErrorDisplay({ error }: ErrorDisplayProps) {
  const [showStack, setShowStack] = useState(false);

  if (!error) return null;

  return (
    <div className="rounded-md border border-destructive/50 bg-destructive/5 overflow-hidden">
      <div className="flex items-start gap-2 p-3">
        <AlertCircle className="h-4 w-4 text-destructive mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-destructive">{error.message}</p>
          {error.code && (
            <p className="text-2xs text-muted-foreground mt-0.5">
              Error code: {error.code}
            </p>
          )}
        </div>
      </div>
      {error.stack && (
        <Collapsible open={showStack} onOpenChange={setShowStack}>
          <CollapsibleTrigger className="flex items-center gap-1 w-full px-3 py-2 text-2xs text-muted-foreground hover:text-foreground border-t border-destructive/30">
            {showStack ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
            Stack trace
          </CollapsibleTrigger>
          <CollapsibleContent>
            <pre className="p-3 text-2xs font-mono text-muted-foreground overflow-auto max-h-40 bg-muted/30 border-t border-destructive/30">
              {error.stack}
            </pre>
          </CollapsibleContent>
        </Collapsible>
      )}
    </div>
  );
}

// Node execution item
interface NodeExecutionItemProps {
  node: NodeExecution;
  isExpanded: boolean;
  onToggle: () => void;
}

function NodeExecutionItem({ node, isExpanded, onToggle }: NodeExecutionItemProps) {
  const config = nodeStatusConfig[node.status];
  const Icon = config.icon;

  return (
    <Collapsible open={isExpanded} onOpenChange={onToggle}>
      <CollapsibleTrigger className="flex items-center gap-3 w-full p-3 hover:bg-accent/50 rounded-md transition-colors group">
        <div
          className={cn(
            "flex items-center justify-center w-6 h-6 rounded-full",
            config.bgColor
          )}
        >
          <Icon
            className={cn(
              "h-3.5 w-3.5",
              config.color,
              config.animate && "animate-spin"
            )}
          />
        </div>
        <div className="flex-1 min-w-0 text-left">
          <p className="text-sm font-medium truncate">{node.nodeName}</p>
          <p className="text-2xs text-muted-foreground">{node.nodeType}</p>
        </div>
        <div className="flex items-center gap-2">
          {node.duration !== undefined && (
            <span className="text-2xs text-muted-foreground font-mono">
              {formatDuration(node.duration)}
            </span>
          )}
          <Badge variant={node.status === "failed" ? "destructive" : "outline"} className="text-2xs">
            {config.label}
          </Badge>
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="pl-12 pr-3 pb-3 space-y-3">
          {/* Timing info */}
          <div className="flex items-center gap-4 text-2xs text-muted-foreground">
            {node.startedAt && (
              <span>Started: {formatTimestamp(node.startedAt)}</span>
            )}
            {node.completedAt && (
              <span>Completed: {formatTimestamp(node.completedAt)}</span>
            )}
            {node.retryCount !== undefined && node.retryCount > 0 && (
              <span className="flex items-center gap-1">
                <RefreshCw className="h-3 w-3" />
                {node.retryCount} retries
              </span>
            )}
          </div>

          {/* Error display */}
          {node.error && <ErrorDisplay error={node.error} />}

          {/* Input/Output data */}
          {node.input && Object.keys(node.input).length > 0 && (
            <DataPreview data={node.input} title="Input" />
          )}
          {node.output && Object.keys(node.output).length > 0 && (
            <DataPreview data={node.output} title="Output" />
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

// ExecutionPanel props
export interface ExecutionPanelProps {
  execution: WorkflowExecution | null;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onPlay: () => void;
  onPause: () => void;
  onStop: () => void;
  onRetry?: () => void;
  className?: string;
}

export function ExecutionPanel({
  execution,
  isExpanded,
  onToggleExpand,
  onPlay,
  onPause,
  onStop,
  onRetry,
  className,
}: ExecutionPanelProps) {
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());

  const toggleNodeExpanded = (nodeId: string) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  const statusConfig = execution
    ? executionStatusConfig[execution.status]
    : executionStatusConfig.idle;
  const StatusIcon = statusConfig.icon;

  const canPlay = !execution || execution.status === "idle" || execution.status === "paused";
  const canPause = execution?.status === "running";
  const canStop = execution?.status === "running" || execution?.status === "paused";
  const canRetry = execution?.status === "failed";

  // Calculate stats
  const stats = useMemo(() => {
    if (!execution) {
      return { completed: 0, failed: 0, pending: 0 };
    }
    return {
      completed: execution.nodes.filter((n) => n.status === "completed").length,
      failed: execution.nodes.filter((n) => n.status === "failed").length,
      pending: execution.nodes.filter((n) => n.status === "pending").length,
    };
  }, [execution]);

  return (
    <div
      className={cn(
        "flex flex-col border-t border-border bg-card",
        isExpanded ? "h-80" : "h-14",
        "transition-all duration-300",
        className
      )}
    >
      {/* Header / Toolbar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border min-h-14">
        <div className="flex items-center gap-4">
          {/* Expand/Collapse */}
          <Button
            variant="ghost"
            size="sm"
            onClick={onToggleExpand}
            className="gap-1.5"
          >
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronUp className="h-4 w-4" />
            )}
            <span className="font-mono text-xs uppercase tracking-widest">
              Execution
            </span>
          </Button>

          {/* Status badge */}
          {execution && (
            <div className="flex items-center gap-2">
              <Badge
                variant={execution.status === "failed" ? "destructive" : "outline"}
                className="gap-1.5"
              >
                <StatusIcon
                  className={cn(
                    "h-3 w-3",
                    statusConfig.color,
                    statusConfig.animate && "animate-spin"
                  )}
                />
                {statusConfig.label}
              </Badge>
              {execution.status === "running" && (
                <span className="text-2xs text-muted-foreground">
                  {execution.currentNodeIndex + 1} / {execution.totalNodes}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          {/* Stats (visible when collapsed) */}
          {!isExpanded && execution && (
            <div className="flex items-center gap-3 mr-4 text-2xs">
              <span className="flex items-center gap-1 text-success">
                <CheckCircle className="h-3 w-3" />
                {stats.completed}
              </span>
              {stats.failed > 0 && (
                <span className="flex items-center gap-1 text-destructive">
                  <XCircle className="h-3 w-3" />
                  {stats.failed}
                </span>
              )}
              <span className="flex items-center gap-1 text-muted-foreground">
                <Clock className="h-3 w-3" />
                {stats.pending}
              </span>
            </div>
          )}

          {/* Play/Pause/Stop */}
          <div className="flex items-center gap-1">
            {canRetry && onRetry && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRetry}
                className="gap-1.5"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Retry
              </Button>
            )}
            <Button
              variant={canPlay ? "default" : "outline"}
              size="icon"
              onClick={onPlay}
              disabled={!canPlay}
              aria-label="Play"
            >
              <Play className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={onPause}
              disabled={!canPause}
              aria-label="Pause"
            >
              <Pause className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={onStop}
              disabled={!canStop}
              aria-label="Stop"
            >
              <Square className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="flex-1 overflow-hidden flex">
          {/* Timeline / Node list */}
          <div className="flex-1 overflow-y-auto p-2">
            {!execution ? (
              <div className="flex flex-col items-center justify-center h-full text-center py-8">
                <Circle className="h-12 w-12 text-muted-foreground/30 mb-3" />
                <p className="text-sm font-medium text-muted-foreground">
                  No execution running
                </p>
                <p className="text-2xs text-muted-foreground mt-1">
                  Click Play to start the workflow
                </p>
              </div>
            ) : execution.nodes.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center py-8">
                <Loader2 className="h-8 w-8 text-primary animate-spin mb-3" />
                <p className="text-sm font-medium">Initializing execution...</p>
              </div>
            ) : (
              <div className="space-y-1">
                {execution.nodes.map((node) => (
                  <NodeExecutionItem
                    key={node.nodeId}
                    node={node}
                    isExpanded={expandedNodes.has(node.nodeId)}
                    onToggle={() => toggleNodeExpanded(node.nodeId)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Progress sidebar */}
          {execution && (
            <div className="w-48 border-l border-border p-4 space-y-4">
              {/* Progress */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-2xs">
                  <span className="text-muted-foreground">Progress</span>
                  <span className="font-medium">{Math.round(execution.progress)}%</span>
                </div>
                <Progress value={execution.progress} className="h-2" />
              </div>

              {/* Duration */}
              {execution.duration !== undefined && (
                <div className="space-y-1">
                  <span className="text-2xs text-muted-foreground">Duration</span>
                  <p className="text-lg font-mono font-medium">
                    {formatDuration(execution.duration)}
                  </p>
                </div>
              )}

              {/* Stats */}
              <div className="space-y-2 pt-2 border-t border-border">
                <span className="text-2xs text-muted-foreground">Statistics</span>
                <div className="grid grid-cols-2 gap-2">
                  <div className="text-center p-2 rounded-md bg-success/10">
                    <p className="text-lg font-semibold text-success">{stats.completed}</p>
                    <p className="text-2xs text-muted-foreground">Completed</p>
                  </div>
                  <div className="text-center p-2 rounded-md bg-destructive/10">
                    <p className="text-lg font-semibold text-destructive">{stats.failed}</p>
                    <p className="text-2xs text-muted-foreground">Failed</p>
                  </div>
                </div>
              </div>

              {/* Workflow info */}
              <div className="space-y-1 pt-2 border-t border-border">
                <span className="text-2xs text-muted-foreground">Workflow</span>
                <p className="text-sm font-medium truncate" title={execution.workflowName}>
                  {execution.workflowName}
                </p>
                <p className="text-2xs text-muted-foreground font-mono">
                  {execution.id.slice(0, 8)}...
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ExecutionPanel;
