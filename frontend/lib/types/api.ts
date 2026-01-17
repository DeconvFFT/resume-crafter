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
