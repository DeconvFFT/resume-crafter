/**
 * React Query hooks for automation API endpoints.
 *
 * Provides hooks for:
 * - useCampaigns() - CRUD for search campaigns
 * - useDiscoveredJobs() - List and manage discovered jobs
 * - useApplications() - List and manage applications
 * - useAutomationStats() - Dashboard statistics
 * - useAutomationLogs() - Audit logs
 */

"use client";

import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryOptions,
} from "@tanstack/react-query";
import { api, handleApiError } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth";
import type {
  SearchCampaignCreate,
  SearchCampaignResponse,
  SearchCampaignListResponse,
  DiscoveredJobListResponse,
  AnalyzeJobResponse,
  BulkActionRequest,
  BulkActionResponse,
  JobApplicationListResponse,
  JobApplicationResponse,
  ApplicationStatus,
  AutomationDashboard,
  AutomationLogListResponse,
} from "@/lib/types/api";

// ============================================================================
// Query Keys
// ============================================================================

export const automationKeys = {
  all: ["automation"] as const,
  campaigns: () => [...automationKeys.all, "campaigns"] as const,
  campaignsList: (params?: { status?: string; limit?: number; offset?: number }) =>
    [...automationKeys.campaigns(), "list", params] as const,
  campaign: (id: string) => [...automationKeys.campaigns(), id] as const,
  discoveredJobs: () => [...automationKeys.all, "discovered-jobs"] as const,
  discoveredJobsList: (params?: {
    campaign_id?: string;
    min_score?: number;
    is_qualified?: boolean;
    company?: string;
    limit?: number;
    offset?: number;
  }) => [...automationKeys.discoveredJobs(), "list", params] as const,
  applications: () => [...automationKeys.all, "applications"] as const,
  applicationsList: (params?: {
    status?: string;
    campaign_id?: string;
    company?: string;
    limit?: number;
    offset?: number;
  }) => [...automationKeys.applications(), "list", params] as const,
  stats: () => [...automationKeys.all, "stats"] as const,
  logs: () => [...automationKeys.all, "logs"] as const,
  logsList: (params?: {
    action_type?: string;
    entity_type?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }) => [...automationKeys.logs(), "list", params] as const,
};

// ============================================================================
// Campaign Hooks
// ============================================================================

export interface UseCampaignsOptions {
  status?: string;
  limit?: number;
  offset?: number;
  enabled?: boolean;
}

export function useCampaigns(options: UseCampaignsOptions = {}) {
  const accessToken = useAuthStore((state) => state.accessToken);
  const { status, limit, offset, enabled = true } = options;

  return useQuery({
    queryKey: automationKeys.campaignsList({ status, limit, offset }),
    queryFn: async () => {
      if (!accessToken) throw new Error("Not authenticated");
      return api.automation.campaigns.list(accessToken, { status, limit, offset });
    },
    enabled: enabled && !!accessToken,
  });
}

export function useCampaign(campaignId: string | null, enabled = true) {
  const accessToken = useAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: automationKeys.campaign(campaignId || ""),
    queryFn: async () => {
      if (!accessToken) throw new Error("Not authenticated");
      if (!campaignId) throw new Error("Campaign ID required");
      return api.automation.campaigns.get(accessToken, campaignId);
    },
    enabled: enabled && !!accessToken && !!campaignId,
  });
}

export function useCreateCampaign() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: SearchCampaignCreate) => {
      if (!accessToken) throw new Error("Not authenticated");
      return api.automation.campaigns.create(accessToken, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: automationKeys.campaigns() });
    },
    onError: handleApiError,
  });
}

export function useActivateCampaign() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (campaignId: string) => {
      if (!accessToken) throw new Error("Not authenticated");
      return api.automation.campaigns.activate(accessToken, campaignId);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: automationKeys.campaigns() });
      queryClient.setQueryData(automationKeys.campaign(data.id), data);
    },
    onError: handleApiError,
  });
}

export function usePauseCampaign() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (campaignId: string) => {
      if (!accessToken) throw new Error("Not authenticated");
      return api.automation.campaigns.pause(accessToken, campaignId);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: automationKeys.campaigns() });
      queryClient.setQueryData(automationKeys.campaign(data.id), data);
    },
    onError: handleApiError,
  });
}

// ============================================================================
// Discovered Jobs Hooks
// ============================================================================

export interface UseDiscoveredJobsOptions {
  campaign_id?: string;
  min_score?: number;
  is_qualified?: boolean;
  company?: string;
  limit?: number;
  offset?: number;
  enabled?: boolean;
}

export function useDiscoveredJobs(options: UseDiscoveredJobsOptions = {}) {
  const accessToken = useAuthStore((state) => state.accessToken);
  const { enabled = true, ...params } = options;

  return useQuery({
    queryKey: automationKeys.discoveredJobsList(params),
    queryFn: async () => {
      if (!accessToken) throw new Error("Not authenticated");
      return api.automation.discoveredJobs.list(accessToken, params);
    },
    enabled: enabled && !!accessToken,
  });
}

export function useAnalyzeJob() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (jobId: string) => {
      if (!accessToken) throw new Error("Not authenticated");
      return api.automation.discoveredJobs.analyze(accessToken, jobId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: automationKeys.discoveredJobs() });
    },
    onError: handleApiError,
  });
}

export function useBulkJobAction() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: BulkActionRequest) => {
      if (!accessToken) throw new Error("Not authenticated");
      return api.automation.discoveredJobs.bulkAction(accessToken, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: automationKeys.discoveredJobs() });
    },
    onError: handleApiError,
  });
}

// ============================================================================
// Applications Hooks
// ============================================================================

export interface UseApplicationsOptions {
  status?: string;
  campaign_id?: string;
  company?: string;
  limit?: number;
  offset?: number;
  enabled?: boolean;
}

export function useApplications(options: UseApplicationsOptions = {}) {
  const accessToken = useAuthStore((state) => state.accessToken);
  const { enabled = true, ...params } = options;

  return useQuery({
    queryKey: automationKeys.applicationsList(params),
    queryFn: async () => {
      if (!accessToken) throw new Error("Not authenticated");
      return api.automation.applications.list(accessToken, params);
    },
    enabled: enabled && !!accessToken,
  });
}

export function useQueueApplication() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: { discovered_job_id: string; notes?: string }) => {
      if (!accessToken) throw new Error("Not authenticated");
      return api.automation.applications.queue(accessToken, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: automationKeys.applications() });
      queryClient.invalidateQueries({ queryKey: automationKeys.discoveredJobs() });
    },
    onError: handleApiError,
  });
}

export function useUpdateApplicationStatus() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      applicationId,
      status,
      notes,
    }: {
      applicationId: string;
      status: ApplicationStatus;
      notes?: string;
    }) => {
      if (!accessToken) throw new Error("Not authenticated");
      return api.automation.applications.updateStatus(accessToken, applicationId, {
        status,
        notes,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: automationKeys.applications() });
      queryClient.invalidateQueries({ queryKey: automationKeys.stats() });
    },
    onError: handleApiError,
  });
}

// ============================================================================
// Stats & Logs Hooks
// ============================================================================

export function useAutomationStats(enabled = true) {
  const accessToken = useAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: automationKeys.stats(),
    queryFn: async () => {
      if (!accessToken) throw new Error("Not authenticated");
      return api.automation.stats.getDashboard(accessToken);
    },
    enabled: enabled && !!accessToken,
  });
}

export interface UseAutomationLogsOptions {
  action_type?: string;
  entity_type?: string;
  status?: string;
  limit?: number;
  offset?: number;
  enabled?: boolean;
}

export function useAutomationLogs(options: UseAutomationLogsOptions = {}) {
  const accessToken = useAuthStore((state) => state.accessToken);
  const { enabled = true, ...params } = options;

  return useQuery({
    queryKey: automationKeys.logsList(params),
    queryFn: async () => {
      if (!accessToken) throw new Error("Not authenticated");
      return api.automation.logs.list(accessToken, params);
    },
    enabled: enabled && !!accessToken,
  });
}
