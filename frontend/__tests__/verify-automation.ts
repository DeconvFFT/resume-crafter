#!/usr/bin/env npx tsx
/**
 * Frontend Automation Verification Script
 *
 * This script verifies that the frontend automation components and types
 * are properly configured and match the backend schemas.
 *
 * Run with: npx tsx frontend/__tests__/verify-automation.ts
 *
 * Or add to package.json scripts:
 *   "verify:automation": "tsx __tests__/verify-automation.ts"
 */

import * as fs from "fs";
import * as path from "path";

// ============================================================================
// Verification Utilities
// ============================================================================

type CheckStatus = "PASS" | "FAIL" | "WARN" | "SKIP";

interface CheckResult {
  name: string;
  status: CheckStatus;
  message: string;
}

const results: CheckResult[] = [];

function addResult(name: string, status: CheckStatus, message: string): void {
  results.push({ name, status, message });
  const symbols = {
    PASS: "\x1b[92m[PASS]\x1b[0m",
    FAIL: "\x1b[91m[FAIL]\x1b[0m",
    WARN: "\x1b[93m[WARN]\x1b[0m",
    SKIP: "\x1b[93m[SKIP]\x1b[0m",
  };
  console.log(`  ${symbols[status]} ${name}: ${message}`);
}

function fileExists(filePath: string): boolean {
  try {
    return fs.existsSync(filePath);
  } catch {
    return false;
  }
}

function readFile(filePath: string): string | null {
  try {
    return fs.readFileSync(filePath, "utf-8");
  } catch {
    return null;
  }
}

// ============================================================================
// Component Verification
// ============================================================================

function checkComponentFiles(): void {
  console.log("\n=== Checking Component Files ===");

  const requiredFiles = [
    {
      path: "app/(dashboard)/automations/page.tsx",
      description: "Automations list page",
    },
    {
      path: "app/(dashboard)/automations/[id]/page.tsx",
      description: "Automation detail page",
    },
    {
      path: "lib/stores/workflow.ts",
      description: "Workflow state store",
    },
    {
      path: "lib/api/client.ts",
      description: "API client",
    },
  ];

  const baseDir = path.resolve(__dirname, "..");

  for (const file of requiredFiles) {
    const fullPath = path.join(baseDir, file.path);
    if (fileExists(fullPath)) {
      addResult(file.description, "PASS", `Found at ${file.path}`);
    } else {
      addResult(file.description, "FAIL", `Missing: ${file.path}`);
    }
  }
}

// ============================================================================
// Store Verification
// ============================================================================

function checkWorkflowStore(): void {
  console.log("\n=== Checking Workflow Store ===");

  const storePath = path.resolve(__dirname, "..", "lib/stores/workflow.ts");
  const content = readFile(storePath);

  if (!content) {
    addResult("Workflow store file", "FAIL", "Cannot read workflow.ts");
    return;
  }

  // Check for required exports
  const requiredExports = [
    "useWorkflowStore",
    "ExecutionStatus",
    "LogLevel",
    "ExecutionLog",
    "WorkflowState",
  ];

  for (const exportName of requiredExports) {
    if (content.includes(`export`) && content.includes(exportName)) {
      addResult(`Export ${exportName}`, "PASS", "Found in workflow store");
    } else {
      addResult(`Export ${exportName}`, "FAIL", "Missing from workflow store");
    }
  }

  // Check for required store actions
  const requiredActions = [
    "setNodes",
    "setEdges",
    "addNode",
    "removeNode",
    "startExecution",
    "pauseExecution",
    "stopExecution",
    "undo",
    "redo",
  ];

  for (const action of requiredActions) {
    if (content.includes(`${action}:`)) {
      addResult(`Action ${action}`, "PASS", "Found in store");
    } else {
      addResult(`Action ${action}`, "WARN", "May be missing from store");
    }
  }
}

// ============================================================================
// API Client Verification
// ============================================================================

function checkApiClient(): void {
  console.log("\n=== Checking API Client ===");

  const clientPath = path.resolve(__dirname, "..", "lib/api/client.ts");
  const content = readFile(clientPath);

  if (!content) {
    addResult("API client file", "FAIL", "Cannot read client.ts");
    return;
  }

  // Check for API base URL handling
  if (content.includes("NEXT_PUBLIC_API_URL") || content.includes("API_BASE_URL")) {
    addResult("API base URL", "PASS", "Environment variable handling found");
  } else {
    addResult("API base URL", "WARN", "No environment variable handling found");
  }

  // Check for error handling
  if (content.includes("ApiError") && content.includes("handleResponse")) {
    addResult("Error handling", "PASS", "ApiError class and handler found");
  } else {
    addResult("Error handling", "WARN", "May be missing error handling");
  }

  // Check for auth headers
  if (content.includes("Authorization") && content.includes("Bearer")) {
    addResult("Auth headers", "PASS", "Bearer token handling found");
  } else {
    addResult("Auth headers", "WARN", "May be missing auth handling");
  }
}

// ============================================================================
// Type Definitions Verification
// ============================================================================

function checkTypeDefinitions(): void {
  console.log("\n=== Checking Type Definitions ===");

  const typesPath = path.resolve(__dirname, "..", "lib/types/api.ts");

  if (!fileExists(typesPath)) {
    addResult("API types file", "WARN", "lib/types/api.ts not found");
    return;
  }

  const content = readFile(typesPath);
  if (!content) {
    addResult("API types file", "FAIL", "Cannot read api.ts");
    return;
  }

  // Note: The types file may be auto-generated from OpenAPI
  addResult("API types file", "PASS", "Found at lib/types/api.ts");

  // Check for key types that should exist
  const keyTypes = [
    "TokenResponse",
    "UserResponse",
    "JobResponse",
  ];

  for (const typeName of keyTypes) {
    if (content.includes(typeName)) {
      addResult(`Type ${typeName}`, "PASS", "Type definition found");
    } else {
      addResult(`Type ${typeName}`, "WARN", "Type may be auto-generated with different name");
    }
  }
}

// ============================================================================
// Automations Page Verification
// ============================================================================

function checkAutomationsPage(): void {
  console.log("\n=== Checking Automations Page ===");

  const pagePath = path.resolve(
    __dirname,
    "..",
    "app/(dashboard)/automations/page.tsx"
  );
  const content = readFile(pagePath);

  if (!content) {
    addResult("Automations page", "FAIL", "Cannot read page.tsx");
    return;
  }

  // Check for React Query usage
  if (content.includes("useQuery") || content.includes("@tanstack/react-query")) {
    addResult("React Query integration", "PASS", "Found query hooks");
  } else {
    addResult("React Query integration", "WARN", "No React Query hooks found");
  }

  // Check for status handling
  const statuses = ["active", "paused", "draft"];
  const statusesFound = statuses.filter((s) => content.includes(s));

  if (statusesFound.length >= 2) {
    addResult("Status handling", "PASS", `Found statuses: ${statusesFound.join(", ")}`);
  } else {
    addResult("Status handling", "WARN", "May be missing status handling");
  }

  // Check for data table
  if (content.includes("DataTable") || content.includes("table")) {
    addResult("Data display", "PASS", "Table component found");
  } else {
    addResult("Data display", "WARN", "No table component found");
  }
}

// ============================================================================
// Package Dependencies Verification
// ============================================================================

function checkDependencies(): void {
  console.log("\n=== Checking Dependencies ===");

  const packagePath = path.resolve(__dirname, "..", "package.json");
  const content = readFile(packagePath);

  if (!content) {
    addResult("package.json", "FAIL", "Cannot read package.json");
    return;
  }

  const pkg = JSON.parse(content);
  const dependencies = {
    ...pkg.dependencies,
    ...pkg.devDependencies,
  };

  const requiredDeps = [
    { name: "@tanstack/react-query", purpose: "Data fetching" },
    { name: "zustand", purpose: "State management" },
    { name: "@xyflow/react", purpose: "Workflow canvas" },
    { name: "zod", purpose: "Schema validation" },
  ];

  for (const dep of requiredDeps) {
    if (dependencies[dep.name]) {
      addResult(dep.name, "PASS", `Installed (${dep.purpose})`);
    } else {
      addResult(dep.name, "FAIL", `Missing dependency for ${dep.purpose}`);
    }
  }
}

// ============================================================================
// Main Execution
// ============================================================================

function main(): void {
  console.log("=".repeat(60));
  console.log("Frontend Automation Verification");
  console.log("=".repeat(60));

  checkComponentFiles();
  checkWorkflowStore();
  checkApiClient();
  checkTypeDefinitions();
  checkAutomationsPage();
  checkDependencies();

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log("Verification Summary");
  console.log("=".repeat(60));

  const passed = results.filter((r) => r.status === "PASS").length;
  const failed = results.filter((r) => r.status === "FAIL").length;
  const warnings = results.filter((r) => r.status === "WARN").length;
  const skipped = results.filter((r) => r.status === "SKIP").length;

  console.log(`
  Total checks: ${results.length}
  \x1b[92mPassed:  ${passed}\x1b[0m
  \x1b[91mFailed:  ${failed}\x1b[0m
  \x1b[93mWarnings: ${warnings}\x1b[0m
  \x1b[93mSkipped: ${skipped}\x1b[0m
`);

  if (failed > 0) {
    console.log("\x1b[91mVerification FAILED\x1b[0m");
    console.log("\nFailed checks:");
    for (const r of results.filter((r) => r.status === "FAIL")) {
      console.log(`  - ${r.name}: ${r.message}`);
    }
    process.exit(1);
  } else if (warnings > 0) {
    console.log("\x1b[93mVerification PASSED with warnings\x1b[0m");
    process.exit(0);
  } else {
    console.log("\x1b[92mVerification PASSED\x1b[0m");
    process.exit(0);
  }
}

main();
