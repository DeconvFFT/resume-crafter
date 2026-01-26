/**
 * Auto-generated API types from OpenAPI schema.
 *
 * Run `npm run generate-types` with the backend running to regenerate.
 *
 * This file contains TypeScript types that match the backend API schema.
 */

// ============================================================================
// Common Types
// ============================================================================

export interface ErrorResponse {
  error_code: string;
  message: string;
  detail?: string;
  correlation_id: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page?: number;
  per_page?: number;
}

// ============================================================================
// Auth Types
// ============================================================================

export interface UserCreate {
  email: string;
  password: string;
  full_name?: string;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserResponse {
  id: string;
  email: string;
  full_name: string | null;
  phone: string | null;
  location: string | null;
  linkedin_url: string | null;
  github_url: string | null;
  portfolio_url: string | null;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Profile Types
// ============================================================================

export interface ProfileUpdate {
  full_name?: string;
  phone?: string;
  location?: string;
  linkedin_url?: string;
  github_url?: string;
  portfolio_url?: string;
}

// ============================================================================
// Document Types
// ============================================================================

export type SourceType = "local_file" | "google_doc" | "url";
export type DocumentClass = "resume" | "experience" | "project" | "supporting";
export type ProcessingStatus = "pending" | "processing" | "completed" | "failed";

export interface ProcessingLogEntry {
  timestamp: string;
  step: string;
  status: string;
  message: string;
  details?: {
    classification?: string;
    confidence?: number;
    has_experiences?: boolean;
    has_projects?: boolean;
    detected_entities?: {
      companies?: string[];
      job_titles?: string[];
      skills?: string[];
      dates?: string[];
    };
    experiences?: Array<{
      company: string;
      role: string;
      bullets_count: number;
    }>;
    projects?: Array<{
      name: string;
      technologies: string[];
      bullets_count: number;
    }>;
    text_length?: number;
    preview?: string;
  };
}

export interface DocumentResponse {
  id: string;
  user_id?: string;
  filename: string;
  file_path?: string;
  file_size_bytes?: number;
  mime_type?: string;
  source_type: SourceType;
  source_url?: string;
  document_class?: DocumentClass;
  classification_confidence?: number;
  classification_reasoning?: string;
  verified_by_user: boolean;
  processing_status: ProcessingStatus;
  processing_error?: string;
  processing_logs?: ProcessingLogEntry[];
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: DocumentResponse[];
  total: number;
}

export interface GoogleDocImportRequest {
  google_doc_id: string;
}

export interface DocumentVerifyRequest {
  document_class: DocumentClass;
}

// ============================================================================
// Experience Types
// ============================================================================

export interface ExperienceBullet {
  id: string;
  content: string;
  skills: string[];
  metrics?: string[];
  action_verbs?: string[];
  embedding_id?: string;
}

export interface ExperienceResponse {
  id: string;
  user_id: string;
  company: string;
  role: string;
  location?: string;
  start_date: string;
  end_date?: string;
  description?: string;
  bullets: ExperienceBullet[];
  created_at: string;
  updated_at: string;
}

export interface ExperienceListResponse {
  items: ExperienceResponse[];
  total: number;
}

export interface ExperienceCreate {
  company: string;
  role: string;
  location?: string;
  start_date: string;
  end_date?: string;
  description?: string;
}

export interface ExperienceUpdate {
  company?: string;
  role?: string;
  location?: string;
  start_date?: string;
  end_date?: string;
  description?: string;
}

// ============================================================================
// Project Types
// ============================================================================

export interface ProjectLink {
  id: string;
  url: string;
  title?: string;
  link_type: "github" | "demo" | "paper" | "docs" | "video" | "other";
}

export interface ProjectBullet {
  id: string;
  content: string;
  skills: string[];
  embedding_id?: string;
}

export interface ProjectResponse {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  technologies: string[];
  bullets: ProjectBullet[];
  links: ProjectLink[];
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  items: ProjectResponse[];
  total: number;
}

export interface ProjectCreate {
  name: string;
  description?: string;
  technologies?: string[];
}

// ============================================================================
// Job Types
// ============================================================================

export type RequirementType =
  | "technical_skill"
  | "soft_skill"
  | "experience"
  | "education"
  | "certification"
  | "other";

export interface JobRequirement {
  id: string;
  content: string;
  requirement_type: RequirementType;
  importance_score: number;
  keywords: string[];
  embedding_id?: string;
}

export interface JobResponse {
  id: string;
  user_id: string;
  source_url?: string;
  raw_text?: string;
  company?: string;
  role?: string;
  location?: string;
  salary_range?: string;
  experience_level?: string;
  requirements: JobRequirement[];
  processing_status: ProcessingStatus;
  processing_error?: string;
  created_at: string;
  updated_at: string;
}

export interface JobListResponse {
  items: JobResponse[];
  total: number;
}

export interface JobAnalyzeRequest {
  url?: string;
  text?: string;
}

// ============================================================================
// Resume Match Types
// ============================================================================

export interface MatchItem {
  id: string;
  requirement_id: string;
  requirement_content: string;
  bullet_id: string;
  bullet_content: string;
  bullet_type: "experience" | "project";
  relevance_score: number;
  match_explanation?: string;
  included_in_resume: boolean;
}

export interface ResumeMatchResponse {
  id: string;
  user_id: string;
  job_id: string;
  job_role?: string;
  job_company?: string;
  overall_match_score: number;
  skill_coverage: number;
  experience_relevance: number;
  items: MatchItem[];
  processing_status: ProcessingStatus;
  processing_error?: string;
  created_at: string;
  updated_at: string;
}

export interface MatchListResponse {
  items: ResumeMatchResponse[];
  total: number;
}

export interface MatchCreateRequest {
  job_id: string;
}

export interface MatchItemUpdate {
  included_in_resume: boolean;
}

export interface ResumeGenerateRequest {
  match_id: string;
  format: "json" | "markdown" | "google_doc";
}

export interface ResumeGenerateResponse {
  format: "json" | "markdown" | "google_doc";
  content: string | object;
  url?: string; // For Google Docs
}

// ============================================================================
// Skill Types
// ============================================================================

export type SkillCategory =
  | "programming_language"
  | "framework"
  | "database"
  | "cloud"
  | "devops"
  | "tool"
  | "soft_skill"
  | "methodology"
  | "other";

export type ProficiencyLevel = "beginner" | "intermediate" | "advanced" | "expert";

export interface SkillResponse {
  id: string;
  user_id: string;
  name: string;
  category: SkillCategory;
  proficiency: ProficiencyLevel | null;
  years_of_experience: number | null;
  is_highlighted: boolean;
  display_order: number;
  created_at: string;
  updated_at: string;
}

export interface SkillListResponse {
  items: SkillResponse[];
  total: number;
}

export interface SkillCreate {
  name: string;
  category?: SkillCategory;
  proficiency?: ProficiencyLevel;
  years_of_experience?: number;
  is_highlighted?: boolean;
  display_order?: number;
}

export interface SkillUpdate {
  name?: string;
  category?: SkillCategory;
  proficiency?: ProficiencyLevel;
  years_of_experience?: number;
  is_highlighted?: boolean;
  display_order?: number;
}

export interface SkillCategoryGroup {
  category: string;
  skills: SkillResponse[];
}

// ============================================================================
// Publication Types
// ============================================================================

export type PublicationType =
  | "journal"
  | "conference"
  | "workshop"
  | "preprint"
  | "thesis"
  | "book_chapter"
  | "patent"
  | "other";

export interface PublicationResponse {
  id: string;
  user_id: string;
  source_document_id: string | null;
  title: string;
  authors: string;
  publication_type: PublicationType;
  venue: string | null;
  publisher: string | null;
  publication_date: string | null;
  doi: string | null;
  arxiv_id: string | null;
  url: string | null;
  abstract: string | null;
  citation_count: number | null;
  is_first_author: boolean;
  author_position: number | null;
  display_order: number;
  created_at: string;
  updated_at: string;
}

export interface PublicationListResponse {
  items: PublicationResponse[];
  total: number;
}

export interface PublicationCreate {
  title: string;
  authors: string;
  publication_type?: PublicationType;
  venue?: string;
  publisher?: string;
  publication_date?: string;
  doi?: string;
  arxiv_id?: string;
  url?: string;
  abstract?: string;
  citation_count?: number;
  is_first_author?: boolean;
  author_position?: number;
  display_order?: number;
}

export interface PublicationUpdate {
  title?: string;
  authors?: string;
  publication_type?: PublicationType;
  venue?: string;
  publisher?: string;
  publication_date?: string;
  doi?: string;
  arxiv_id?: string;
  url?: string;
  abstract?: string;
  citation_count?: number;
  is_first_author?: boolean;
  author_position?: number;
  display_order?: number;
}

// ============================================================================
// Task Types
// ============================================================================

export interface TaskStatusResponse {
  id: string;
  task_type: string;
  status: ProcessingStatus;
  progress: number;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Automation Types - Search Campaigns
// ============================================================================

export type CampaignStatus = "draft" | "active" | "paused" | "completed";
export type RemotePreference = "remote" | "hybrid" | "onsite" | "any";
export type ExperienceLevel = "entry" | "mid" | "senior" | "lead" | "any";

export interface SearchCampaignCreate {
  name: string;
  target_roles: string[];
  target_locations?: string[];
  target_companies?: string[];
  keywords?: string[];
  excluded_keywords?: string[];
  min_salary?: number;
  max_salary?: number;
  remote_preference?: RemotePreference;
  experience_level?: ExperienceLevel;
  settings?: Record<string, unknown>;
}

export interface SearchCampaignUpdate {
  name?: string;
  status?: CampaignStatus;
  target_roles?: string[];
  target_locations?: string[];
  target_companies?: string[];
  keywords?: string[];
  excluded_keywords?: string[];
  min_salary?: number;
  max_salary?: number;
  remote_preference?: RemotePreference;
  experience_level?: ExperienceLevel;
  settings?: Record<string, unknown>;
}

export interface SearchCampaignResponse {
  id: string;
  user_id: string;
  name: string;
  status: CampaignStatus;
  target_roles: string[];
  target_locations: string[];
  target_companies: string[] | null;
  keywords: string[];
  excluded_keywords: string[] | null;
  min_salary: number | null;
  max_salary: number | null;
  remote_preference: RemotePreference | null;
  experience_level: ExperienceLevel | null;
  last_run_at: string | null;
  next_run_at: string | null;
  settings: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface SearchCampaignListResponse {
  items: SearchCampaignResponse[];
  total: number;
}

// ============================================================================
// Automation Types - Discovered Jobs
// ============================================================================

export interface DiscoveredJobResponse {
  id: string;
  campaign_id: string;
  user_id: string;
  external_id: string;
  source: string;
  title: string;
  company: string;
  location: string;
  description: string;
  requirements: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  url: string;
  posted_at: string | null;
  match_score: number | null;
  match_reasoning: string | null;
  is_qualified: boolean | null;
  created_at: string;
}

export interface DiscoveredJobListResponse {
  items: DiscoveredJobResponse[];
  total: number;
}

export interface BulkActionRequest {
  job_ids: string[];
  action: "approve" | "reject";
}

export interface BulkActionResponse {
  processed: number;
  failed: number;
  errors?: Array<{ job_id: string; error: string }>;
}

export interface AnalyzeJobResponse {
  job_id: string;
  match_score: number | null;
  match_reasoning: string | null;
  is_qualified: boolean | null;
}

// ============================================================================
// Automation Types - Job Applications
// ============================================================================

export type ApplicationStatus =
  | "discovered"
  | "filtered"
  | "queued"
  | "resume_generated"
  | "applying"
  | "applied"
  | "viewed"
  | "response_received"
  | "interview_scheduled"
  | "rejected"
  | "offer_received";

export interface JobApplicationCreate {
  discovered_job_id?: string;
  campaign_id?: string;
  job_title: string;
  company: string;
  job_url?: string;
  notes?: string;
}

export interface JobApplicationUpdate {
  status?: ApplicationStatus;
  resume_id?: string;
  cover_letter?: string;
  notes?: string;
  rejection_reason?: string;
}

export interface JobApplicationResponse {
  id: string;
  user_id: string;
  discovered_job_id: string | null;
  campaign_id: string | null;
  status: ApplicationStatus;
  status_history: Array<{ status: string; timestamp: string; notes?: string }> | null;
  job_title: string;
  company: string;
  job_url: string | null;
  resume_id: string | null;
  cover_letter: string | null;
  applied_at: string | null;
  response_received_at: string | null;
  interview_scheduled_at: string | null;
  notes: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobApplicationListResponse {
  items: JobApplicationResponse[];
  total: number;
}

export interface QueueApplicationRequest {
  discovered_job_id: string;
  notes?: string;
}

export interface ApplicationStatusUpdateRequest {
  status: ApplicationStatus;
  notes?: string;
}

// ============================================================================
// Automation Types - Dashboard Stats
// ============================================================================

export interface ApplicationPipelineStats {
  discovered: number;
  filtered: number;
  queued: number;
  resume_generated: number;
  applying: number;
  applied: number;
  viewed: number;
  response_received: number;
  interview_scheduled: number;
  rejected: number;
  offer_received: number;
}

export interface AutomationDashboard {
  active_campaigns: number;
  total_jobs_discovered: number;
  pending_applications: number;
  applications_this_week: number;
  response_rate: number;
  interview_rate: number;
  pipeline_stats: ApplicationPipelineStats;
}

// ============================================================================
// Automation Types - Automation Logs
// ============================================================================

export interface AutomationLogResponse {
  id: string;
  user_id: string;
  action_type: string;
  entity_type: string;
  entity_id: string | null;
  status: string;
  details: Record<string, unknown> | null;
  duration_ms: number | null;
  created_at: string;
}

export interface AutomationLogListResponse {
  items: AutomationLogResponse[];
  total: number;
}

// ============================================================================
// Execution Types - Workflow Execution Monitoring
// ============================================================================

export type ExecutionStatus =
  | "pending"
  | "running"
  | "paused"
  | "completed"
  | "failed"
  | "cancelled";

export type ExecutionStepStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "skipped";

export type WorkflowType =
  | "job_discovery"
  | "job_analysis"
  | "resume_generation"
  | "application_processing"
  | "company_research"
  | "contact_discovery"
  | "outreach_generation";

export type LogLevel = "debug" | "info" | "warning" | "error";

export interface ExecutionLogEntry {
  id: string;
  execution_id: string;
  step_id: string | null;
  level: LogLevel;
  message: string;
  data: Record<string, unknown> | null;
  timestamp: string;
}

export interface ExecutionStepResponse {
  id: string;
  execution_id: string;
  name: string;
  description: string | null;
  status: ExecutionStepStatus;
  order_index: number;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  result: Record<string, unknown> | null;
  error_message: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ExecutionResponse {
  id: string;
  user_id: string;
  workflow_type: WorkflowType;
  status: ExecutionStatus;
  campaign_id: string | null;
  entity_id: string | null;
  entity_type: string | null;
  config: Record<string, unknown> | null;
  progress: number;
  current_step: string | null;
  total_steps: number;
  completed_steps: number;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  result: Record<string, unknown> | null;
  error_message: string | null;
  scheduled_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExecutionDetailResponse extends ExecutionResponse {
  steps: ExecutionStepResponse[];
  recent_logs: ExecutionLogEntry[];
}

export interface ExecutionListResponse {
  items: ExecutionResponse[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ExecutionLogListResponse {
  items: ExecutionLogEntry[];
  total: number;
  has_more: boolean;
}

export interface ExecutionCancelRequest {
  reason?: string;
}

export interface ExecutionCancelResponse {
  id: string;
  status: ExecutionStatus;
  cancelled_at: string;
  reason: string | null;
}

export interface ExecutionSSEEvent {
  event_type: string;
  execution_id: string;
  timestamp: string;
  data: Record<string, unknown>;
}

// ============================================================================
// Cron Job Types
// ============================================================================

export type CronJobStatus = "active" | "paused" | "disabled";
export type CronJobType = "job_discovery" | "job_analysis" | "application_queue";

export interface CronJobConfig {
  job_type: CronJobType;
  interval_seconds: number;
  max_retries?: number;
  retry_delay_seconds?: number;
  config?: Record<string, unknown>;
}

export interface CronJobResponse {
  job_type: CronJobType;
  status: CronJobStatus;
  interval_seconds: number;
  last_run_at: string | null;
  next_run_at: string | null;
  last_run_status: string | null;
  last_run_duration_ms: number | null;
  run_count: number;
  error_count: number;
  config: Record<string, unknown> | null;
}

export interface CronJobListResponse {
  items: CronJobResponse[];
}

export interface CronJobSchedule {
  job_discovery_interval_hours: number;
  job_analysis_interval_hours: number;
  application_queue_delay_seconds: number;
  application_queue_batch_size: number;
}
