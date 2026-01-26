/**
 * SSE hook for real-time execution monitoring.
 *
 * Connects to /api/automation/executions/{id}/stream for real-time updates.
 *
 * Event types:
 * - init: Initial state with existing logs
 * - log: New log entry
 * - step_update: Step status change
 * - status_change: Execution status change
 * - progress: Progress percentage update
 * - done: Execution complete
 * - error: Execution failed
 * - heartbeat: Keep-alive
 */

"use client";

import { useCallback, useState, useRef, useEffect } from "react";
import { useSSE, SSEEvent, SSEConnectionState } from "./useSSE";
import { useQueryClient } from "@tanstack/react-query";
import { executionKeys } from "./useExecutions";
import type {
  ExecutionStatus,
  ExecutionLogEntry,
  ExecutionStepResponse,
  ExecutionDetailResponse,
} from "@/lib/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ============================================================================
// Types
// ============================================================================

export interface ExecutionStreamState {
  status: ExecutionStatus | null;
  progress: number;
  currentStep: string | null;
  completedSteps: number;
  totalSteps: number;
  logs: ExecutionLogEntry[];
  steps: ExecutionStepResponse[];
  error: string | null;
  result: Record<string, unknown> | null;
  startedAt: string | null;
  completedAt: string | null;
  durationMs: number | null;
}

export interface UseExecutionStreamOptions {
  executionId: string | null;
  accessToken: string | null;
  enabled?: boolean;
  includeHistory?: boolean;
  onStatusChange?: (status: ExecutionStatus) => void;
  onProgress?: (progress: number) => void;
  onLog?: (log: ExecutionLogEntry) => void;
  onStepUpdate?: (step: ExecutionStepResponse) => void;
  onComplete?: (result: Record<string, unknown> | null) => void;
  onError?: (message: string) => void;
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useExecutionStream({
  executionId,
  accessToken,
  enabled = true,
  includeHistory = true,
  onStatusChange,
  onProgress,
  onLog,
  onStepUpdate,
  onComplete,
  onError,
}: UseExecutionStreamOptions) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<ExecutionStreamState>({
    status: null,
    progress: 0,
    currentStep: null,
    completedSteps: 0,
    totalSteps: 0,
    logs: [],
    steps: [],
    error: null,
    result: null,
    startedAt: null,
    completedAt: null,
    durationMs: null,
  });

  // Track if we've received the init event
  const initializedRef = useRef(false);

  const handleMessage = useCallback(
    (event: SSEEvent) => {
      const eventData = event.data as Record<string, unknown>;

      switch (event.type) {
        case "init": {
          // Initial state with existing logs and status
          const initData = eventData as {
            status: ExecutionStatus;
            progress: number;
            logs: ExecutionLogEntry[];
            steps?: ExecutionStepResponse[];
            current_step?: string;
            completed_steps?: number;
            total_steps?: number;
            started_at?: string;
          };

          setState((prev) => ({
            ...prev,
            status: initData.status,
            progress: initData.progress || 0,
            logs: initData.logs || [],
            steps: initData.steps || prev.steps,
            currentStep: initData.current_step || null,
            completedSteps: initData.completed_steps || 0,
            totalSteps: initData.total_steps || 0,
            startedAt: initData.started_at || null,
          }));

          initializedRef.current = true;
          break;
        }

        case "log": {
          // New log entry
          const logData = eventData as unknown as ExecutionLogEntry;
          setState((prev) => ({
            ...prev,
            logs: [...prev.logs, logData],
          }));
          onLog?.(logData);
          break;
        }

        case "step_update": {
          // Step status change
          const stepData = eventData as unknown as ExecutionStepResponse;
          setState((prev) => {
            const existingIndex = prev.steps.findIndex((s) => s.id === stepData.id);
            const newSteps =
              existingIndex >= 0
                ? prev.steps.map((s, i) => (i === existingIndex ? stepData : s))
                : [...prev.steps, stepData];

            return {
              ...prev,
              steps: newSteps,
              currentStep: stepData.status === "running" ? stepData.name : prev.currentStep,
              completedSteps:
                stepData.status === "completed"
                  ? prev.completedSteps + 1
                  : prev.completedSteps,
            };
          });
          onStepUpdate?.(stepData);
          break;
        }

        case "status_change": {
          // Execution status change
          const statusData = eventData as { status: ExecutionStatus };
          setState((prev) => ({
            ...prev,
            status: statusData.status,
          }));
          onStatusChange?.(statusData.status);
          break;
        }

        case "progress": {
          // Progress percentage update
          const progressData = eventData as {
            progress: number;
            current_step?: string;
            completed_steps?: number;
          };
          setState((prev) => ({
            ...prev,
            progress: progressData.progress,
            currentStep: progressData.current_step || prev.currentStep,
            completedSteps: progressData.completed_steps ?? prev.completedSteps,
          }));
          onProgress?.(progressData.progress);
          break;
        }

        case "done": {
          // Execution complete
          const doneData = eventData as {
            status: ExecutionStatus;
            result?: Record<string, unknown>;
            completed_at?: string;
            duration_ms?: number;
          };
          setState((prev) => ({
            ...prev,
            status: doneData.status || "completed",
            progress: 100,
            result: doneData.result || null,
            completedAt: doneData.completed_at || new Date().toISOString(),
            durationMs: doneData.duration_ms || null,
          }));
          onComplete?.(doneData.result || null);

          // Invalidate queries to refresh data
          if (executionId) {
            queryClient.invalidateQueries({ queryKey: executionKeys.detail(executionId) });
            queryClient.invalidateQueries({ queryKey: executionKeys.lists() });
          }
          break;
        }

        case "error": {
          // Execution failed
          const errorData = eventData as {
            error: string;
            detail?: string;
            status?: ExecutionStatus;
          };
          setState((prev) => ({
            ...prev,
            status: errorData.status || "failed",
            error: errorData.detail || errorData.error,
          }));
          onError?.(errorData.detail || errorData.error);

          // Invalidate queries to refresh data
          if (executionId) {
            queryClient.invalidateQueries({ queryKey: executionKeys.detail(executionId) });
            queryClient.invalidateQueries({ queryKey: executionKeys.lists() });
          }
          break;
        }

        case "heartbeat": {
          // Keep-alive, no action needed
          break;
        }

        default: {
          // Unknown event type, try to handle gracefully
          console.warn("Unknown SSE event type:", event.type, eventData);
        }
      }
    },
    [executionId, queryClient, onStatusChange, onProgress, onLog, onStepUpdate, onComplete, onError]
  );

  const handleSSEError = useCallback(
    (error: Event) => {
      console.error("SSE connection error:", error);
      setState((prev) => ({
        ...prev,
        error: "Connection lost. Attempting to reconnect...",
      }));
    },
    []
  );

  const handleSSEOpen = useCallback(() => {
    // Clear error on successful connection
    setState((prev) => ({
      ...prev,
      error: null,
    }));
  }, []);

  // Build SSE URL with token as query parameter (EventSource doesn't support headers)
  const sseUrl =
    executionId && accessToken
      ? `${API_BASE}/automation/executions/${executionId}/stream?token=${encodeURIComponent(
          accessToken
        )}&include_history=${includeHistory}`
      : "";

  const { connectionState, reconnect, disconnect } = useSSE({
    url: sseUrl,
    enabled: enabled && !!executionId && !!accessToken,
    onMessage: handleMessage,
    onError: handleSSEError,
    onOpen: handleSSEOpen,
    reconnectAttempts: 5,
    reconnectInterval: 2000,
  });

  // Reset state when execution changes
  useEffect(() => {
    if (executionId) {
      initializedRef.current = false;
      setState({
        status: null,
        progress: 0,
        currentStep: null,
        completedSteps: 0,
        totalSteps: 0,
        logs: [],
        steps: [],
        error: null,
        result: null,
        startedAt: null,
        completedAt: null,
        durationMs: null,
      });
    }
  }, [executionId]);

  const reset = useCallback(() => {
    initializedRef.current = false;
    setState({
      status: null,
      progress: 0,
      currentStep: null,
      completedSteps: 0,
      totalSteps: 0,
      logs: [],
      steps: [],
      error: null,
      result: null,
      startedAt: null,
      completedAt: null,
      durationMs: null,
    });
  }, []);

  return {
    ...state,
    connectionState,
    isConnected: connectionState === "connected",
    isConnecting: connectionState === "connecting",
    isInitialized: initializedRef.current,
    reconnect,
    disconnect,
    reset,
  };
}

// Note: ExecutionStreamState and UseExecutionStreamOptions are already exported
// through the interface declarations above
