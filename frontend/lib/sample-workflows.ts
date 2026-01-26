/**
 * Sample workflow configurations for demonstrating the workflow builder.
 *
 * These can be loaded into the workflow store to help users understand
 * how the workflow system works.
 */

import type { Node, Edge } from "@xyflow/react";
import type { WorkflowNodeData } from "@/components/workflow/workflow-node";

export interface SampleWorkflow {
  id: string;
  name: string;
  description: string;
  nodes: Node<WorkflowNodeData>[];
  edges: Edge[];
}

/**
 * Sample Workflow 1: Basic Job Application Automation
 *
 * This workflow demonstrates a simple automation flow:
 * 1. Manual Trigger - Start the workflow manually
 * 2. Generate Resume - Create a tailored resume
 * 3. Send Email Draft - Create an outreach email
 */
export const basicJobApplicationWorkflow: SampleWorkflow = {
  id: "sample-basic-job-application",
  name: "Basic Job Application Workflow",
  description: "A simple workflow that generates a tailored resume and creates an outreach email draft",
  nodes: [
    {
      id: "trigger-manual",
      type: "workflowNode",
      position: { x: 100, y: 200 },
      data: {
        type: "trigger",
        title: "Manual Trigger",
        description: "Click Run to start this workflow",
      },
    },
    {
      id: "action-generate-resume",
      type: "workflowNode",
      position: { x: 400, y: 200 },
      data: {
        type: "action",
        title: "Generate Resume",
        description: "Creates a resume tailored to the job requirements",
      },
    },
    {
      id: "action-send-email",
      type: "workflowNode",
      position: { x: 700, y: 200 },
      data: {
        type: "action",
        title: "Send Email Draft",
        description: "Creates a professional outreach email draft",
      },
    },
    {
      id: "output-notify",
      type: "workflowNode",
      position: { x: 1000, y: 200 },
      data: {
        type: "output",
        title: "Notify User",
        description: "Sends notification when complete",
      },
    },
  ],
  edges: [
    {
      id: "edge-1",
      source: "trigger-manual",
      target: "action-generate-resume",
      type: "workflowEdge",
    },
    {
      id: "edge-2",
      source: "action-generate-resume",
      target: "action-send-email",
      type: "workflowEdge",
    },
    {
      id: "edge-3",
      source: "action-send-email",
      target: "output-notify",
      type: "workflowEdge",
    },
  ],
};

/**
 * Sample Workflow 2: New Job Alert with Filtering
 *
 * This workflow demonstrates conditional branching:
 * 1. New Job Found trigger
 * 2. Filter based on match score
 * 3. High match: Generate resume and apply
 * 4. Low match: Save for later review
 */
export const jobAlertWithFilteringWorkflow: SampleWorkflow = {
  id: "sample-job-alert-filtering",
  name: "Job Alert with Smart Filtering",
  description: "Automatically processes new job postings and routes them based on match score",
  nodes: [
    {
      id: "trigger-new-job",
      type: "workflowNode",
      position: { x: 100, y: 200 },
      data: {
        type: "trigger",
        title: "New Job Found",
        description: "Triggers when a matching job is discovered",
      },
    },
    {
      id: "logic-filter",
      type: "workflowNode",
      position: { x: 400, y: 200 },
      data: {
        type: "condition",
        title: "Filter by Match Score",
        description: "Route based on 70% match threshold",
      },
    },
    {
      id: "action-generate-resume",
      type: "workflowNode",
      position: { x: 700, y: 100 },
      data: {
        type: "action",
        title: "Generate Resume",
        description: "Tailored resume for high-match jobs",
      },
    },
    {
      id: "output-apply",
      type: "workflowNode",
      position: { x: 1000, y: 100 },
      data: {
        type: "output",
        title: "Apply to Job",
        description: "Queue application for review",
      },
    },
    {
      id: "output-save-draft",
      type: "workflowNode",
      position: { x: 700, y: 300 },
      data: {
        type: "output",
        title: "Save Draft",
        description: "Save for later review",
      },
    },
  ],
  edges: [
    {
      id: "edge-1",
      source: "trigger-new-job",
      target: "logic-filter",
      type: "workflowEdge",
    },
    {
      id: "edge-2-true",
      source: "logic-filter",
      target: "action-generate-resume",
      sourceHandle: "true",
      type: "workflowEdge",
    },
    {
      id: "edge-3",
      source: "action-generate-resume",
      target: "output-apply",
      type: "workflowEdge",
    },
    {
      id: "edge-2-false",
      source: "logic-filter",
      target: "output-save-draft",
      sourceHandle: "false",
      type: "workflowEdge",
    },
  ],
};

/**
 * Sample Workflow 3: Full Application Pipeline
 *
 * A comprehensive workflow showing the complete automation:
 * 1. Scheduled trigger (runs every 4 hours)
 * 2. Filter qualified jobs
 * 3. Generate tailored resume
 * 4. Fill application form
 * 5. Send outreach email
 * 6. Notify user
 */
export const fullApplicationPipelineWorkflow: SampleWorkflow = {
  id: "sample-full-pipeline",
  name: "Full Application Pipeline",
  description: "Complete end-to-end job application automation with scheduled execution",
  nodes: [
    {
      id: "trigger-schedule",
      type: "workflowNode",
      position: { x: 50, y: 200 },
      data: {
        type: "trigger",
        title: "Schedule",
        description: "Runs every 4 hours to check for new jobs",
      },
    },
    {
      id: "logic-condition",
      type: "workflowNode",
      position: { x: 300, y: 200 },
      data: {
        type: "condition",
        title: "Condition",
        description: "Check if job meets criteria",
      },
    },
    {
      id: "action-resume",
      type: "workflowNode",
      position: { x: 550, y: 120 },
      data: {
        type: "action",
        title: "Generate Resume",
        description: "Create tailored resume",
      },
    },
    {
      id: "action-fill-app",
      type: "workflowNode",
      position: { x: 800, y: 120 },
      data: {
        type: "action",
        title: "Fill Application",
        description: "Auto-fill application form",
      },
    },
    {
      id: "action-email",
      type: "workflowNode",
      position: { x: 1050, y: 120 },
      data: {
        type: "action",
        title: "Send Email Draft",
        description: "Create networking outreach",
      },
    },
    {
      id: "output-notify",
      type: "workflowNode",
      position: { x: 1300, y: 120 },
      data: {
        type: "output",
        title: "Notify User",
        description: "Alert when ready for review",
      },
    },
    {
      id: "output-skip",
      type: "workflowNode",
      position: { x: 550, y: 300 },
      data: {
        type: "output",
        title: "Save Draft",
        description: "Save unqualified jobs for later",
      },
    },
  ],
  edges: [
    {
      id: "edge-1",
      source: "trigger-schedule",
      target: "logic-condition",
      type: "workflowEdge",
    },
    {
      id: "edge-2-true",
      source: "logic-condition",
      target: "action-resume",
      sourceHandle: "true",
      type: "workflowEdge",
    },
    {
      id: "edge-3",
      source: "action-resume",
      target: "action-fill-app",
      type: "workflowEdge",
    },
    {
      id: "edge-4",
      source: "action-fill-app",
      target: "action-email",
      type: "workflowEdge",
    },
    {
      id: "edge-5",
      source: "action-email",
      target: "output-notify",
      type: "workflowEdge",
    },
    {
      id: "edge-2-false",
      source: "logic-condition",
      target: "output-skip",
      sourceHandle: "false",
      type: "workflowEdge",
    },
  ],
};

/**
 * All sample workflows
 */
export const sampleWorkflows: SampleWorkflow[] = [
  basicJobApplicationWorkflow,
  jobAlertWithFilteringWorkflow,
  fullApplicationPipelineWorkflow,
];

/**
 * Get a sample workflow by ID
 */
export function getSampleWorkflow(id: string): SampleWorkflow | undefined {
  return sampleWorkflows.find((w) => w.id === id);
}

/**
 * Get the recommended sample workflow for new users
 */
export function getRecommendedSampleWorkflow(): SampleWorkflow {
  return basicJobApplicationWorkflow;
}
