/**
 * React Query hooks for workflow execution monitoring.
 *
 * Provides hooks for:
 * - useExecutions() - List and filter workflow executions
 * - useExecution() - Get execution details with steps and logs
 * - useCancelExecution() - Cancel a running execution
 * - useExecutionLogs() - Get paginated execution logs
 */

"use client";

import {
  useQuery,
  useMutation,
  useQueryClient,
  useInfiniteQuery,
} from "@tanstack/react-query";
import { api, handleApiError } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth";
import type {
  ExecutionStatus,
  WorkflowType,
  ExecutionListResponse,
  ExecutionDetailResponse,
  ExecutionCancelResponse,
  ExecutionLogListResponse,
} from "@/lib/types/api";

// ============================================================================
// Query Keys
// ============================================================================

export const executionKeys = {
  all: ["executions"] as const,
  lists: () => [...executionKeys.all, "list"] as const,
  list: (params?: {
    workflow_type?: string;
    status?: string;
    campaign_id?: string;
    entity_id?: string;
    started_after?: string;
    started_before?: string;
    page?: number;
    page_size?: number;
  }) => [...executionKeys.lists(), params] as const,
  details: () => [...executionKeys.all, "detail"] as const,
  detail: (id: string) => [...executionKeys.details(), id] as const,
  logs: (id: string) => [...executionKeys.all, "logs", id] as const,
};

// ============================================================================
// Executions List Hooks
// ============================================================================

export interface UseExecutionsOptions {
  workflow_type?: WorkflowType;
  status?: ExecutionStatus;
  campaign_id?: string;
  entity_id?: string;
  started_after?: string;
  started_before?: string;
  page?: number;
  page_size?: number;
  enabled?: boolean;
  refetchInterval?: number | false;
}

export function useExecutions(options: UseExecutionsOptions = {}) {
  const accessToken = useAuthStore((state) => state.accessToken);
  const {
    enabled = true,
    refetchInterval = false,
    workflow_type,
    status,
    campaign_id,
    entity_id,
    started_after,
    started_before,
    page,
    page_size,
  } = options;

  const params = {
    workflow_type,
    status,
    campaign_id,
    entity_id,
    started_after,
    started_before,
    page,
    page_size,
  };

  return useQuery({
    queryKey: executionKeys.list(params),
    queryFn: async () => {
      if (!accessToken) throw new Error("Not authenticated");
      return api.automation.executions.list(accessToken, params);
    },
    enabled: enabled && !!accessToken,
    refetchInterval,
  });
}

// ============================================================================
// Execution Detail Hook
// ============================================================================

export interface UseExecutionOptions {
  include_logs?: boolean;
  log_limit?: number;
  enabled?: boolean;
  refetchInterval?: number | false;
}

export function useExecution(executionId: string | null, options: UseExecutionOptions = {}) {
  const accessToken = useAuthStore((state) => state.accessToken);
  const { include_logs = true, log_limit = 50, enabled = true, refetchInterval = false } = options;

  return useQuery({
    queryKey: executionKeys.detail(executionId || ""),
    queryFn: async () => {
      if (!accessToken) throw new Error("Not authenticated");
      if (!executionId) throw new Error("Execution ID required");
      return api.automation.executions.get(accessToken, executionId, {
        include_logs,
        log_limit,
      });
    },
    enabled: enabled && !!accessToken && !!executionId,
    refetchInterval,
  });
}

// ============================================================================
// Cancel Execution Hook
// ============================================================================

export function useCancelExecution() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      executionId,
      reason,
    }: {
      executionId: string;
      reason?: string;
    }) => {
      if (!accessToken) throw new Error("Not authenticated");
      return api.automation.executions.cancel(accessToken, executionId, reason);
    },
    onSuccess: (data) => {
      // Update the execution in cache
      queryClient.setQueryData(executionKeys.detail(data.id), (old: ExecutionDetailResponse | undefined) => {
        if (!old) return old;
        return {
          ...old,
          status: data.status,
          completed_at: data.cancelled_at,
          error_message: data.reason,
        };
      });
      // Invalidate list queries
      queryClient.invalidateQueries({ queryKey: executionKeys.lists() });
    },
    onError: handleApiError,
  });
}

// ============================================================================
// Execution Logs Hook
// ============================================================================

export interface UseExecutionLogsOptions {
  level?: string;
  step_id?: string;
  limit?: number;
  newest_first?: boolean;
  enabled?: boolean;
}

export function useExecutionLogs(
  executionId: string | null,
  options: UseExecutionLogsOptions = {}
) {
  const accessToken = useAuthStore((state) => state.accessToken);
  const { level, step_id, limit = 100, newest_first = true, enabled = true } = options;

  return useInfiniteQuery({
    queryKey: [...executionKeys.logs(executionId || ""), { level, step_id, newest_first }],
    queryFn: async ({ pageParam = 0 }) => {
      if (!accessToken) throw new Error("Not authenticated");
      if (!executionId) throw new Error("Execution ID required");
      return api.automation.executions.getLogs(accessToken, executionId, {
        level,
        step_id,
        offset: pageParam,
        limit,
        newest_first,
      });
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      if (!lastPage.has_more) return undefined;
      return allPages.reduce((total, page) => total + page.items.length, 0);
    },
    enabled: enabled && !!accessToken && !!executionId,
  });
}

// ============================================================================
// Cron Jobs Hooks
// ============================================================================

export const cronJobKeys = {
  all: ["cron-jobs"] as const,
  list: () => [...cronJobKeys.all, "list"] as const,
  detail: (jobType: string) => [...cronJobKeys.all, jobType] as const,
  schedule: () => [...cronJobKeys.all, "schedule"] as const,
};

export function useCronJobs(enabled = true) {
  const accessToken = useAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: cronJobKeys.list(),
    queryFn: async () => {
      if (!accessToken) throw new Error("Not authenticated");
      return api.automation.cronJobs.list(accessToken);
    },
    enabled: enabled && !!accessToken,
  });
}

export function useCronJob(jobType: string | null, enabled = true) {
  const accessToken = useAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: cronJobKeys.detail(jobType || ""),
    queryFn: async () => {
      if (!accessToken) throw new Error("Not authenticated");
      if (!jobType) throw new Error("Job type required");
      return api.automation.cronJobs.get(accessToken, jobType);
    },
    enabled: enabled && !!accessToken && !!jobType,
  });
}

export function usePauseCronJob() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (jobType: string) => {
      if (!accessToken) throw new Error("Not authenticated");
      return api.automation.cronJobs.pause(accessToken, jobType);
    },
    onSuccess: (data) => {
      queryClient.setQueryData(cronJobKeys.detail(data.job_type), data);
      queryClient.invalidateQueries({ queryKey: cronJobKeys.list() });
    },
    onError: handleApiError,
  });
}

export function useResumeCronJob() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (jobType: string) => {
      if (!accessToken) throw new Error("Not authenticated");
      return api.automation.cronJobs.resume(accessToken, jobType);
    },
    onSuccess: (data) => {
      queryClient.setQueryData(cronJobKeys.detail(data.job_type), data);
      queryClient.invalidateQueries({ queryKey: cronJobKeys.list() });
    },
    onError: handleApiError,
  });
}

export function useTriggerCronJob() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (jobType: string) => {
      if (!accessToken) throw new Error("Not authenticated");
      return api.automation.cronJobs.trigger(accessToken, jobType);
    },
    onSuccess: (data) => {
      queryClient.setQueryData(cronJobKeys.detail(data.job_type), data);
      queryClient.invalidateQueries({ queryKey: cronJobKeys.list() });
      // Also refresh executions since a new one might have been created
      queryClient.invalidateQueries({ queryKey: executionKeys.lists() });
    },
    onError: handleApiError,
  });
}

export function useCronSchedule(enabled = true) {
  const accessToken = useAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: cronJobKeys.schedule(),
    queryFn: async () => {
      if (!accessToken) throw new Error("Not authenticated");
      return api.automation.cronJobs.getSchedule(accessToken);
    },
    enabled: enabled && !!accessToken,
  });
}

export function useUpdateCronSchedule() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (schedule: {
      job_discovery_interval_hours: number;
      job_analysis_interval_hours: number;
      application_queue_delay_seconds: number;
      application_queue_batch_size: number;
    }) => {
      if (!accessToken) throw new Error("Not authenticated");
      return api.automation.cronJobs.updateSchedule(accessToken, schedule);
    },
    onSuccess: (data) => {
      queryClient.setQueryData(cronJobKeys.schedule(), data);
      queryClient.invalidateQueries({ queryKey: cronJobKeys.list() });
    },
    onError: handleApiError,
  });
}
