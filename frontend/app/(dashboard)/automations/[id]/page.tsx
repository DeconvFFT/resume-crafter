"use client";

import { useEffect, useState, useCallback, useMemo, type DragEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  useNodesState,
  useEdgesState,
  addEdge,
  type Connection,
  type Node,
  type Edge,
  type ReactFlowInstance,
} from "@xyflow/react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  Save,
  Play,
  Undo2,
  Redo2,
  Settings,
  ChevronDown,
  ChevronUp,
  MoreVertical,
  Loader2,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { NodePanel, nodeTypes as availableNodeTypes, type NodeType } from "@/components/workflow/node-panel";
import { WorkflowCanvas } from "@/components/workflow/workflow-canvas";
import { NodeConfigPanel, type NodeConfig } from "@/components/workflow/node-config-panel";
import {
  ExecutionPanel,
  type WorkflowExecution,
  type NodeExecution,
} from "@/components/workflow/execution-panel";
import type { WorkflowNodeData } from "@/components/workflow/workflow-node";
import {
  useWorkflowStore,
  useHistoryControls,
  useExecutionControls,
  initializeWorkflowKeyboardShortcuts,
} from "@/lib/stores/workflow";

// ============================================================================
// Mock Data
// ============================================================================

const mockWorkflow = {
  id: "workflow-1",
  name: "Auto-Apply to Jobs",
  description: "Automatically apply to matching job postings",
  nodes: [
    {
      id: "node-1",
      type: "workflowNode",
      position: { x: 100, y: 150 },
      data: {
        type: "trigger" as const,
        title: "New Job Found",
        description: "Triggers when a new job matches criteria",
      },
    },
    {
      id: "node-2",
      type: "workflowNode",
      position: { x: 400, y: 100 },
      data: {
        type: "condition" as const,
        title: "Check Salary",
        description: "Salary > $100k",
      },
    },
    {
      id: "node-3",
      type: "workflowNode",
      position: { x: 700, y: 50 },
      data: {
        type: "action" as const,
        title: "Generate Resume",
        description: "Create tailored resume",
      },
    },
    {
      id: "node-4",
      type: "workflowNode",
      position: { x: 1000, y: 50 },
      data: {
        type: "output" as const,
        title: "Apply to Job",
        description: "Submit application",
      },
    },
    {
      id: "node-5",
      type: "workflowNode",
      position: { x: 700, y: 250 },
      data: {
        type: "output" as const,
        title: "Save Draft",
        description: "Save for review",
      },
    },
  ] as Node<WorkflowNodeData>[],
  edges: [
    { id: "edge-1", source: "node-1", target: "node-2" },
    { id: "edge-2", source: "node-2", target: "node-3", sourceHandle: "true" },
    { id: "edge-3", source: "node-3", target: "node-4" },
    { id: "edge-4", source: "node-2", target: "node-5", sourceHandle: "false" },
  ] as Edge[],
};

// Map node category to WorkflowNodeData type
const categoryToNodeType: Record<string, WorkflowNodeData["type"]> = {
  trigger: "trigger",
  action: "action",
  logic: "condition",
  output: "output",
};

// ============================================================================
// Component
// ============================================================================

export default function WorkflowBuilderPage() {
  const params = useParams();
  const router = useRouter();
  const workflowId = params.id as string;
  const isNewWorkflow = workflowId === "new";

  // Local state for ReactFlow
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<WorkflowNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance<Node<WorkflowNodeData>, Edge> | null>(null);

  // UI state
  const [workflowName, setWorkflowName] = useState(isNewWorkflow ? "Untitled Workflow" : "");
  const [isEditingName, setIsEditingName] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [showExecutionPanel, setShowExecutionPanel] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [showConfigPanel, setShowConfigPanel] = useState(false);
  const [execution, setExecution] = useState<WorkflowExecution | null>(null);

  // Store hooks
  const { canUndo, canRedo, undo, redo } = useHistoryControls();
  const {
    startExecution,
    pauseExecution,
    stopExecution,
    executionStatus,
  } = useExecutionControls();

  // Global store for persistence
  const storeSetNodes = useWorkflowStore((state) => state.setNodes);
  const storeSetEdges = useWorkflowStore((state) => state.setEdges);
  const storeSelectNode = useWorkflowStore((state) => state.selectNode);
  const storeAddNode = useWorkflowStore((state) => state.addNode);

  // Initialize keyboard shortcuts
  useEffect(() => {
    const cleanup = initializeWorkflowKeyboardShortcuts();
    return cleanup;
  }, []);

  // Load workflow data
  useEffect(() => {
    if (isNewWorkflow) {
      setNodes([]);
      setEdges([]);
      setWorkflowName("Untitled Workflow");
    } else {
      // Load mock data for existing workflow
      setNodes(mockWorkflow.nodes);
      setEdges(mockWorkflow.edges);
      setWorkflowName(mockWorkflow.name);
    }
  }, [workflowId, isNewWorkflow, setNodes, setEdges]);

  // Sync local state with store
  useEffect(() => {
    storeSetNodes(nodes);
  }, [nodes, storeSetNodes]);

  useEffect(() => {
    storeSetEdges(edges);
  }, [edges, storeSetEdges]);

  // Get selected node config
  const selectedNodeConfig = useMemo((): NodeConfig | null => {
    if (!selectedNodeId) return null;
    const node = nodes.find((n) => n.id === selectedNodeId);
    if (!node) return null;

    const nodeTypeInfo = availableNodeTypes.find(
      (nt) => categoryToNodeType[nt.category] === node.data.type
    );

    return {
      id: node.id,
      nodeTypeId: nodeTypeInfo?.id || node.data.type,
      title: node.data.title,
      description: node.data.description || "",
      category: nodeTypeInfo?.category || "action",
      icon: nodeTypeInfo?.icon || availableNodeTypes[0].icon,
      // Add default configs based on category
      ...(node.data.type === "trigger" && {
        triggerConfig: {
          eventType: "job_posting" as const,
        },
      }),
      ...(node.data.type === "action" && {
        actionConfig: {
          actionType: nodeTypeInfo?.id || "generate-resume",
          parameters: {},
          timeout: 30,
        },
      }),
      ...(node.data.type === "condition" && {
        conditionConfig: {
          field: "",
          operator: "equals" as const,
          value: "",
        },
      }),
      ...(node.data.type === "output" && {
        outputConfig: {
          destination: "draft" as const,
          format: "pdf" as const,
        },
      }),
    };
  }, [selectedNodeId, nodes]);

  // Handle connection between nodes
  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge(connection, eds));
    },
    [setEdges]
  );

  // Handle node click
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node<WorkflowNodeData>) => {
      setSelectedNodeId(node.id);
      setShowConfigPanel(true);
      storeSelectNode(node.id);
    },
    [storeSelectNode]
  );

  // Handle pane click (deselect)
  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
    setShowConfigPanel(false);
    storeSelectNode(null);
  }, [storeSelectNode]);

  // Handle drag over canvas
  const onDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  // Handle drop on canvas
  const onDrop = useCallback(
    (event: DragEvent<HTMLDivElement>, instance: ReactFlowInstance<Node<WorkflowNodeData>, Edge>) => {
      event.preventDefault();

      const nodeTypeData = event.dataTransfer.getData("application/workflow-node");
      if (!nodeTypeData) {
        // Try the alternative key
        const altData = event.dataTransfer.getData("application/reactflow");
        if (!altData) return;
      }

      const nodeType: NodeType = JSON.parse(nodeTypeData || event.dataTransfer.getData("application/reactflow"));

      // Get the position where the node was dropped
      const position = instance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      // Create new node
      const newNode: Node<WorkflowNodeData> = {
        id: `node-${Date.now()}`,
        type: "workflowNode",
        position,
        data: {
          type: categoryToNodeType[nodeType.category],
          title: nodeType.label,
          description: nodeType.description,
        },
      };

      setNodes((nds) => [...nds, newNode]);
      storeAddNode(newNode);
    },
    [setNodes, storeAddNode]
  );

  // Handle ReactFlow init
  const onInit = useCallback((instance: ReactFlowInstance<Node<WorkflowNodeData>, Edge>) => {
    setReactFlowInstance(instance);
  }, []);

  // Handle node config update
  const handleNodeUpdate = useCallback(
    (config: NodeConfig) => {
      setNodes((nds) =>
        nds.map((node) => {
          if (node.id === config.id) {
            return {
              ...node,
              data: {
                ...node.data,
                title: config.title,
                description: config.description,
              },
            };
          }
          return node;
        })
      );
    },
    [setNodes]
  );

  // Handle node delete
  const handleNodeDelete = useCallback(
    (nodeId: string) => {
      setNodes((nds) => nds.filter((node) => node.id !== nodeId));
      setEdges((eds) =>
        eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId)
      );
      setSelectedNodeId(null);
      setShowConfigPanel(false);
    },
    [setNodes, setEdges]
  );

  // Handle save
  const handleSave = useCallback(async () => {
    setIsSaving(true);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setIsSaving(false);
    // In production, this would save to the backend
  }, []);

  // Handle run workflow
  const handleRun = useCallback(() => {
    setIsRunning(true);
    setShowExecutionPanel(true);
    startExecution();

    // Create mock execution
    const mockExecution: WorkflowExecution = {
      id: `exec-${Date.now()}`,
      workflowId: workflowId,
      workflowName: workflowName,
      status: "running",
      startedAt: new Date(),
      progress: 0,
      nodes: nodes.map((node) => ({
        nodeId: node.id,
        nodeName: node.data.title,
        nodeType: node.data.type,
        status: "pending" as const,
      })),
      currentNodeIndex: 0,
      totalNodes: nodes.length,
    };

    setExecution(mockExecution);

    // Simulate execution progress
    let currentIndex = 0;
    const interval = setInterval(() => {
      if (currentIndex >= nodes.length) {
        clearInterval(interval);
        setExecution((prev) =>
          prev
            ? {
                ...prev,
                status: "completed",
                completedAt: new Date(),
                progress: 100,
                duration: Date.now() - prev.startedAt.getTime(),
              }
            : null
        );
        setIsRunning(false);
        return;
      }

      setExecution((prev) => {
        if (!prev) return null;

        const updatedNodes = prev.nodes.map((node, idx) => {
          if (idx < currentIndex) {
            return {
              ...node,
              status: "completed" as const,
              startedAt: new Date(Date.now() - 2000),
              completedAt: new Date(Date.now() - 1000),
              duration: 1000,
              output: { success: true },
            };
          }
          if (idx === currentIndex) {
            return {
              ...node,
              status: "running" as const,
              startedAt: new Date(),
            };
          }
          return node;
        });

        return {
          ...prev,
          nodes: updatedNodes,
          currentNodeIndex: currentIndex,
          progress: Math.round(((currentIndex + 1) / nodes.length) * 100),
          duration: Date.now() - prev.startedAt.getTime(),
        };
      });

      currentIndex++;
    }, 1500);

    return () => clearInterval(interval);
  }, [nodes, workflowId, workflowName, startExecution]);

  // Handle pause execution
  const handlePause = useCallback(() => {
    pauseExecution();
    setExecution((prev) =>
      prev ? { ...prev, status: "paused" } : null
    );
  }, [pauseExecution]);

  // Handle stop execution
  const handleStop = useCallback(() => {
    stopExecution();
    setExecution((prev) =>
      prev ? { ...prev, status: "cancelled" } : null
    );
    setIsRunning(false);
  }, [stopExecution]);

  return (
    <div className="fixed inset-0 top-14 left-0 flex flex-col bg-background overflow-hidden">
      {/* Top Bar */}
      <div className="flex items-center justify-between h-14 px-4 border-b border-border bg-card shrink-0">
        {/* Left section */}
        <div className="flex items-center gap-4">
          <Link href="/automations">
            <Button variant="ghost" size="icon" aria-label="Back to automations">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>

          {/* Workflow name */}
          <div className="flex items-center gap-2">
            {isEditingName ? (
              <Input
                value={workflowName}
                onChange={(e) => setWorkflowName(e.target.value)}
                onBlur={() => setIsEditingName(false)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") setIsEditingName(false);
                  if (e.key === "Escape") setIsEditingName(false);
                }}
                className="h-8 w-64 font-semibold"
                autoFocus
              />
            ) : (
              <button
                onClick={() => setIsEditingName(true)}
                className="text-lg font-semibold hover:text-primary transition-colors"
              >
                {workflowName}
              </button>
            )}
            {isNewWorkflow && (
              <Badge variant="secondary" className="text-2xs">
                Draft
              </Badge>
            )}
          </div>
        </div>

        {/* Center section - History controls */}
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={undo}
            disabled={!canUndo}
            aria-label="Undo"
          >
            <Undo2 className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={redo}
            disabled={!canRedo}
            aria-label="Redo"
          >
            <Redo2 className="h-4 w-4" />
          </Button>
        </div>

        {/* Right section */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleSave}
            disabled={isSaving}
            className="gap-1.5"
          >
            {isSaving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Save
          </Button>
          <Button
            variant="default"
            size="sm"
            onClick={handleRun}
            disabled={isRunning || nodes.length === 0}
            className="gap-1.5"
          >
            {isRunning ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            Run
          </Button>
          <Button variant="ghost" size="icon" aria-label="More options">
            <MoreVertical className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Main content area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar - Node Panel */}
        <NodePanel
          className="shrink-0"
          onDragStart={(nodeType) => {
            // Optional: track drag state
          }}
        />

        {/* Center - Workflow Canvas */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <WorkflowCanvas
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            onInit={onInit}
            onDrop={onDrop}
            onDragOver={onDragOver}
            showMiniMap={true}
            showControls={true}
            showBackground={true}
            className="flex-1 rounded-none border-0"
          />

          {/* Execution Panel (collapsible at bottom) */}
          <AnimatePresence>
            {showExecutionPanel && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <ExecutionPanel
                  execution={execution}
                  isExpanded={showExecutionPanel}
                  onToggleExpand={() => setShowExecutionPanel(!showExecutionPanel)}
                  onPlay={handleRun}
                  onPause={handlePause}
                  onStop={handleStop}
                  onRetry={handleRun}
                />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Toggle execution panel button (when collapsed) */}
          {!showExecutionPanel && (
            <button
              onClick={() => setShowExecutionPanel(true)}
              className="flex items-center justify-center gap-2 h-10 border-t border-border bg-card hover:bg-accent/50 transition-colors text-sm text-muted-foreground"
            >
              <ChevronUp className="h-4 w-4" />
              Show Execution Panel
            </button>
          )}
        </div>

        {/* Right sidebar - Node Config Panel */}
        <AnimatePresence>
          {showConfigPanel && selectedNodeConfig && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 320, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="shrink-0 overflow-hidden"
            >
              <NodeConfigPanel
                node={selectedNodeConfig}
                isOpen={showConfigPanel}
                onClose={() => {
                  setShowConfigPanel(false);
                  setSelectedNodeId(null);
                }}
                onUpdate={handleNodeUpdate}
                onDelete={handleNodeDelete}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
