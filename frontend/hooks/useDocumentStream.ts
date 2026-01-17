"use client";

import { useCallback, useState } from "react";
import { useSSE, SSEEvent, SSEConnectionState } from "./useSSE";

export type ProcessingLogEntry = {
  step: string;
  status: "started" | "completed" | "failed" | "skipped";
  message: string;
  timestamp: string;
  details?: Record<string, unknown>;
};

export type DocumentStreamState = {
  status: "pending" | "processing" | "completed" | "failed" | null;
  logs: ProcessingLogEntry[];
  thinking: string | null;
  isThinking: boolean;
  progress: {
    current: number;
    total: number;
    percentage: number;
  } | null;
  extractionCounts: {
    experiences?: number;
    projects?: number;
    skills?: number;
    publications?: number;
  };
};

export type UseDocumentStreamOptions = {
  documentId: string | null;
  accessToken: string | null;
  enabled?: boolean;
  onStatusChange?: (status: string) => void;
  onComplete?: () => void;
  onError?: (message: string) => void;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useDocumentStream({
  documentId,
  accessToken,
  enabled = true,
  onStatusChange,
  onComplete,
  onError,
}: UseDocumentStreamOptions) {
  const [state, setState] = useState<DocumentStreamState>({
    status: null,
    logs: [],
    thinking: null,
    isThinking: false,
    progress: null,
    extractionCounts: {},
  });

  const handleMessage = useCallback(
    (event: SSEEvent) => {
      switch (event.type) {
        case "init":
          // Initial state with existing logs
          const initData = event.data as {
            status: string;
            logs: ProcessingLogEntry[];
          };
          setState((prev) => ({
            ...prev,
            status: initData.status as DocumentStreamState["status"],
            logs: initData.logs || [],
          }));
          break;

        case "log":
          // New processing log entry
          const logData = event.data as ProcessingLogEntry;
          setState((prev) => ({
            ...prev,
            logs: [...prev.logs, logData],
          }));

          // Extract counts from completed steps
          if (logData.status === "completed" && logData.details) {
            const details = logData.details as Record<string, unknown>;
            if (logData.step === "experience_extraction" && typeof details.count === "number") {
              setState((prev) => ({
                ...prev,
                extractionCounts: { ...prev.extractionCounts, experiences: details.count as number },
              }));
            }
            if (logData.step === "project_extraction" && typeof details.count === "number") {
              setState((prev) => ({
                ...prev,
                extractionCounts: { ...prev.extractionCounts, projects: details.count as number },
              }));
            }
            if (logData.step === "skill_extraction" && typeof details.count === "number") {
              setState((prev) => ({
                ...prev,
                extractionCounts: { ...prev.extractionCounts, skills: details.count as number },
              }));
            }
            if (logData.step === "publication_extraction" && typeof details.count === "number") {
              setState((prev) => ({
                ...prev,
                extractionCounts: { ...prev.extractionCounts, publications: details.count as number },
              }));
            }
          }
          break;

        case "status":
          // Status change
          const statusData = event.data as { status: string };
          setState((prev) => ({
            ...prev,
            status: statusData.status as DocumentStreamState["status"],
          }));
          onStatusChange?.(statusData.status);
          break;

        case "thinking":
          // LLM thinking/reasoning stream
          const thinkingData = event.data as { thinking: string };
          setState((prev) => ({
            ...prev,
            thinking: (prev.thinking || "") + thinkingData.thinking,
            isThinking: true,
          }));
          break;

        case "thinking_complete":
          // Thinking section finished
          setState((prev) => ({
            ...prev,
            isThinking: false,
          }));
          break;

        case "progress":
          // Progress update
          const progressData = event.data as { current: number; total: number };
          setState((prev) => ({
            ...prev,
            progress: {
              current: progressData.current,
              total: progressData.total,
              percentage: Math.round((progressData.current / progressData.total) * 100),
            },
          }));
          break;

        case "done":
          // Processing complete
          setState((prev) => ({
            ...prev,
            status: "completed",
            isThinking: false,
          }));
          onComplete?.();
          break;

        case "error":
          // Error occurred
          const errorData = event.data as { error: string };
          setState((prev) => ({
            ...prev,
            status: "failed",
            isThinking: false,
          }));
          onError?.(errorData.error);
          break;

        case "heartbeat":
          // Keep-alive, no action needed
          break;
      }
    },
    [onStatusChange, onComplete, onError]
  );

  const handleSSEError = useCallback(() => {
    // SSE connection failed, will fall back to polling
    console.warn("SSE connection failed, falling back to polling");
  }, []);

  // Build SSE URL with token as query parameter (EventSource doesn't support headers)
  const sseUrl = documentId && accessToken
    ? `${API_BASE}/sse/documents/${documentId}/stream?token=${encodeURIComponent(accessToken)}`
    : "";

  const { connectionState, reconnect, disconnect } = useSSE({
    url: sseUrl,
    enabled: enabled && !!documentId && !!accessToken,
    onMessage: handleMessage,
    onError: handleSSEError,
    reconnectAttempts: 3,
    reconnectInterval: 2000,
  });

  const reset = useCallback(() => {
    setState({
      status: null,
      logs: [],
      thinking: null,
      isThinking: false,
      progress: null,
      extractionCounts: {},
    });
  }, []);

  return {
    ...state,
    connectionState,
    isConnected: connectionState === "connected",
    reconnect,
    disconnect,
    reset,
  };
}
