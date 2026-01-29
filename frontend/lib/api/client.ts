/**
 * API client for communicating with the Resume Crafter backend.
 */

import { toast } from "sonner";
import type {
  TokenResponse,
  UserResponse,
  ProfileUpdate,
  DocumentResponse,
  DocumentListResponse,
  ExperienceResponse,
  ExperienceListResponse,
  ExperienceCreate,
  ExperienceUpdate,
  ProjectResponse,
  ProjectListResponse,
  ProjectCreate,
  SkillResponse,
  SkillListResponse,
  SkillCreate,
  SkillUpdate,
  SkillCategoryGroup,
  PublicationResponse,
  PublicationListResponse,
  PublicationCreate,
  PublicationUpdate,
  JobResponse,
  JobListResponse,
  ResumeMatchResponse,
  MatchListResponse,
  ResumeGenerateResponse,
  TaskStatusResponse,
  // Automation types
  SearchCampaignCreate,
  SearchCampaignResponse,
  SearchCampaignListResponse,
  DiscoveredJobListResponse,
  AnalyzeJobResponse,
  BulkActionRequest,
  BulkActionResponse,
  JobApplicationListResponse,
  JobApplicationResponse,
  QueueApplicationRequest,
  ApplicationStatusUpdateRequest,
  AutomationDashboard,
  AutomationLogListResponse,
  // Execution types
  ExecutionListResponse,
  ExecutionDetailResponse,
  ExecutionCancelResponse,
  ExecutionLogListResponse,
  // Cron job types
  CronJobConfig,
  CronJobResponse,
  CronJobListResponse,
  CronJobTriggerResponse,
  CronJobSchedule,
} from "@/lib/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ErrorResponse {
  error_code: string;
  message: string;
  detail: string | null;
  correlation_id: string;
}

export class ApiError extends Error {
  constructor(
    public statusCode: number,
    public errorCode: string,
    message: string,
    public detail: string | null,
    public correlationId: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorData: ErrorResponse;
    try {
      errorData = await response.json();
    } catch {
      throw new ApiError(
        response.status,
        "UNKNOWN_ERROR",
        response.statusText || "Unknown error",
        null,
        "unknown"
      );
    }
    throw new ApiError(
      response.status,
      errorData.error_code,
      errorData.message,
      errorData.detail,
      errorData.correlation_id
    );
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

function getAuthHeaders(token?: string): HeadersInit {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export const api = {
  // Auth endpoints
  auth: {
    register: async (email: string, password: string, fullName?: string): Promise<UserResponse> => {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, full_name: fullName }),
      });
      return handleResponse<UserResponse>(response);
    },

    login: async (email: string, password: string): Promise<TokenResponse> => {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      return handleResponse<TokenResponse>(response);
    },

    refresh: async (refreshToken: string): Promise<TokenResponse> => {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      return handleResponse<TokenResponse>(response);
    },

    me: async (token: string): Promise<UserResponse> => {
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: getAuthHeaders(token),
      });
      return handleResponse<UserResponse>(response);
    },
  },

  // Profile endpoints
  profile: {
    get: async (token: string): Promise<UserResponse> => {
      const response = await fetch(`${API_BASE_URL}/profile`, {
        headers: getAuthHeaders(token),
      });
      return handleResponse<UserResponse>(response);
    },

    update: async (token: string, data: ProfileUpdate): Promise<UserResponse> => {
      const response = await fetch(`${API_BASE_URL}/profile`, {
        method: "PATCH",
        headers: getAuthHeaders(token),
        body: JSON.stringify(data),
      });
      return handleResponse<UserResponse>(response);
    },
  },

  // Document endpoints
  documents: {
    list: async (token: string): Promise<DocumentListResponse> => {
      const response = await fetch(`${API_BASE_URL}/documents`, {
        headers: getAuthHeaders(token),
      });
      return handleResponse<DocumentListResponse>(response);
    },

    upload: async (token: string, file: File): Promise<DocumentResponse> => {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE_URL}/documents/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      return handleResponse<DocumentResponse>(response);
    },

    importGoogleDoc: async (token: string, googleDocId: string): Promise<DocumentResponse> => {
      const response = await fetch(`${API_BASE_URL}/documents/google`, {
        method: "POST",
        headers: getAuthHeaders(token),
        body: JSON.stringify({ google_doc_id: googleDocId }),
      });
      return handleResponse<DocumentResponse>(response);
    },

    get: async (token: string, id: string): Promise<DocumentResponse> => {
      const response = await fetch(`${API_BASE_URL}/documents/${id}`, {
        headers: getAuthHeaders(token),
      });
      return handleResponse<DocumentResponse>(response);
    },

    verify: async (token: string, id: string, documentClass: string): Promise<DocumentResponse> => {
      const response = await fetch(`${API_BASE_URL}/documents/${id}/verify`, {
        method: "PUT",
        headers: getAuthHeaders(token),
        body: JSON.stringify({ document_class: documentClass }),
      });
      return handleResponse<DocumentResponse>(response);
    },

    delete: async (token: string, id: string): Promise<void> => {
      const response = await fetch(`${API_BASE_URL}/documents/${id}`, {
        method: "DELETE",
        headers: getAuthHeaders(token),
      });
      return handleResponse<void>(response);
    },
  },

  // Experience endpoints
  experiences: {
    list: async (token: string): Promise<ExperienceListResponse> => {
      const response = await fetch(`${API_BASE_URL}/experiences`, {
        headers: getAuthHeaders(token),
      });
      return handleResponse<ExperienceListResponse>(response);
    },

    create: async (token: string, data: ExperienceCreate): Promise<ExperienceResponse> => {
      const response = await fetch(`${API_BASE_URL}/experiences`, {
        method: "POST",
        headers: getAuthHeaders(token),
        body: JSON.stringify(data),
      });
      return handleResponse<ExperienceResponse>(response);
    },

    update: async (token: string, id: string, data: ExperienceUpdate): Promise<ExperienceResponse> => {
      const response = await fetch(`${API_BASE_URL}/experiences/${id}`, {
        method: "PATCH",
        headers: getAuthHeaders(token),
        body: JSON.stringify(data),
      });
      return handleResponse<ExperienceResponse>(response);
    },

    delete: async (token: string, id: string): Promise<void> => {
      const response = await fetch(`${API_BASE_URL}/experiences/${id}`, {
        method: "DELETE",
        headers: getAuthHeaders(token),
      });
      return handleResponse<void>(response);
    },
  },

  // Project endpoints
  projects: {
    list: async (token: string): Promise<ProjectListResponse> => {
      const response = await fetch(`${API_BASE_URL}/projects`, {
        headers: getAuthHeaders(token),
      });
      return handleResponse<ProjectListResponse>(response);
    },

    create: async (token: string, data: ProjectCreate): Promise<ProjectResponse> => {
      const response = await fetch(`${API_BASE_URL}/projects`, {
        method: "POST",
        headers: getAuthHeaders(token),
        body: JSON.stringify(data),
      });
      return handleResponse<ProjectResponse>(response);
    },

    delete: async (token: string, id: string): Promise<void> => {
      const response = await fetch(`${API_BASE_URL}/projects/${id}`, {
        method: "DELETE",
        headers: getAuthHeaders(token),
      });
      return handleResponse<void>(response);
    },

    enrich: async (token: string, projectId: string, githubUrl: string): Promise<{ task_id: string; message: string }> => {
      const response = await fetch(`${API_BASE_URL}/projects/${projectId}/enrich`, {
        method: "POST",
        headers: getAuthHeaders(token),
        body: JSON.stringify({ github_url: githubUrl }),
      });
      return handleResponse<{ task_id: string; message: string }>(response);
    },
  },

  // Skill endpoints
  skills: {
    list: async (token: string, category?: string): Promise<SkillListResponse> => {
      const url = category
        ? `${API_BASE_URL}/skills?category=${category}`
        : `${API_BASE_URL}/skills`;
      const response = await fetch(url, {
        headers: getAuthHeaders(token),
      });
      return handleResponse<SkillListResponse>(response);
    },

    listGrouped: async (token: string): Promise<SkillCategoryGroup[]> => {
      const response = await fetch(`${API_BASE_URL}/skills/grouped`, {
        headers: getAuthHeaders(token),
      });
      return handleResponse<SkillCategoryGroup[]>(response);
    },

    create: async (token: string, data: SkillCreate): Promise<SkillResponse> => {
      const response = await fetch(`${API_BASE_URL}/skills`, {
        method: "POST",
        headers: getAuthHeaders(token),
        body: JSON.stringify(data),
      });
      return handleResponse<SkillResponse>(response);
    },

    createBulk: async (token: string, skills: SkillCreate[]): Promise<SkillListResponse> => {
      const response = await fetch(`${API_BASE_URL}/skills/bulk`, {
        method: "POST",
        headers: getAuthHeaders(token),
        body: JSON.stringify({ skills }),
      });
      return handleResponse<SkillListResponse>(response);
    },

    update: async (token: string, id: string, data: SkillUpdate): Promise<SkillResponse> => {
      const response = await fetch(`${API_BASE_URL}/skills/${id}`, {
        method: "PATCH",
        headers: getAuthHeaders(token),
        body: JSON.stringify(data),
      });
      return handleResponse<SkillResponse>(response);
    },

    delete: async (token: string, id: string): Promise<void> => {
      const response = await fetch(`${API_BASE_URL}/skills/${id}`, {
        method: "DELETE",
        headers: getAuthHeaders(token),
      });
      return handleResponse<void>(response);
    },
  },

  // Publication endpoints
  publications: {
    list: async (token: string, publicationType?: string): Promise<PublicationListResponse> => {
      const url = publicationType
        ? `${API_BASE_URL}/publications?publication_type=${publicationType}`
        : `${API_BASE_URL}/publications`;
      const response = await fetch(url, {
        headers: getAuthHeaders(token),
      });
      return handleResponse<PublicationListResponse>(response);
    },

    create: async (token: string, data: PublicationCreate): Promise<PublicationResponse> => {
      const response = await fetch(`${API_BASE_URL}/publications`, {
        method: "POST",
        headers: getAuthHeaders(token),
        body: JSON.stringify(data),
      });
      return handleResponse<PublicationResponse>(response);
    },

    update: async (token: string, id: string, data: PublicationUpdate): Promise<PublicationResponse> => {
      const response = await fetch(`${API_BASE_URL}/publications/${id}`, {
        method: "PATCH",
        headers: getAuthHeaders(token),
        body: JSON.stringify(data),
      });
      return handleResponse<PublicationResponse>(response);
    },

    delete: async (token: string, id: string): Promise<void> => {
      const response = await fetch(`${API_BASE_URL}/publications/${id}`, {
        method: "DELETE",
        headers: getAuthHeaders(token),
      });
      return handleResponse<void>(response);
    },
  },

  // Job endpoints
  jobs: {
    list: async (token: string): Promise<JobListResponse> => {
      const response = await fetch(`${API_BASE_URL}/jobs`, {
        headers: getAuthHeaders(token),
      });
      return handleResponse<JobListResponse>(response);
    },

    analyze: async (token: string, sourceUrl?: string, rawText?: string): Promise<JobResponse> => {
      const response = await fetch(`${API_BASE_URL}/jobs/analyze`, {
        method: "POST",
        headers: getAuthHeaders(token),
        body: JSON.stringify({ source_url: sourceUrl, raw_text: rawText }),
      });
      return handleResponse<JobResponse>(response);
    },

    get: async (token: string, id: string): Promise<JobResponse> => {
      const response = await fetch(`${API_BASE_URL}/jobs/${id}`, {
        headers: getAuthHeaders(token),
      });
      return handleResponse<JobResponse>(response);
    },

    delete: async (token: string, id: string): Promise<void> => {
      const response = await fetch(`${API_BASE_URL}/jobs/${id}`, {
        method: "DELETE",
        headers: getAuthHeaders(token),
      });
      return handleResponse<void>(response);
    },
  },

  // Resume endpoints
  resume: {
    createMatch: async (token: string, jobId: string): Promise<ResumeMatchResponse> => {
      const response = await fetch(`${API_BASE_URL}/resume/match`, {
        method: "POST",
        headers: getAuthHeaders(token),
        body: JSON.stringify({ job_id: jobId }),
      });
      return handleResponse<ResumeMatchResponse>(response);
    },

    listMatches: async (token: string): Promise<MatchListResponse> => {
      const response = await fetch(`${API_BASE_URL}/resume/matches`, {
        headers: getAuthHeaders(token),
      });
      return handleResponse<MatchListResponse>(response);
    },

    getMatch: async (token: string, matchId: string): Promise<ResumeMatchResponse> => {
      const response = await fetch(`${API_BASE_URL}/resume/matches/${matchId}`, {
        headers: getAuthHeaders(token),
      });
      return handleResponse<ResumeMatchResponse>(response);
    },

    toggleItem: async (token: string, matchId: string, itemId: string, included: boolean): Promise<ResumeMatchResponse> => {
      const response = await fetch(
        `${API_BASE_URL}/resume/matches/${matchId}/items/${itemId}`,
        {
          method: "PUT",
          headers: getAuthHeaders(token),
          body: JSON.stringify({ included_in_resume: included }),
        }
      );
      return handleResponse<ResumeMatchResponse>(response);
    },

    generate: async (token: string, matchId: string, format: "json" | "markdown" | "google_doc"): Promise<ResumeGenerateResponse> => {
      const response = await fetch(`${API_BASE_URL}/resume/generate`, {
        method: "POST",
        headers: getAuthHeaders(token),
        body: JSON.stringify({ match_id: matchId, format }),
      });
      return handleResponse<ResumeGenerateResponse>(response);
    },

    deleteMatch: async (token: string, matchId: string): Promise<void> => {
      const response = await fetch(`${API_BASE_URL}/resume/matches/${matchId}`, {
        method: "DELETE",
        headers: getAuthHeaders(token),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Failed to delete match" }));
        throw new Error(error.detail || "Failed to delete match");
      }
    },
  },

  // Task status endpoints
  tasks: {
    getStatus: async (token: string, taskId: string): Promise<TaskStatusResponse> => {
      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/status`, {
        headers: getAuthHeaders(token),
      });
      return handleResponse<TaskStatusResponse>(response);
    },

    getByEntity: async (token: string, entityId: string, taskType?: string): Promise<TaskStatusResponse | null> => {
      const url = taskType
        ? `${API_BASE_URL}/tasks/entity/${entityId}?task_type=${taskType}`
        : `${API_BASE_URL}/tasks/entity/${entityId}`;
      const response = await fetch(url, {
        headers: getAuthHeaders(token),
      });
      if (response.status === 200) {
        return handleResponse<TaskStatusResponse>(response);
      }
      return null;
    },
  },

  // Automation endpoints
  automation: {
    // Campaign endpoints
    campaigns: {
      list: async (
        token: string,
        params?: { status?: string; limit?: number; offset?: number }
      ): Promise<SearchCampaignListResponse> => {
        const searchParams = new URLSearchParams();
        if (params?.status) searchParams.append("status", params.status);
        if (params?.limit) searchParams.append("limit", params.limit.toString());
        if (params?.offset) searchParams.append("offset", params.offset.toString());
        const query = searchParams.toString();
        const response = await fetch(
          `${API_BASE_URL}/api/automation/campaigns${query ? `?${query}` : ""}`,
          { headers: getAuthHeaders(token) }
        );
        return handleResponse<SearchCampaignListResponse>(response);
      },

      get: async (token: string, campaignId: string): Promise<SearchCampaignResponse> => {
        const response = await fetch(`${API_BASE_URL}/api/automation/campaigns/${campaignId}`, {
          headers: getAuthHeaders(token),
        });
        return handleResponse<SearchCampaignResponse>(response);
      },

      create: async (token: string, data: SearchCampaignCreate): Promise<SearchCampaignResponse> => {
        const response = await fetch(`${API_BASE_URL}/api/automation/campaigns`, {
          method: "POST",
          headers: getAuthHeaders(token),
          body: JSON.stringify(data),
        });
        return handleResponse<SearchCampaignResponse>(response);
      },

      activate: async (token: string, campaignId: string): Promise<SearchCampaignResponse> => {
        const response = await fetch(`${API_BASE_URL}/api/automation/campaigns/${campaignId}/activate`, {
          method: "POST",
          headers: getAuthHeaders(token),
        });
        return handleResponse<SearchCampaignResponse>(response);
      },

      pause: async (token: string, campaignId: string): Promise<SearchCampaignResponse> => {
        const response = await fetch(`${API_BASE_URL}/api/automation/campaigns/${campaignId}/pause`, {
          method: "POST",
          headers: getAuthHeaders(token),
        });
        return handleResponse<SearchCampaignResponse>(response);
      },
    },

    // Discovered jobs endpoints
    discoveredJobs: {
      list: async (
        token: string,
        params?: {
          campaign_id?: string;
          min_score?: number;
          is_qualified?: boolean;
          company?: string;
          limit?: number;
          offset?: number;
        }
      ): Promise<DiscoveredJobListResponse> => {
        const searchParams = new URLSearchParams();
        if (params?.campaign_id) searchParams.append("campaign_id", params.campaign_id);
        if (params?.min_score !== undefined) searchParams.append("min_score", params.min_score.toString());
        if (params?.is_qualified !== undefined) searchParams.append("is_qualified", params.is_qualified.toString());
        if (params?.company) searchParams.append("company", params.company);
        if (params?.limit) searchParams.append("limit", params.limit.toString());
        if (params?.offset) searchParams.append("offset", params.offset.toString());
        const query = searchParams.toString();
        const response = await fetch(
          `${API_BASE_URL}/api/automation/discovered-jobs${query ? `?${query}` : ""}`,
          { headers: getAuthHeaders(token) }
        );
        return handleResponse<DiscoveredJobListResponse>(response);
      },

      analyze: async (token: string, jobId: string): Promise<AnalyzeJobResponse> => {
        const response = await fetch(`${API_BASE_URL}/api/automation/discovered-jobs/${jobId}/analyze`, {
          method: "POST",
          headers: getAuthHeaders(token),
        });
        return handleResponse<AnalyzeJobResponse>(response);
      },

      bulkAction: async (token: string, data: BulkActionRequest): Promise<BulkActionResponse> => {
        const response = await fetch(`${API_BASE_URL}/api/automation/discovered-jobs/bulk-action`, {
          method: "POST",
          headers: getAuthHeaders(token),
          body: JSON.stringify(data),
        });
        return handleResponse<BulkActionResponse>(response);
      },
    },

    // Applications endpoints
    applications: {
      list: async (
        token: string,
        params?: {
          status?: string;
          campaign_id?: string;
          company?: string;
          limit?: number;
          offset?: number;
        }
      ): Promise<JobApplicationListResponse> => {
        const searchParams = new URLSearchParams();
        if (params?.status) searchParams.append("status", params.status);
        if (params?.campaign_id) searchParams.append("campaign_id", params.campaign_id);
        if (params?.company) searchParams.append("company", params.company);
        if (params?.limit) searchParams.append("limit", params.limit.toString());
        if (params?.offset) searchParams.append("offset", params.offset.toString());
        const query = searchParams.toString();
        const response = await fetch(
          `${API_BASE_URL}/api/automation/applications${query ? `?${query}` : ""}`,
          { headers: getAuthHeaders(token) }
        );
        return handleResponse<JobApplicationListResponse>(response);
      },

      queue: async (token: string, data: QueueApplicationRequest): Promise<JobApplicationResponse> => {
        const response = await fetch(`${API_BASE_URL}/api/automation/applications/queue`, {
          method: "POST",
          headers: getAuthHeaders(token),
          body: JSON.stringify(data),
        });
        return handleResponse<JobApplicationResponse>(response);
      },

      updateStatus: async (
        token: string,
        applicationId: string,
        data: ApplicationStatusUpdateRequest
      ): Promise<JobApplicationResponse> => {
        const response = await fetch(`${API_BASE_URL}/api/automation/applications/${applicationId}/status`, {
          method: "PATCH",
          headers: getAuthHeaders(token),
          body: JSON.stringify(data),
        });
        return handleResponse<JobApplicationResponse>(response);
      },
    },

    // Stats endpoints
    stats: {
      getDashboard: async (token: string): Promise<AutomationDashboard> => {
        const response = await fetch(`${API_BASE_URL}/api/automation/stats`, {
          headers: getAuthHeaders(token),
        });
        return handleResponse<AutomationDashboard>(response);
      },
    },

    // Logs endpoints
    logs: {
      list: async (
        token: string,
        params?: {
          action_type?: string;
          entity_type?: string;
          status?: string;
          limit?: number;
          offset?: number;
        }
      ): Promise<AutomationLogListResponse> => {
        const searchParams = new URLSearchParams();
        if (params?.action_type) searchParams.append("action_type", params.action_type);
        if (params?.entity_type) searchParams.append("entity_type", params.entity_type);
        if (params?.status) searchParams.append("status", params.status);
        if (params?.limit) searchParams.append("limit", params.limit.toString());
        if (params?.offset) searchParams.append("offset", params.offset.toString());
        const query = searchParams.toString();
        const response = await fetch(
          `${API_BASE_URL}/api/automation/logs${query ? `?${query}` : ""}`,
          { headers: getAuthHeaders(token) }
        );
        return handleResponse<AutomationLogListResponse>(response);
      },
    },

    // Execution endpoints
    executions: {
      list: async (
        token: string,
        params?: {
          workflow_type?: string;
          status?: string;
          campaign_id?: string;
          entity_id?: string;
          started_after?: string;
          started_before?: string;
          page?: number;
          page_size?: number;
        }
      ): Promise<ExecutionListResponse> => {
        const searchParams = new URLSearchParams();
        if (params?.workflow_type) searchParams.append("workflow_type", params.workflow_type);
        if (params?.status) searchParams.append("status", params.status);
        if (params?.campaign_id) searchParams.append("campaign_id", params.campaign_id);
        if (params?.entity_id) searchParams.append("entity_id", params.entity_id);
        if (params?.started_after) searchParams.append("started_after", params.started_after);
        if (params?.started_before) searchParams.append("started_before", params.started_before);
        if (params?.page) searchParams.append("page", params.page.toString());
        if (params?.page_size) searchParams.append("page_size", params.page_size.toString());
        const query = searchParams.toString();
        const response = await fetch(
          `${API_BASE_URL}/api/automation/executions${query ? `?${query}` : ""}`,
          { headers: getAuthHeaders(token) }
        );
        return handleResponse<ExecutionListResponse>(response);
      },

      get: async (
        token: string,
        executionId: string,
        params?: { include_logs?: boolean; log_limit?: number }
      ): Promise<ExecutionDetailResponse> => {
        const searchParams = new URLSearchParams();
        if (params?.include_logs !== undefined) searchParams.append("include_logs", params.include_logs.toString());
        if (params?.log_limit) searchParams.append("log_limit", params.log_limit.toString());
        const query = searchParams.toString();
        const response = await fetch(
          `${API_BASE_URL}/api/automation/executions/${executionId}${query ? `?${query}` : ""}`,
          { headers: getAuthHeaders(token) }
        );
        return handleResponse<ExecutionDetailResponse>(response);
      },

      cancel: async (token: string, executionId: string, reason?: string): Promise<ExecutionCancelResponse> => {
        const response = await fetch(`${API_BASE_URL}/api/automation/executions/${executionId}/cancel`, {
          method: "POST",
          headers: getAuthHeaders(token),
          body: JSON.stringify(reason ? { reason } : {}),
        });
        return handleResponse<ExecutionCancelResponse>(response);
      },

      getLogs: async (
        token: string,
        executionId: string,
        params?: {
          level?: string;
          step_id?: string;
          offset?: number;
          limit?: number;
          newest_first?: boolean;
        }
      ): Promise<ExecutionLogListResponse> => {
        const searchParams = new URLSearchParams();
        if (params?.level) searchParams.append("level", params.level);
        if (params?.step_id) searchParams.append("step_id", params.step_id);
        if (params?.offset !== undefined) searchParams.append("offset", params.offset.toString());
        if (params?.limit) searchParams.append("limit", params.limit.toString());
        if (params?.newest_first !== undefined) searchParams.append("newest_first", params.newest_first.toString());
        const query = searchParams.toString();
        const response = await fetch(
          `${API_BASE_URL}/api/automation/executions/${executionId}/logs${query ? `?${query}` : ""}`,
          { headers: getAuthHeaders(token) }
        );
        return handleResponse<ExecutionLogListResponse>(response);
      },

      getStreamUrl: (executionId: string, token: string, includeHistory?: boolean): string => {
        const params = new URLSearchParams();
        params.append("token", token);
        if (includeHistory !== undefined) params.append("include_history", includeHistory.toString());
        return `${API_BASE_URL}/api/automation/executions/${executionId}/stream?${params.toString()}`;
      },
    },

    // Cron job endpoints
    cronJobs: {
      list: async (token: string): Promise<CronJobListResponse> => {
        const response = await fetch(`${API_BASE_URL}/api/automation/cron/jobs`, {
          headers: getAuthHeaders(token),
        });
        return handleResponse<CronJobListResponse>(response);
      },

      get: async (token: string, jobType: string): Promise<CronJobResponse> => {
        const response = await fetch(`${API_BASE_URL}/api/automation/cron/jobs/${jobType}`, {
          headers: getAuthHeaders(token),
        });
        return handleResponse<CronJobResponse>(response);
      },

      pause: async (token: string, jobType: string): Promise<CronJobResponse> => {
        const response = await fetch(`${API_BASE_URL}/api/automation/cron/jobs/${jobType}/pause`, {
          method: "POST",
          headers: getAuthHeaders(token),
        });
        return handleResponse<CronJobResponse>(response);
      },

      resume: async (token: string, jobType: string): Promise<CronJobResponse> => {
        const response = await fetch(`${API_BASE_URL}/api/automation/cron/jobs/${jobType}/resume`, {
          method: "POST",
          headers: getAuthHeaders(token),
        });
        return handleResponse<CronJobResponse>(response);
      },

      trigger: async (token: string, jobType: string): Promise<CronJobTriggerResponse> => {
        const response = await fetch(`${API_BASE_URL}/api/automation/cron/jobs/${jobType}/trigger`, {
          method: "POST",
          headers: getAuthHeaders(token),
        });
        return handleResponse<CronJobTriggerResponse>(response);
      },

      updateConfig: async (token: string, jobType: string, config: CronJobConfig): Promise<CronJobResponse> => {
        const response = await fetch(`${API_BASE_URL}/api/automation/cron/jobs/${jobType}/config`, {
          method: "PUT",
          headers: getAuthHeaders(token),
          body: JSON.stringify(config),
        });
        return handleResponse<CronJobResponse>(response);
      },

      getSchedule: async (token: string): Promise<CronJobSchedule> => {
        const response = await fetch(`${API_BASE_URL}/api/automation/cron/schedule`, {
          headers: getAuthHeaders(token),
        });
        return handleResponse<CronJobSchedule>(response);
      },

      updateSchedule: async (token: string, schedule: CronJobSchedule): Promise<CronJobSchedule> => {
        const response = await fetch(`${API_BASE_URL}/api/automation/cron/schedule`, {
          method: "PUT",
          headers: getAuthHeaders(token),
          body: JSON.stringify(schedule),
        });
        return handleResponse<CronJobSchedule>(response);
      },
    },
  },
};

// Error handler for use with TanStack Query
export function handleApiError(error: unknown) {
  if (error instanceof ApiError) {
    toast.error(error.message, {
      description: error.detail || undefined,
    });
    console.error(`API Error [${error.correlationId}]:`, error);
  } else if (error instanceof Error) {
    toast.error("An unexpected error occurred", {
      description: error.message,
    });
    console.error("Unexpected error:", error);
  }
}
