"use client";

import { useCallback, useState, type DragEvent } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  ConnectionLineType,
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  type NodeMouseHandler,
  type OnInit,
  type ReactFlowInstance,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { workflowNodeTypes, type WorkflowNodeData } from "./workflow-node";
import { workflowEdgeTypes } from "./workflow-edge";
import { cn } from "@/lib/utils";

// Default edge options
const defaultEdgeOptions = {
  type: "workflowEdge",
  markerEnd: {
    type: MarkerType.ArrowClosed,
    width: 16,
    height: 16,
  },
  data: {
    animated: true,
  },
};

// Connection line style
const connectionLineStyle = {
  stroke: "hsl(var(--primary))",
  strokeWidth: 2,
  strokeDasharray: "5 5",
};

// Fit view options
const fitViewOptions = {
  padding: 0.2,
  maxZoom: 1.5,
};

// Minimap node color based on node type
const getMinimapNodeColor = (node: Node<WorkflowNodeData>) => {
  const colors: Record<string, string> = {
    trigger: "hsl(var(--node-trigger))",
    action: "hsl(var(--node-action))",
    condition: "hsl(var(--node-condition))",
    output: "hsl(var(--node-output))",
  };
  return colors[node.data?.type] || "hsl(var(--muted-foreground))";
};

export interface WorkflowCanvasProps {
  /** Array of nodes to render */
  nodes: Node<WorkflowNodeData>[];
  /** Array of edges connecting nodes */
  edges: Edge[];
  /** Callback when nodes change (move, delete, etc.) */
  onNodesChange: OnNodesChange<Node<WorkflowNodeData>>;
  /** Callback when edges change (delete, etc.) */
  onEdgesChange: OnEdgesChange<Edge>;
  /** Callback when a new connection is made between nodes */
  onConnect: OnConnect;
  /** Callback when a node is clicked */
  onNodeClick?: NodeMouseHandler<Node<WorkflowNodeData>>;
  /** Callback when the canvas (pane) is clicked */
  onPaneClick?: () => void;
  /** Callback when ReactFlow instance is initialized */
  onInit?: OnInit<Node<WorkflowNodeData>, Edge>;
  /** Callback when a draggable item is dropped on the canvas */
  onDrop?: (event: DragEvent<HTMLDivElement>, instance: ReactFlowInstance<Node<WorkflowNodeData>, Edge>) => void;
  /** Callback when a draggable item is dragged over the canvas */
  onDragOver?: (event: DragEvent<HTMLDivElement>) => void;
  /** Whether to show the mini map */
  showMiniMap?: boolean;
  /** Whether to show the controls */
  showControls?: boolean;
  /** Whether to show the background pattern */
  showBackground?: boolean;
  /** Additional CSS classes */
  className?: string;
}

export function WorkflowCanvas({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onNodeClick,
  onPaneClick,
  onInit,
  onDrop,
  onDragOver,
  showMiniMap = true,
  showControls = true,
  showBackground = true,
  className,
}: WorkflowCanvasProps) {
  // Store the ReactFlow instance for drop handling
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance<Node<WorkflowNodeData>, Edge> | null>(null);

  // Handle init to store the instance
  const handleInit = useCallback(
    (instance: ReactFlowInstance<Node<WorkflowNodeData>, Edge>) => {
      setReactFlowInstance(instance);
      onInit?.(instance);
    },
    [onInit]
  );

  // Handle drop events for adding new nodes
  const handleDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      if (reactFlowInstance && onDrop) {
        onDrop(event, reactFlowInstance);
      }
    },
    [onDrop, reactFlowInstance]
  );

  const handleDragOver = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      onDragOver?.(event);
    },
    [onDragOver]
  );

  return (
    <div
      className={cn(
        "w-full h-full bg-background rounded-lg border border-border overflow-hidden",
        className
      )}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        onInit={handleInit}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        nodeTypes={workflowNodeTypes}
        edgeTypes={workflowEdgeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        connectionLineType={ConnectionLineType.Bezier}
        connectionLineStyle={connectionLineStyle}
        fitView
        fitViewOptions={fitViewOptions}
        snapToGrid
        snapGrid={[16, 16]}
        deleteKeyCode={["Backspace", "Delete"]}
        multiSelectionKeyCode={["Meta", "Control"]}
        selectionKeyCode={["Shift"]}
        panOnScroll
        selectionOnDrag
        proOptions={{
          hideAttribution: true,
        }}
        className="workflow-canvas"
      >
        {/* Background Pattern */}
        {showBackground && (
          <Background
            variant={BackgroundVariant.Dots}
            gap={16}
            size={1}
            color="hsl(var(--muted-foreground) / 0.2)"
            className="bg-background"
          />
        )}

        {/* Zoom and Pan Controls */}
        {showControls && (
          <Controls
            showZoom
            showFitView
            showInteractive={false}
            className={cn(
              "[&>button]:bg-card [&>button]:border-border [&>button]:text-foreground",
              "[&>button:hover]:bg-muted [&>button]:rounded-md",
              "[&>button]:shadow-sm"
            )}
          />
        )}

        {/* Mini Map Overview */}
        {showMiniMap && (
          <MiniMap
            nodeColor={getMinimapNodeColor}
            nodeStrokeWidth={2}
            nodeBorderRadius={4}
            maskColor="hsl(var(--background) / 0.8)"
            className={cn(
              "bg-card border border-border rounded-lg shadow-md",
              "!bottom-4 !right-4"
            )}
            pannable
            zoomable
          />
        )}
      </ReactFlow>
    </div>
  );
}

export default WorkflowCanvas;
