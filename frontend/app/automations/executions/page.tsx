"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DataTable,
  DataTableColumnHeader,
  type ColumnDef,
} from "@/components/ui/data-table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  MoreHorizontal,
  RefreshCw,
  Eye,
  Activity,
  ArrowLeft,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useExecutions, useCancelExecution } from "@/hooks/useExecutions";
import { StatusBadge, type StatusType } from "@/components/ui/status-badge";
import { PageSkeleton } from "@/components/ui/page-skeleton";
import type { ExecutionResponse, ExecutionStatus, WorkflowType } from "@/lib/types/api";

// ============================================================================
// Configuration
// ============================================================================

const workflowTypeLabels: Record<WorkflowType, string> = {
  job_discovery: "Job Discovery",
  job_analysis: "Job Analysis",
  resume_generation: "Resume Generation",
  application_processing: "Application Processing",
  company_research: "Company Research",
  contact_discovery: "Contact Discovery",
  outreach_generation: "Outreach Generation",
};

// ============================================================================
// Helpers
// ============================================================================

const formatDate = (dateStr: string | null): string => {
  if (!dateStr) return "-";
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
};

const formatDuration = (ms: number | null): string => {
  if (!ms) return "-";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
};

// ============================================================================
// Component
// ============================================================================

export default function ExecutionsPage() {
  const [statusFilter, setStatusFilter] = useState<ExecutionStatus | "all">("all");
  const [workflowTypeFilter, setWorkflowTypeFilter] = useState<WorkflowType | "all">("all");
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Fetch executions from API
  const { data: executionsData, isLoading, refetch } = useExecutions({
    status: statusFilter === "all" ? undefined : statusFilter,
    workflow_type: workflowTypeFilter === "all" ? undefined : workflowTypeFilter,
    page,
    page_size: pageSize,
    refetchInterval: 10000, // Refresh every 10 seconds for running executions
  });

  // Cancel mutation
  const cancelMutation = useCancelExecution();

  const handleCancel = async (executionId: string) => {
    try {
      await cancelMutation.mutateAsync({ executionId, reason: "Cancelled by user" });
      toast.success("Execution cancelled");
    } catch {
      toast.error("Failed to cancel execution");
    }
  };

  // Column definitions
  const columns: ColumnDef<ExecutionResponse, unknown>[] = [
    {
      accessorKey: "workflow_type",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Workflow" />
      ),
      cell: ({ row }) => {
        const workflowType = row.getValue("workflow_type") as WorkflowType;
        return (
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium">
              {workflowTypeLabels[workflowType] || workflowType}
            </span>
          </div>
        );
      },
    },
    {
      accessorKey: "status",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Status" />
      ),
      cell: ({ row }) => {
        const status = row.getValue("status") as ExecutionStatus;
        return (
          <StatusBadge status={status as StatusType} size="sm" />
        );
      },
    },
    {
      accessorKey: "progress",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Progress" />
      ),
      cell: ({ row }) => {
        const progress = row.getValue("progress") as number;
        const status = row.original.status;
        return (
          <div className="flex items-center gap-2 min-w-[100px]">
            <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full transition-all duration-300",
                  status === "completed" ? "bg-emerald-500" :
                  status === "failed" ? "bg-red-500" :
                  status === "running" ? "bg-blue-500" : "bg-muted-foreground"
                )}
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground w-10 text-right">
              {progress}%
            </span>
          </div>
        );
      },
    },
    {
      accessorKey: "started_at",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Started" />
      ),
      cell: ({ row }) => {
        const startedAt = row.getValue("started_at") as string | null;
        return (
          <span className="text-sm text-muted-foreground">
            {formatDate(startedAt)}
          </span>
        );
      },
    },
    {
      accessorKey: "duration_ms",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Duration" />
      ),
      cell: ({ row }) => {
        const durationMs = row.getValue("duration_ms") as number | null;
        return (
          <span className="text-sm text-muted-foreground font-mono">
            {formatDuration(durationMs)}
          </span>
        );
      },
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => {
        const execution = row.original;
        const canCancel = execution.status === "running" || execution.status === "pending";

        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="h-4 w-4" />
                <span className="sr-only">Open menu</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem asChild>
                <Link href={`/automations/executions/${execution.id}`}>
                  <Eye className="mr-2 h-4 w-4" />
                  View Details
                </Link>
              </DropdownMenuItem>
              {canCancel && (
                <DropdownMenuItem
                  onClick={() => handleCancel(execution.id)}
                  disabled={cancelMutation.isPending}
                  className="text-destructive focus:text-destructive"
                >
                  <XCircle className="mr-2 h-4 w-4" />
                  Cancel
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
    },
  ];

  // Loading skeleton
  if (isLoading) {
    return (
      <PageSkeleton
        variant="table"
        count={5}
        showHeader
        headerWidth="w-40"
      />
    );
  }

  const executions = executionsData?.items || [];
  const totalPages = executionsData?.pages || 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/automations">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Executions</h1>
            <p className="text-muted-foreground mt-1">
              Monitor and manage workflow executions
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          className="gap-2"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <Select
          value={statusFilter}
          onValueChange={(value) => setStatusFilter(value as ExecutionStatus | "all")}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="running">Running</SelectItem>
            <SelectItem value="paused">Paused</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
            <SelectItem value="cancelled">Cancelled</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={workflowTypeFilter}
          onValueChange={(value) => setWorkflowTypeFilter(value as WorkflowType | "all")}
        >
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Filter by workflow" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Workflows</SelectItem>
            <SelectItem value="job_discovery">Job Discovery</SelectItem>
            <SelectItem value="job_analysis">Job Analysis</SelectItem>
            <SelectItem value="resume_generation">Resume Generation</SelectItem>
            <SelectItem value="application_processing">Application Processing</SelectItem>
            <SelectItem value="company_research">Company Research</SelectItem>
            <SelectItem value="contact_discovery">Contact Discovery</SelectItem>
            <SelectItem value="outreach_generation">Outreach Generation</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Data Table */}
      {executions.length === 0 ? (
        <div className="simple-card text-center py-16">
          <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-6">
            <Activity className="h-8 w-8 text-primary" />
          </div>
          <h2 className="text-xl font-semibold mb-2">No executions yet</h2>
          <p className="text-muted-foreground max-w-md mx-auto mb-8">
            Executions will appear here when you run workflows or when scheduled
            automations are triggered.
          </p>
          <Button asChild>
            <Link href="/automations">View Automations</Link>
          </Button>
        </div>
      ) : (
        <div className="simple-card p-0 overflow-hidden">
          <DataTable
            columns={columns}
            data={executions}
            enableSearch={false}
            enablePagination
            defaultPageSize={pageSize}
            pageSizeOptions={[10, 20, 50]}
            enableSorting
          />
        </div>
      )}

      {/* Pagination info */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
