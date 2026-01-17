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
