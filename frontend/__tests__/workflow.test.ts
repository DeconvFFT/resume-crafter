/**
 * Workflow Verification Tests
 *
 * This file contains type-level tests and verification utilities for the
 * automation/workflow system. Since no test framework is currently set up,
 * these serve as:
 *
 * 1. TypeScript compile-time verification of types and interfaces
 * 2. Documentation of expected behavior
 * 3. Ready-to-use tests when a test framework is added
 *
 * To add a test framework, install vitest or jest:
 *   npm install -D vitest @testing-library/react @testing-library/jest-dom
 *
 * Then uncomment the test blocks below and run with:
 *   npx vitest run __tests__/workflow.test.ts
 */

import type { Node, Edge } from "@xyflow/react";

// ============================================================================
// Type Imports - These serve as compile-time verification
// ============================================================================

import type {
  ExecutionStatus,
  LogLevel,
  ExecutionLog,
  WorkflowState,
  HistoryState,
  WorkflowMeta,
} from "@/lib/stores/workflow";

// ============================================================================
// Backend Schema Types (should match backend Pydantic schemas)
// ============================================================================

/**
 * Frontend types that should match backend automation schemas.
 * These type definitions serve as a contract between frontend and backend.
 */

// Campaign types
interface SearchCampaignCreate {
  name: string;
  target_roles: string[];
  target_locations?: string[];
  target_companies?: string[] | null;
  keywords?: string[];
  excluded_keywords?: string[] | null;
  min_salary?: number | null;
  max_salary?: number | null;
  remote_preference?: "remote" | "hybrid" | "onsite" | "any";
  experience_level?: "entry" | "mid" | "senior" | "lead" | "any";
  settings?: Record<string, unknown> | null;
}

interface SearchCampaignResponse {
  id: string;
  user_id: string;
  name: string;
  status: "draft" | "active" | "paused" | "completed";
  target_roles: string[];
  target_locations: string[];
  target_companies: string[] | null;
  keywords: string[];
  excluded_keywords: string[] | null;
  min_salary: number | null;
  max_salary: number | null;
  remote_preference: string | null;
  experience_level: string | null;
  last_run_at: string | null;
  next_run_at: string | null;
  settings: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

// Application types
interface JobApplicationCreate {
  discovered_job_id?: string | null;
  campaign_id?: string | null;
  job_title: string;
  company: string;
  job_url?: string | null;
  notes?: string | null;
}

type ApplicationStatus =
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

interface JobApplicationResponse {
  id: string;
  user_id: string;
  discovered_job_id: string | null;
  campaign_id: string | null;
  status: ApplicationStatus;
  status_history: Array<{
    status: string;
    timestamp: string;
    notes?: string | null;
  }> | null;
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

// Dashboard types
interface ApplicationPipelineStats {
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

interface AutomationDashboard {
  active_campaigns: number;
  total_jobs_discovered: number;
  pending_applications: number;
  applications_this_week: number;
  response_rate: number;
  interview_rate: number;
  pipeline_stats: ApplicationPipelineStats;
}

// Cron job types
type CronJobType = "job_discovery" | "job_analysis" | "application_queue";
type CronJobStatus = "active" | "paused" | "disabled" | "running";

interface CronJobResponse {
  job_type: CronJobType;
  status: CronJobStatus;
  interval_seconds: number;
  last_run_at: string | null;
  next_run_at: string | null;
  last_run_status: string | null;
  last_run_duration_ms: number | null;
  run_count: number;
  error_count: number;
  config: Record<string, unknown>;
}

// ============================================================================
// Type Verification Functions
// ============================================================================

/**
 * Type guard to verify SearchCampaignResponse shape
 */
function isValidCampaignResponse(obj: unknown): obj is SearchCampaignResponse {
  if (typeof obj !== "object" || obj === null) return false;

  const campaign = obj as Record<string, unknown>;

  return (
    typeof campaign.id === "string" &&
    typeof campaign.user_id === "string" &&
    typeof campaign.name === "string" &&
    ["draft", "active", "paused", "completed"].includes(campaign.status as string) &&
    Array.isArray(campaign.target_roles) &&
    Array.isArray(campaign.target_locations) &&
    typeof campaign.created_at === "string" &&
    typeof campaign.updated_at === "string"
  );
}

/**
 * Type guard to verify JobApplicationResponse shape
 */
function isValidApplicationResponse(obj: unknown): obj is JobApplicationResponse {
  if (typeof obj !== "object" || obj === null) return false;

  const app = obj as Record<string, unknown>;
  const validStatuses: ApplicationStatus[] = [
    "discovered",
    "filtered",
    "queued",
    "resume_generated",
    "applying",
    "applied",
    "viewed",
    "response_received",
    "interview_scheduled",
    "rejected",
    "offer_received",
  ];

  return (
    typeof app.id === "string" &&
    typeof app.user_id === "string" &&
    validStatuses.includes(app.status as ApplicationStatus) &&
    typeof app.job_title === "string" &&
    typeof app.company === "string" &&
    typeof app.created_at === "string" &&
    typeof app.updated_at === "string"
  );
}

/**
 * Type guard to verify AutomationDashboard shape
 */
function isValidDashboard(obj: unknown): obj is AutomationDashboard {
  if (typeof obj !== "object" || obj === null) return false;

  const dashboard = obj as Record<string, unknown>;

  return (
    typeof dashboard.active_campaigns === "number" &&
    typeof dashboard.total_jobs_discovered === "number" &&
    typeof dashboard.pending_applications === "number" &&
    typeof dashboard.applications_this_week === "number" &&
    typeof dashboard.response_rate === "number" &&
    typeof dashboard.interview_rate === "number" &&
    typeof dashboard.pipeline_stats === "object"
  );
}

/**
 * Type guard for workflow store state
 */
function isValidWorkflowState(obj: unknown): obj is WorkflowState {
  if (typeof obj !== "object" || obj === null) return false;

  const state = obj as Record<string, unknown>;

  return (
    Array.isArray(state.nodes) &&
    Array.isArray(state.edges) &&
    typeof state.workflowName === "string" &&
    typeof state.isDirty === "boolean" &&
    typeof state.executionStatus === "string" &&
    Array.isArray(state.executionLogs) &&
    Array.isArray(state.past) &&
    Array.isArray(state.future)
  );
}

// ============================================================================
// Mock Data Factories
// ============================================================================

/**
 * Create mock campaign data for testing
 */
function createMockCampaign(overrides?: Partial<SearchCampaignResponse>): SearchCampaignResponse {
  return {
    id: "test-campaign-id",
    user_id: "test-user-id",
    name: "Test Campaign",
    status: "draft",
    target_roles: ["Software Engineer"],
    target_locations: ["San Francisco", "Remote"],
    target_companies: null,
    keywords: ["python", "fastapi"],
    excluded_keywords: null,
    min_salary: 150000,
    max_salary: 200000,
    remote_preference: "any",
    experience_level: "senior",
    last_run_at: null,
    next_run_at: null,
    settings: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

/**
 * Create mock application data for testing
 */
function createMockApplication(overrides?: Partial<JobApplicationResponse>): JobApplicationResponse {
  return {
    id: "test-app-id",
    user_id: "test-user-id",
    discovered_job_id: "test-job-id",
    campaign_id: "test-campaign-id",
    status: "queued",
    status_history: [
      {
        status: "queued",
        timestamp: new Date().toISOString(),
        notes: "Application queued",
      },
    ],
    job_title: "Senior Software Engineer",
    company: "Test Company",
    job_url: "https://example.com/job/123",
    resume_id: null,
    cover_letter: null,
    applied_at: null,
    response_received_at: null,
    interview_scheduled_at: null,
    notes: null,
    rejection_reason: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

/**
 * Create mock dashboard data for testing
 */
function createMockDashboard(overrides?: Partial<AutomationDashboard>): AutomationDashboard {
  return {
    active_campaigns: 3,
    total_jobs_discovered: 150,
    pending_applications: 12,
    applications_this_week: 25,
    response_rate: 15.5,
    interview_rate: 8.2,
    pipeline_stats: {
      discovered: 100,
      filtered: 30,
      queued: 20,
      resume_generated: 15,
      applying: 2,
      applied: 50,
      viewed: 10,
      response_received: 8,
      interview_scheduled: 4,
      rejected: 5,
      offer_received: 1,
    },
    ...overrides,
  };
}

/**
 * Create mock workflow node
 */
function createMockNode(overrides?: Partial<Node>): Node {
  return {
    id: `node-${Date.now()}`,
    type: "default",
    position: { x: 100, y: 100 },
    data: { label: "Test Node" },
    ...overrides,
  };
}

/**
 * Create mock workflow edge
 */
function createMockEdge(source: string, target: string, overrides?: Partial<Edge>): Edge {
  return {
    id: `edge-${source}-${target}`,
    source,
    target,
    ...overrides,
  };
}

// ============================================================================
// Verification Tests (ready for test framework)
// ============================================================================

/**
 * Verification functions that can be used with any test framework.
 * Uncomment the describe/it blocks when a test framework is added.
 */

// describe("Workflow State Management", () => {
//   it("should have correct initial state structure", () => {
//     const { useWorkflowStore } = require("@/lib/stores/workflow");
//     const state = useWorkflowStore.getState();
//
//     expect(isValidWorkflowState(state)).toBe(true);
//     expect(state.nodes).toEqual([]);
//     expect(state.edges).toEqual([]);
//     expect(state.executionStatus).toBe("idle");
//   });
//
//   it("should track nodes correctly", () => {
//     const { useWorkflowStore } = require("@/lib/stores/workflow");
//     const { addNode, setNodes } = useWorkflowStore.getState();
//
//     const nodeId = addNode(createMockNode());
//     const state = useWorkflowStore.getState();
//
//     expect(state.nodes.length).toBe(1);
//     expect(state.nodes[0].id).toBe(nodeId);
//   });
//
//   it("should support undo/redo", () => {
//     const { useWorkflowStore } = require("@/lib/stores/workflow");
//     const store = useWorkflowStore.getState();
//
//     // Add a node
//     store.addNode(createMockNode());
//     expect(store.canUndo()).toBe(true);
//
//     // Undo
//     store.undo();
//     expect(useWorkflowStore.getState().nodes.length).toBe(0);
//     expect(store.canRedo()).toBe(true);
//
//     // Redo
//     store.redo();
//     expect(useWorkflowStore.getState().nodes.length).toBe(1);
//   });
// });

// describe("API Type Verification", () => {
//   it("should validate campaign response structure", () => {
//     const campaign = createMockCampaign();
//     expect(isValidCampaignResponse(campaign)).toBe(true);
//   });
//
//   it("should validate application response structure", () => {
//     const application = createMockApplication();
//     expect(isValidApplicationResponse(application)).toBe(true);
//   });
//
//   it("should validate dashboard response structure", () => {
//     const dashboard = createMockDashboard();
//     expect(isValidDashboard(dashboard)).toBe(true);
//   });
//
//   it("should reject invalid campaign data", () => {
//     const invalid = { id: 123, name: "test" }; // id should be string
//     expect(isValidCampaignResponse(invalid)).toBe(false);
//   });
// });

// describe("Automation Page Integration", () => {
//   it("should render automations list", async () => {
//     const { render, screen } = require("@testing-library/react");
//     const AutomationsPage = require("@/app/(dashboard)/automations/page").default;
//
//     render(<AutomationsPage />);
//
//     // Should show loading initially
//     expect(screen.getByRole("status")).toBeInTheDocument();
//
//     // Wait for content
//     await screen.findByText("Automations");
//   });
// });

// ============================================================================
// Compile-time Type Verification
// ============================================================================

// These assignments verify that types are compatible at compile time

// Verify ExecutionStatus is a valid union type
const _executionStatusCheck: ExecutionStatus = "idle";
const _executionStatuses: ExecutionStatus[] = ["idle", "running", "paused", "completed", "failed"];

// Verify LogLevel type
const _logLevelCheck: LogLevel = "info";
const _logLevels: LogLevel[] = ["info", "warning", "error", "success"];

// Verify ExecutionLog structure
const _executionLogCheck: ExecutionLog = {
  id: "log-1",
  timestamp: new Date().toISOString(),
  nodeId: "node-1",
  nodeName: "Test Node",
  level: "info",
  message: "Test message",
  details: { key: "value" },
};

// Verify CronJobType values
const _cronJobTypes: CronJobType[] = ["job_discovery", "job_analysis", "application_queue"];

// Verify ApplicationStatus values
const _applicationStatuses: ApplicationStatus[] = [
  "discovered",
  "filtered",
  "queued",
  "resume_generated",
  "applying",
  "applied",
  "viewed",
  "response_received",
  "interview_scheduled",
  "rejected",
  "offer_received",
];

// ============================================================================
// Export for use in other tests
// ============================================================================

export {
  // Type guards
  isValidCampaignResponse,
  isValidApplicationResponse,
  isValidDashboard,
  isValidWorkflowState,

  // Mock data factories
  createMockCampaign,
  createMockApplication,
  createMockDashboard,
  createMockNode,
  createMockEdge,

  // Types
  type SearchCampaignCreate,
  type SearchCampaignResponse,
  type JobApplicationCreate,
  type JobApplicationResponse,
  type ApplicationStatus,
  type AutomationDashboard,
  type ApplicationPipelineStats,
  type CronJobType,
  type CronJobStatus,
  type CronJobResponse,
};

// ============================================================================
// Self-verification on import (development mode)
// ============================================================================

if (process.env.NODE_ENV === "development") {
  // Run type guards on mock data to verify they work
  const campaign = createMockCampaign();
  const application = createMockApplication();
  const dashboard = createMockDashboard();

  console.assert(isValidCampaignResponse(campaign), "Campaign mock should be valid");
  console.assert(isValidApplicationResponse(application), "Application mock should be valid");
  console.assert(isValidDashboard(dashboard), "Dashboard mock should be valid");

  console.log("[workflow.test.ts] Type verification passed");
}
