/**
 * Workflow state management store using Zustand.
 *
 * Manages state for an N8N-style workflow builder including:
 * - Canvas state (nodes and edges)
 * - Selection state
 * - Workflow metadata
 * - Execution state
 * - Undo/redo history
 */

import { create } from "zustand";
import { persist, subscribeWithSelector } from "zustand/middleware";
import type { Node, Edge } from "@xyflow/react";

// ============================================================================
// Types
// ============================================================================

export type ExecutionStatus =
  | "idle"
  | "running"
  | "paused"
  | "completed"
  | "failed";

export type LogLevel = "info" | "warning" | "error" | "success";

export interface ExecutionLog {
  id: string;
  timestamp: string;
  nodeId: string | null;
  nodeName: string | null;
  level: LogLevel;
  message: string;
  details?: Record<string, unknown>;
}

export interface HistoryState {
  nodes: Node[];
  edges: Edge[];
}

export interface WorkflowMeta {
  workflowName?: string;
  workflowDescription?: string;
}

export interface WorkflowState {
  // Canvas state
  nodes: Node[];
  edges: Edge[];

  // Selection
  selectedNodeId: string | null;
  selectedEdgeId: string | null;

  // Workflow metadata
  workflowId: string | null;
  workflowName: string;
  workflowDescription: string;
  isDirty: boolean;

  // Execution state
  executionStatus: ExecutionStatus;
  executionLogs: ExecutionLog[];
  currentExecutingNodeId: string | null;

  // History for undo/redo
  past: HistoryState[];
  future: HistoryState[];

  // Hydration state
  _hasHydrated: boolean;
}

// ============================================================================
// Constants
// ============================================================================

const MAX_HISTORY_SIZE = 50;
const STORAGE_KEY = "workflow-draft";

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Generate a unique ID for nodes, edges, and logs
 */
const generateId = (): string => {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
};

/**
 * Create a snapshot of the current canvas state for history
 */
const createSnapshot = (nodes: Node[], edges: Edge[]): HistoryState => ({
  nodes: JSON.parse(JSON.stringify(nodes)),
  edges: JSON.parse(JSON.stringify(edges)),
});

/**
 * Add a state to history, respecting the max history size
 */
const addToHistory = (
  past: HistoryState[],
  snapshot: HistoryState
): HistoryState[] => {
  const newPast = [...past, snapshot];
  if (newPast.length > MAX_HISTORY_SIZE) {
    return newPast.slice(-MAX_HISTORY_SIZE);
  }
  return newPast;
};

// ============================================================================
// Initial State
// ============================================================================

const initialState: Omit<WorkflowState, keyof WorkflowActions> = {
  // Canvas state
  nodes: [],
  edges: [],

  // Selection
  selectedNodeId: null,
  selectedEdgeId: null,

  // Workflow metadata
  workflowId: null,
  workflowName: "Untitled Workflow",
  workflowDescription: "",
  isDirty: false,

  // Execution state
  executionStatus: "idle",
  executionLogs: [],
  currentExecutingNodeId: null,

  // History
  past: [],
  future: [],

  // Hydration
  _hasHydrated: false,
};

// ============================================================================
// Actions Interface
// ============================================================================

interface WorkflowActions {
  // Hydration
  setHasHydrated: (state: boolean) => void;

  // Canvas updates
  setNodes: (nodes: Node[]) => void;
  setEdges: (edges: Edge[]) => void;

  // Node CRUD
  addNode: (node: Omit<Node, "id"> & { id?: string }) => string;
  removeNode: (nodeId: string) => void;
  updateNode: (nodeId: string, updates: Partial<Node>) => void;

  // Edge CRUD
  addEdge: (edge: Omit<Edge, "id"> & { id?: string }) => string;
  removeEdge: (edgeId: string) => void;

  // Selection
  selectNode: (nodeId: string | null) => void;
  selectEdge: (edgeId: string | null) => void;
  clearSelection: () => void;

  // Workflow metadata
  setWorkflowMeta: (meta: WorkflowMeta) => void;
  setWorkflowId: (id: string | null) => void;
  markClean: () => void;

  // History (undo/redo)
  undo: () => void;
  redo: () => void;
  saveToHistory: () => void;

  // Execution control
  startExecution: () => void;
  pauseExecution: () => void;
  stopExecution: () => void;
  setCurrentExecutingNode: (nodeId: string | null) => void;
  setExecutionStatus: (status: ExecutionStatus) => void;

  // Execution logging
  addExecutionLog: (log: Omit<ExecutionLog, "id" | "timestamp">) => void;
  clearExecutionLogs: () => void;

  // Persistence
  loadWorkflow: (workflow: {
    id?: string;
    name: string;
    description?: string;
    nodes: Node[];
    edges: Edge[];
  }) => void;
  saveWorkflow: () => {
    id: string | null;
    name: string;
    description: string;
    nodes: Node[];
    edges: Edge[];
  };
  resetWorkflow: () => void;

  // Computed values (implemented as getters in store)
  canUndo: () => boolean;
  canRedo: () => boolean;
  hasUnsavedChanges: () => boolean;
  getSelectedNode: () => Node | undefined;
  getSelectedEdge: () => Edge | undefined;
}

// ============================================================================
// Store Definition
// ============================================================================

export const useWorkflowStore = create<WorkflowState & WorkflowActions>()(
  subscribeWithSelector(
    persist(
      (set, get) => ({
        ...initialState,

        // ====================================================================
        // Hydration
        // ====================================================================

        setHasHydrated: (state) => set({ _hasHydrated: state }),

        // ====================================================================
        // Canvas Updates
        // ====================================================================

        setNodes: (nodes) => {
          const state = get();
          const snapshot = createSnapshot(state.nodes, state.edges);

          set({
            nodes,
            isDirty: true,
            past: addToHistory(state.past, snapshot),
            future: [],
          });
        },

        setEdges: (edges) => {
          const state = get();
          const snapshot = createSnapshot(state.nodes, state.edges);

          set({
            edges,
            isDirty: true,
            past: addToHistory(state.past, snapshot),
            future: [],
          });
        },

        // ====================================================================
        // Node CRUD
        // ====================================================================

        addNode: (nodeData) => {
          const state = get();
          const snapshot = createSnapshot(state.nodes, state.edges);
          const id = nodeData.id || generateId();

          const newNode: Node = {
            ...nodeData,
            id,
          };

          set({
            nodes: [...state.nodes, newNode],
            isDirty: true,
            past: addToHistory(state.past, snapshot),
            future: [],
          });

          return id;
        },

        removeNode: (nodeId) => {
          const state = get();
          const snapshot = createSnapshot(state.nodes, state.edges);

          // Remove node and any connected edges
          const newNodes = state.nodes.filter((node) => node.id !== nodeId);
          const newEdges = state.edges.filter(
            (edge) => edge.source !== nodeId && edge.target !== nodeId
          );

          set({
            nodes: newNodes,
            edges: newEdges,
            isDirty: true,
            // Clear selection if the removed node was selected
            selectedNodeId:
              state.selectedNodeId === nodeId ? null : state.selectedNodeId,
            past: addToHistory(state.past, snapshot),
            future: [],
          });
        },

        updateNode: (nodeId, updates) => {
          const state = get();
          const snapshot = createSnapshot(state.nodes, state.edges);

          const newNodes = state.nodes.map((node) => {
            if (node.id === nodeId) {
              return {
                ...node,
                ...updates,
                data: {
                  ...node.data,
                  ...(updates.data || {}),
                },
              };
            }
            return node;
          });

          set({
            nodes: newNodes,
            isDirty: true,
            past: addToHistory(state.past, snapshot),
            future: [],
          });
        },

        // ====================================================================
        // Edge CRUD
        // ====================================================================

        addEdge: (edgeData) => {
          const state = get();
          const snapshot = createSnapshot(state.nodes, state.edges);
          const id = edgeData.id || generateId();

          const newEdge: Edge = {
            ...edgeData,
            id,
          };

          // Prevent duplicate edges
          const existingEdge = state.edges.find(
            (e) =>
              e.source === newEdge.source &&
              e.target === newEdge.target &&
              e.sourceHandle === newEdge.sourceHandle &&
              e.targetHandle === newEdge.targetHandle
          );

          if (existingEdge) {
            return existingEdge.id;
          }

          set({
            edges: [...state.edges, newEdge],
            isDirty: true,
            past: addToHistory(state.past, snapshot),
            future: [],
          });

          return id;
        },

        removeEdge: (edgeId) => {
          const state = get();
          const snapshot = createSnapshot(state.nodes, state.edges);

          set({
            edges: state.edges.filter((edge) => edge.id !== edgeId),
            isDirty: true,
            // Clear selection if the removed edge was selected
            selectedEdgeId:
              state.selectedEdgeId === edgeId ? null : state.selectedEdgeId,
            past: addToHistory(state.past, snapshot),
            future: [],
          });
        },

        // ====================================================================
        // Selection
        // ====================================================================

        selectNode: (nodeId) => {
          set({
            selectedNodeId: nodeId,
            selectedEdgeId: null, // Clear edge selection when selecting a node
          });
        },

        selectEdge: (edgeId) => {
          set({
            selectedEdgeId: edgeId,
            selectedNodeId: null, // Clear node selection when selecting an edge
          });
        },

        clearSelection: () => {
          set({
            selectedNodeId: null,
            selectedEdgeId: null,
          });
        },

        // ====================================================================
        // Workflow Metadata
        // ====================================================================

        setWorkflowMeta: (meta) => {
          set({
            ...(meta.workflowName !== undefined && {
              workflowName: meta.workflowName,
            }),
            ...(meta.workflowDescription !== undefined && {
              workflowDescription: meta.workflowDescription,
            }),
            isDirty: true,
          });
        },

        setWorkflowId: (id) => {
          set({ workflowId: id });
        },

        markClean: () => {
          set({ isDirty: false });
        },

        // ====================================================================
        // History (Undo/Redo)
        // ====================================================================

        saveToHistory: () => {
          const state = get();
          const snapshot = createSnapshot(state.nodes, state.edges);

          set({
            past: addToHistory(state.past, snapshot),
            future: [],
          });
        },

        undo: () => {
          const state = get();

          if (state.past.length === 0) {
            return;
          }

          const previous = state.past[state.past.length - 1];
          const newPast = state.past.slice(0, -1);
          const currentSnapshot = createSnapshot(state.nodes, state.edges);

          set({
            nodes: previous.nodes,
            edges: previous.edges,
            past: newPast,
            future: [currentSnapshot, ...state.future].slice(0, MAX_HISTORY_SIZE),
            isDirty: true,
          });
        },

        redo: () => {
          const state = get();

          if (state.future.length === 0) {
            return;
          }

          const next = state.future[0];
          const newFuture = state.future.slice(1);
          const currentSnapshot = createSnapshot(state.nodes, state.edges);

          set({
            nodes: next.nodes,
            edges: next.edges,
            past: [...state.past, currentSnapshot].slice(-MAX_HISTORY_SIZE),
            future: newFuture,
            isDirty: true,
          });
        },

        // ====================================================================
        // Execution Control
        // ====================================================================

        startExecution: () => {
          set({
            executionStatus: "running",
            executionLogs: [],
            currentExecutingNodeId: null,
          });
        },

        pauseExecution: () => {
          const state = get();
          if (state.executionStatus === "running") {
            set({ executionStatus: "paused" });
          }
        },

        stopExecution: () => {
          set({
            executionStatus: "idle",
            currentExecutingNodeId: null,
          });
        },

        setCurrentExecutingNode: (nodeId) => {
          set({ currentExecutingNodeId: nodeId });
        },

        setExecutionStatus: (status) => {
          set({ executionStatus: status });
        },

        // ====================================================================
        // Execution Logging
        // ====================================================================

        addExecutionLog: (log) => {
          const state = get();

          const newLog: ExecutionLog = {
            ...log,
            id: generateId(),
            timestamp: new Date().toISOString(),
          };

          set({
            executionLogs: [...state.executionLogs, newLog],
          });
        },

        clearExecutionLogs: () => {
          set({ executionLogs: [] });
        },

        // ====================================================================
        // Persistence
        // ====================================================================

        loadWorkflow: (workflow) => {
          set({
            workflowId: workflow.id || null,
            workflowName: workflow.name,
            workflowDescription: workflow.description || "",
            nodes: workflow.nodes,
            edges: workflow.edges,
            isDirty: false,
            // Clear history when loading a new workflow
            past: [],
            future: [],
            // Clear selection and execution state
            selectedNodeId: null,
            selectedEdgeId: null,
            executionStatus: "idle",
            executionLogs: [],
            currentExecutingNodeId: null,
          });
        },

        saveWorkflow: () => {
          const state = get();

          // Mark as clean after saving
          set({ isDirty: false });

          return {
            id: state.workflowId,
            name: state.workflowName,
            description: state.workflowDescription,
            nodes: state.nodes,
            edges: state.edges,
          };
        },

        resetWorkflow: () => {
          set({
            ...initialState,
            _hasHydrated: true, // Keep hydrated state
          });
        },

        // ====================================================================
        // Computed Values
        // ====================================================================

        canUndo: () => {
          return get().past.length > 0;
        },

        canRedo: () => {
          return get().future.length > 0;
        },

        hasUnsavedChanges: () => {
          return get().isDirty;
        },

        getSelectedNode: () => {
          const state = get();
          if (!state.selectedNodeId) return undefined;
          return state.nodes.find((node) => node.id === state.selectedNodeId);
        },

        getSelectedEdge: () => {
          const state = get();
          if (!state.selectedEdgeId) return undefined;
          return state.edges.find((edge) => edge.id === state.selectedEdgeId);
        },
      }),
      {
        name: STORAGE_KEY,
        // Only persist specific parts of the state
        partialize: (state) => ({
          nodes: state.nodes,
          edges: state.edges,
          workflowId: state.workflowId,
          workflowName: state.workflowName,
          workflowDescription: state.workflowDescription,
          // Do not persist: isDirty, selection, execution state, history
        }),
        onRehydrateStorage: () => (state, error) => {
          if (state) {
            state.setHasHydrated(true);
          } else {
            useWorkflowStore.setState({ _hasHydrated: true });
          }
        },
      }
    )
  )
);

// ============================================================================
// Selectors for Optimized Re-renders
// ============================================================================

/**
 * Selector for nodes only
 */
export const selectNodes = (state: WorkflowState) => state.nodes;

/**
 * Selector for edges only
 */
export const selectEdges = (state: WorkflowState) => state.edges;

/**
 * Selector for selection state
 */
export const selectSelection = (state: WorkflowState) => ({
  selectedNodeId: state.selectedNodeId,
  selectedEdgeId: state.selectedEdgeId,
});

/**
 * Selector for workflow metadata
 */
export const selectWorkflowMeta = (state: WorkflowState) => ({
  workflowId: state.workflowId,
  workflowName: state.workflowName,
  workflowDescription: state.workflowDescription,
  isDirty: state.isDirty,
});

/**
 * Selector for execution state
 */
export const selectExecutionState = (state: WorkflowState) => ({
  executionStatus: state.executionStatus,
  executionLogs: state.executionLogs,
  currentExecutingNodeId: state.currentExecutingNodeId,
});

/**
 * Selector for history state (undo/redo availability)
 */
export const selectHistoryState = (state: WorkflowState) => ({
  canUndo: state.past.length > 0,
  canRedo: state.future.length > 0,
});

// ============================================================================
// Hooks for Common Use Cases
// ============================================================================

/**
 * Hook to get the currently selected node
 */
export const useSelectedNode = () => {
  return useWorkflowStore((state) => {
    if (!state.selectedNodeId) return undefined;
    return state.nodes.find((node) => node.id === state.selectedNodeId);
  });
};

/**
 * Hook to get the currently selected edge
 */
export const useSelectedEdge = () => {
  return useWorkflowStore((state) => {
    if (!state.selectedEdgeId) return undefined;
    return state.edges.find((edge) => edge.id === state.selectedEdgeId);
  });
};

/**
 * Hook to get undo/redo availability
 */
export const useHistoryControls = () => {
  const canUndo = useWorkflowStore((state) => state.past.length > 0);
  const canRedo = useWorkflowStore((state) => state.future.length > 0);
  const undo = useWorkflowStore((state) => state.undo);
  const redo = useWorkflowStore((state) => state.redo);

  return { canUndo, canRedo, undo, redo };
};

/**
 * Hook to get execution controls
 */
export const useExecutionControls = () => {
  const executionStatus = useWorkflowStore((state) => state.executionStatus);
  const startExecution = useWorkflowStore((state) => state.startExecution);
  const pauseExecution = useWorkflowStore((state) => state.pauseExecution);
  const stopExecution = useWorkflowStore((state) => state.stopExecution);
  const currentExecutingNodeId = useWorkflowStore(
    (state) => state.currentExecutingNodeId
  );

  return {
    executionStatus,
    currentExecutingNodeId,
    startExecution,
    pauseExecution,
    stopExecution,
    isRunning: executionStatus === "running",
    isPaused: executionStatus === "paused",
    isIdle: executionStatus === "idle",
  };
};

// ============================================================================
// Keyboard Shortcuts Handler
// ============================================================================

/**
 * Initialize keyboard shortcuts for undo/redo and delete.
 * Should be called once on app mount.
 * Returns a cleanup function.
 */
export const initializeWorkflowKeyboardShortcuts = (): (() => void) => {
  if (typeof window === "undefined") return () => {};

  const handleKeyDown = (event: KeyboardEvent) => {
    const { undo, redo, canUndo, canRedo, removeNode, removeEdge } =
      useWorkflowStore.getState();

    const isMac = navigator.platform.toUpperCase().indexOf("MAC") >= 0;
    const modifier = isMac ? event.metaKey : event.ctrlKey;

    // Undo: Cmd/Ctrl + Z
    if (modifier && event.key === "z" && !event.shiftKey) {
      event.preventDefault();
      if (canUndo()) {
        undo();
      }
      return;
    }

    // Redo: Cmd/Ctrl + Shift + Z or Cmd/Ctrl + Y
    if (
      (modifier && event.key === "z" && event.shiftKey) ||
      (modifier && event.key === "y")
    ) {
      event.preventDefault();
      if (canRedo()) {
        redo();
      }
      return;
    }

    // Delete selected node or edge: Delete or Backspace
    if (event.key === "Delete" || event.key === "Backspace") {
      // Don't delete if user is typing in an input
      const target = event.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      ) {
        return;
      }

      const state = useWorkflowStore.getState();
      if (state.selectedNodeId) {
        event.preventDefault();
        removeNode(state.selectedNodeId);
      } else if (state.selectedEdgeId) {
        event.preventDefault();
        removeEdge(state.selectedEdgeId);
      }
    }
  };

  window.addEventListener("keydown", handleKeyDown);

  return () => {
    window.removeEventListener("keydown", handleKeyDown);
  };
};
