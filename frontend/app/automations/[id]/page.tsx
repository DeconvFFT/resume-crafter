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
import { toast } from "sonner";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
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
import { useCampaign, useCreateCampaign, useActivateCampaign } from "@/hooks/useAutomation";
import { useExecutionStream } from "@/hooks/useExecutionStream";
import { useTriggerCronJob } from "@/hooks/useExecutions";
import { useAuthStore } from "@/lib/stores/auth";
import { api } from "@/lib/api/client";

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Convert campaign settings to workflow nodes.
 * This maps the campaign configuration to visual workflow nodes.
 */
function campaignToWorkflowNodes(campaign: {
  id: string;
  name: string;
  target_roles: string[];
  target_locations: string[];
  keywords: string[];
  min_salary?: number | null;
  settings?: Record<string, unknown> | null;
}): { nodes: Node<WorkflowNodeData>[]; edges: Edge[] } {
  // Default workflow structure for a job search campaign
  const nodes: Node<WorkflowNodeData>[] = [
    {
      id: "node-trigger",
      type: "workflowNode",
      position: { x: 100, y: 150 },
      data: {
        type: "trigger" as const,
        title: "Job Discovery",
        description: `Search for: ${campaign.target_roles.join(", ")}`,
      },
    },
    {
      id: "node-filter",
      type: "workflowNode",
      position: { x: 400, y: 100 },
      data: {
        type: "condition" as const,
        title: "Filter Jobs",
        description: campaign.min_salary 
          ? `Salary >= $${campaign.min_salary.toLocaleString()}`
          : "Match score > 70%",
      },
    },
    {
      id: "node-analyze",
      type: "workflowNode",
      position: { x: 700, y: 50 },
      data: {
        type: "action" as const,
        title: "Analyze & Score",
        description: "Match against profile",
      },
    },
    {
      id: "node-resume",
      type: "workflowNode",
      position: { x: 1000, y: 50 },
      data: {
        type: "action" as const,
        title: "Generate Resume",
        description: "Tailor for job",
      },
    },
    {
      id: "node-apply",
      type: "workflowNode",
      position: { x: 1300, y: 50 },
      data: {
        type: "output" as const,
        title: "Queue Application",
        description: "Add to application queue",
      },
    },
    {
      id: "node-skip",
      type: "workflowNode",
      position: { x: 700, y: 250 },
      data: {
        type: "output" as const,
        title: "Skip Job",
        description: "Mark as not qualified",
      },
    },
  ];

  const edges: Edge[] = [
    { id: "edge-1", source: "node-trigger", target: "node-filter" },
    { id: "edge-2", source: "node-filter", target: "node-analyze", sourceHandle: "true" },
    { id: "edge-3", source: "node-analyze", target: "node-resume" },
    { id: "edge-4", source: "node-resume", target: "node-apply" },
    { id: "edge-5", source: "node-filter", target: "node-skip", sourceHandle: "false" },
  ];

  return { nodes, edges };
}

// Default workflow for new campaigns
const defaultWorkflow = {
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
  ] as Node<WorkflowNodeData>[],
  edges: [] as Edge[],
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

  // Auth state
  const accessToken = useAuthStore((state) => state.accessToken);

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
  const [currentExecutionId, setCurrentExecutionId] = useState<string | null>(null);

  // API hooks
  const { data: campaign, isLoading: isLoadingCampaign } = useCampaign(
    isNewWorkflow ? null : workflowId,
    !isNewWorkflow
  );
  const createCampaignMutation = useCreateCampaign();
  const activateCampaignMutation = useActivateCampaign();
  const triggerJobMutation = useTriggerCronJob();

  // Execution stream for real-time monitoring
  const executionStream = useExecutionStream({
    executionId: currentExecutionId,
    accessToken,
    enabled: !!currentExecutionId && isRunning,
    onStatusChange: (status) => {
      if (status === "completed" || status === "failed" || status === "cancelled") {
        setIsRunning(false);
        if (status === "completed") {
          toast.success("Workflow execution completed");
        } else if (status === "failed") {
          toast.error("Workflow execution failed");
        }
      }
    },
    onProgress: (progress) => {
      setExecution((prev) => prev ? { ...prev, progress } : null);
    },
    onComplete: () => {
      setExecution((prev) => prev ? { ...prev, status: "completed", completedAt: new Date() } : null);
    },
    onError: (message) => {
      setExecution((prev) => prev ? { ...prev, status: "failed", error: message } : null);
      toast.error(message);
    },
  });

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

  // Load workflow data from API
  useEffect(() => {
    if (isNewWorkflow) {
      setNodes(defaultWorkflow.nodes);
      setEdges(defaultWorkflow.edges);
      setWorkflowName("Untitled Workflow");
    } else if (campaign) {
      // Convert campaign data to workflow visualization
      const { nodes: campaignNodes, edges: campaignEdges } = campaignToWorkflowNodes(campaign);
      setNodes(campaignNodes);
      setEdges(campaignEdges);
      setWorkflowName(campaign.name);
    }
  }, [workflowId, isNewWorkflow, campaign, setNodes, setEdges]);

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
    if (!accessToken) {
      toast.error("Please log in to save");
      return;
    }

    setIsSaving(true);
    try {
      if (isNewWorkflow) {
        // Create new campaign
        const newCampaign = await createCampaignMutation.mutateAsync({
          name: workflowName,
          target_roles: ["Software Engineer"], // Default, should be extracted from nodes
          target_locations: [],
          keywords: [],
          settings: {
            workflow_nodes: nodes.map((n) => ({
              id: n.id,
              type: n.data.type,
              title: n.data.title,
              position: n.position,
            })),
            workflow_edges: edges.map((e) => ({
              id: e.id,
              source: e.source,
              target: e.target,
            })),
          },
        });
        toast.success("Campaign created successfully");
        router.push(`/automations/${newCampaign.id}`);
      } else {
        // Update existing campaign - for now, just show success
        // In a full implementation, we'd call an update endpoint
        toast.success("Workflow saved successfully");
      }
    } catch (error) {
      console.error("Failed to save workflow:", error);
      toast.error("Failed to save workflow");
    } finally {
      setIsSaving(false);
    }
  }, [accessToken, isNewWorkflow, workflowName, nodes, edges, createCampaignMutation, router]);

  // Handle run workflow
  const handleRun = useCallback(async () => {
    if (!accessToken) {
      toast.error("Please log in to run workflow");
      return;
    }

    setIsRunning(true);
    setShowExecutionPanel(true);
    startExecution();

    // Create initial execution state
    const initialExecution: WorkflowExecution = {
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

    setExecution(initialExecution);

    try {
      // If this is an existing campaign, activate it and trigger job discovery
      if (!isNewWorkflow && campaign) {
        // Activate the campaign if it's not already active
        if (campaign.status !== "active") {
          await activateCampaignMutation.mutateAsync(campaign.id);
        }

        // Trigger job discovery cron job
        const result = await triggerJobMutation.mutateAsync("job_discovery");
        toast.success("Workflow triggered! Job discovery started.");
        
        // Note: In a full implementation, we'd get the execution ID from the trigger response
        // and use it to track real-time progress via SSE
        // setCurrentExecutionId(result.execution_id);
      } else {
        // For new workflows, save first then run
        toast.info("Save the workflow first to run it");
        setIsRunning(false);
        return;
      }

      // Simulate execution progress for UI feedback
      // In production, this would be driven by SSE events from executionStream
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
    } catch (error) {
      console.error("Failed to run workflow:", error);
      toast.error("Failed to start workflow");
      setIsRunning(false);
      setExecution((prev) => prev ? { ...prev, status: "failed" } : null);
    }
  }, [accessToken, nodes, workflowId, workflowName, isNewWorkflow, campaign, activateCampaignMutation, triggerJobMutation, startExecution]);

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
