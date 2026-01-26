"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DataTable,
  DataTableColumnHeader,
  type ColumnDef,
} from "@/components/ui/data-table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Play,
  Pause,
  Trash2,
  Copy,
  Edit,
  Plus,
  Zap,
  MoreHorizontal,
  Clock,
  Webhook,
  Calendar,
  FileText,
  Mail,
} from "lucide-react";
import { cn } from "@/lib/utils";

// Types
interface Automation {
  id: string;
  name: string;
  description: string;
  status: "active" | "paused" | "draft";
  triggerType: "manual" | "webhook" | "schedule" | "event";
  lastRun: string | null;
  runCount: number;
  createdAt: string;
  updatedAt: string;
}

// Status badge configuration
const statusConfig = {
  active: {
    label: "Active",
    className: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
  },
  paused: {
    label: "Paused",
    className: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
  },
  draft: {
    label: "Draft",
    className: "bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20",
  },
};

// Trigger type configuration
const triggerConfig = {
  manual: { label: "Manual", icon: Play },
  webhook: { label: "Webhook", icon: Webhook },
  schedule: { label: "Schedule", icon: Calendar },
  event: { label: "Event", icon: Zap },
};

// Mock data for automations
const mockAutomations: Automation[] = [
  {
    id: "1",
    name: "Resume Tailor for Tech Jobs",
    description: "Automatically tailors resume when a new tech job is added",
    status: "active",
    triggerType: "event",
    lastRun: "2024-01-20T14:30:00Z",
    runCount: 47,
    createdAt: "2024-01-01T10:00:00Z",
    updatedAt: "2024-01-20T14:30:00Z",
  },
  {
    id: "2",
    name: "Weekly Job Digest",
    description: "Sends a weekly email digest of new job matches",
    status: "active",
    triggerType: "schedule",
    lastRun: "2024-01-19T09:00:00Z",
    runCount: 12,
    createdAt: "2024-01-05T08:00:00Z",
    updatedAt: "2024-01-19T09:00:00Z",
  },
  {
    id: "3",
    name: "LinkedIn Job Sync",
    description: "Syncs jobs from LinkedIn saved positions via webhook",
    status: "paused",
    triggerType: "webhook",
    lastRun: "2024-01-15T16:45:00Z",
    runCount: 156,
    createdAt: "2023-12-15T12:00:00Z",
    updatedAt: "2024-01-15T16:45:00Z",
  },
  {
    id: "4",
    name: "Cover Letter Generator",
    description: "Generates personalized cover letters for matched jobs",
    status: "draft",
    triggerType: "manual",
    lastRun: null,
    runCount: 0,
    createdAt: "2024-01-18T11:00:00Z",
    updatedAt: "2024-01-18T11:00:00Z",
  },
  {
    id: "5",
    name: "Skills Gap Analysis",
    description: "Analyzes skill gaps when new jobs are analyzed",
    status: "active",
    triggerType: "event",
    lastRun: "2024-01-20T10:15:00Z",
    runCount: 28,
    createdAt: "2024-01-10T14:00:00Z",
    updatedAt: "2024-01-20T10:15:00Z",
  },
  {
    id: "6",
    name: "Application Tracker Update",
    description: "Updates application status from email notifications",
    status: "paused",
    triggerType: "webhook",
    lastRun: "2024-01-12T08:30:00Z",
    runCount: 89,
    createdAt: "2023-11-20T09:00:00Z",
    updatedAt: "2024-01-12T08:30:00Z",
  },
  {
    id: "7",
    name: "Portfolio PDF Export",
    description: "Manually triggered export of portfolio to PDF",
    status: "active",
    triggerType: "manual",
    lastRun: "2024-01-17T15:20:00Z",
    runCount: 8,
    createdAt: "2024-01-08T10:30:00Z",
    updatedAt: "2024-01-17T15:20:00Z",
  },
];

// Simulate API delay
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// Mock API functions (ready for real API integration)
const automationsApi = {
  list: async (): Promise<Automation[]> => {
    await delay(800);
    return mockAutomations;
  },
  delete: async (id: string): Promise<void> => {
    await delay(500);
  },
  duplicate: async (id: string): Promise<Automation> => {
    await delay(500);
    const original = mockAutomations.find((a) => a.id === id);
    if (!original) throw new Error("Automation not found");
    return {
      ...original,
      id: `${Date.now()}`,
      name: `${original.name} (Copy)`,
      status: "draft",
      runCount: 0,
      lastRun: null,
    };
  },
  toggleStatus: async (
    id: string,
    newStatus: "active" | "paused"
  ): Promise<Automation> => {
    await delay(500);
    const automation = mockAutomations.find((a) => a.id === id);
    if (!automation) throw new Error("Automation not found");
    return { ...automation, status: newStatus };
  },
};

// Format date helper
const formatDate = (dateStr: string | null): string => {
  if (!dateStr) return "Never";
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
      year: date.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
    });
  } catch {
    return dateStr;
  }
};

export default function AutomationsPage() {
  const queryClient = useQueryClient();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [automationToDelete, setAutomationToDelete] = useState<Automation | null>(
    null
  );

  // Fetch automations
  const { data: automations, isLoading } = useQuery({
    queryKey: ["automations"],
    queryFn: automationsApi.list,
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: automationsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["automations"] });
      toast.success("Automation deleted successfully");
      setDeleteDialogOpen(false);
      setAutomationToDelete(null);
    },
    onError: () => {
      toast.error("Failed to delete automation");
    },
  });

  // Duplicate mutation
  const duplicateMutation = useMutation({
    mutationFn: automationsApi.duplicate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["automations"] });
      toast.success("Automation duplicated successfully");
    },
    onError: () => {
      toast.error("Failed to duplicate automation");
    },
  });

  // Toggle status mutation
  const toggleStatusMutation = useMutation({
    mutationFn: ({
      id,
      newStatus,
    }: {
      id: string;
      newStatus: "active" | "paused";
    }) => automationsApi.toggleStatus(id, newStatus),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["automations"] });
      toast.success(
        `Automation ${data.status === "active" ? "activated" : "paused"}`
      );
    },
    onError: () => {
      toast.error("Failed to update automation status");
    },
  });

  // Handle delete confirmation
  const handleDeleteClick = (automation: Automation) => {
    setAutomationToDelete(automation);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (automationToDelete) {
      deleteMutation.mutate(automationToDelete.id);
    }
  };

  // Column definitions
  const columns: ColumnDef<Automation, unknown>[] = [
    {
      accessorKey: "name",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Name" />
      ),
      cell: ({ row }) => {
        const automation = row.original;
        return (
          <div className="flex flex-col gap-0.5">
            <Link
              href={`/automations/${automation.id}`}
              className="font-medium text-foreground hover:text-primary transition-colors"
            >
              {automation.name}
            </Link>
            <span className="text-xs text-muted-foreground line-clamp-1">
              {automation.description}
            </span>
          </div>
        );
      },
      enableSorting: true,
    },
    {
      accessorKey: "status",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Status" />
      ),
      cell: ({ row }) => {
        const status = row.getValue("status") as Automation["status"];
        const config = statusConfig[status];
        return (
          <span
            className={cn(
              "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border",
              config.className
            )}
          >
            {config.label}
          </span>
        );
      },
      enableSorting: true,
    },
    {
      accessorKey: "triggerType",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Trigger" />
      ),
      cell: ({ row }) => {
        const triggerType = row.getValue("triggerType") as Automation["triggerType"];
        const config = triggerConfig[triggerType];
        const TriggerIcon = config.icon;
        return (
          <div className="flex items-center gap-2 text-muted-foreground">
            <TriggerIcon className="h-4 w-4" />
            <span className="text-sm">{config.label}</span>
          </div>
        );
      },
      enableSorting: true,
    },
    {
      accessorKey: "lastRun",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Last Run" />
      ),
      cell: ({ row }) => {
        const lastRun = row.getValue("lastRun") as string | null;
        return (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span className="text-sm">{formatDate(lastRun)}</span>
          </div>
        );
      },
      enableSorting: true,
    },
    {
      accessorKey: "runCount",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Runs" />
      ),
      cell: ({ row }) => {
        const runCount = row.getValue("runCount") as number;
        return (
          <span className="text-sm text-muted-foreground font-mono">
            {runCount.toLocaleString()}
          </span>
        );
      },
      enableSorting: true,
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => {
        const automation = row.original;
        const canToggle = automation.status !== "draft";
        const isActive = automation.status === "active";

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
                <Link href={`/automations/${automation.id}`}>
                  <Edit className="mr-2 h-4 w-4" />
                  Edit
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => duplicateMutation.mutate(automation.id)}
                disabled={duplicateMutation.isPending}
              >
                <Copy className="mr-2 h-4 w-4" />
                Duplicate
              </DropdownMenuItem>
              {canToggle && (
                <DropdownMenuItem
                  onClick={() =>
                    toggleStatusMutation.mutate({
                      id: automation.id,
                      newStatus: isActive ? "paused" : "active",
                    })
                  }
                  disabled={toggleStatusMutation.isPending}
                >
                  {isActive ? (
                    <>
                      <Pause className="mr-2 h-4 w-4" />
                      Pause
                    </>
                  ) : (
                    <>
                      <Play className="mr-2 h-4 w-4" />
                      Activate
                    </>
                  )}
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => handleDeleteClick(automation)}
                className="text-destructive focus:text-destructive"
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
    },
  ];

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="space-y-8">
        {/* Header skeleton */}
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton className="h-8 w-40" />
            <Skeleton className="h-4 w-64" />
          </div>
          <Skeleton className="h-9 w-40" />
        </div>

        {/* Table skeleton */}
        <div className="simple-card p-0">
          <div className="p-4 border-b border-border">
            <Skeleton className="h-9 w-64" />
          </div>
          <div className="divide-y divide-border">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="p-4 flex items-center gap-4">
                <Skeleton className="h-4 flex-1" />
                <Skeleton className="h-6 w-20" />
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-12" />
                <Skeleton className="h-8 w-8" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Empty state
  if (!automations || automations.length === 0) {
    return (
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Automations</h1>
            <p className="text-muted-foreground mt-1">
              Create workflows to automate your job search
            </p>
          </div>
        </div>

        {/* Empty state card */}
        <div className="simple-card text-center py-16">
          <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-6">
            <Zap className="h-8 w-8 text-primary" />
          </div>
          <h2 className="text-xl font-semibold mb-2">No automations yet</h2>
          <p className="text-muted-foreground max-w-md mx-auto mb-8">
            Automations help you streamline your job search by automatically
            tailoring resumes, generating cover letters, and more.
          </p>
          <Button asChild className="btn-primary">
            <Link href="/automations/new">
              <Plus className="h-4 w-4 mr-2" />
              Create your first automation
            </Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Automations</h1>
          <p className="text-muted-foreground mt-1">
            Manage your automated workflows
          </p>
        </div>
        <Button asChild className="btn-primary">
          <Link href="/automations/new">
            <Plus className="h-4 w-4 mr-2" />
            Create Automation
          </Link>
        </Button>
      </div>

      {/* Data Table */}
      <div className="simple-card p-0 overflow-hidden">
        <DataTable
          columns={columns}
          data={automations}
          enableSearch
          searchPlaceholder="Search automations..."
          enablePagination
          defaultPageSize={10}
          pageSizeOptions={[5, 10, 20, 50]}
          enableSorting
        />
      </div>

      {/* Delete confirmation dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete automation?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete{" "}
              <span className="font-medium text-foreground">
                {automationToDelete?.name}
              </span>
              . This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
