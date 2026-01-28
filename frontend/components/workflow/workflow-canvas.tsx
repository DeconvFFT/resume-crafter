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

// Default edge options with enhanced styling
const defaultEdgeOptions = {
  type: "workflowEdge",
  markerEnd: {
    type: MarkerType.ArrowClosed,
    width: 20,
    height: 20,
    color: "hsl(var(--primary))",
  },
  data: {
    animated: true,
  },
};

// Connection line style - glowing effect
const connectionLineStyle = {
  stroke: "url(#connection-gradient)",
  strokeWidth: 3,
  strokeDasharray: "8 4",
  filter: "drop-shadow(0 0 6px hsl(var(--primary) / 0.6))",
};

// Fit view options
const fitViewOptions = {
  padding: 0.2,
  maxZoom: 1.5,
};

// Minimap node color based on node type - enhanced with glow colors
const getMinimapNodeColor = (node: Node<WorkflowNodeData>) => {
  const colors: Record<string, string> = {
    trigger: "hsl(38, 92%, 50%)",    // Amber
    action: "hsl(262, 83%, 58%)",    // Purple
    condition: "hsl(174, 84%, 45%)", // Teal
    output: "hsl(142, 76%, 45%)",    // Green
  };
  return colors[node.data?.type] || "hsl(215, 20%, 45%)";
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
        "workflow-canvas-wrapper w-full h-full overflow-hidden relative",
        className
      )}
    >
      {/* Executive Noir background gradient */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `
            radial-gradient(ellipse 80% 50% at 50% 50%, hsl(var(--primary) / 0.03) 0%, transparent 60%),
            linear-gradient(180deg, #0a0a0f 0%, #12121a 50%, #0a0a0f 100%)
          `,
        }}
      />

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
        snapGrid={[20, 20]}
        deleteKeyCode={["Backspace", "Delete"]}
        multiSelectionKeyCode={["Meta", "Control"]}
        selectionKeyCode={["Shift"]}
        panOnScroll
        selectionOnDrag
        proOptions={{
          hideAttribution: true,
        }}
        className="workflow-canvas-noir"
        style={{
          background: "transparent",
        }}
      >
        {/* SVG Defs for gradients and filters */}
        <svg width="0" height="0" style={{ position: "absolute" }}>
          <defs>
            {/* Connection gradient */}
            <linearGradient id="connection-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.8" />
              <stop offset="100%" stopColor="hsl(262, 83%, 58%)" stopOpacity="0.8" />
            </linearGradient>

            {/* Glow filter */}
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
        </svg>

        {/* Background Pattern - Subtle dot grid */}
        {showBackground && (
          <Background
            variant={BackgroundVariant.Dots}
            gap={24}
            size={1.5}
            color="hsl(220, 20%, 20%)"
            className="!bg-transparent"
          />
        )}

        {/* Zoom and Pan Controls - Executive dark theme */}
        {showControls && (
          <Controls
            showZoom
            showFitView
            showInteractive={false}
            className={cn(
              "workflow-controls-noir",
              "!bg-[#0d0d14]/90 !border !border-white/10 !rounded-xl !shadow-2xl !backdrop-blur-xl",
              "[&>button]:!bg-transparent [&>button]:!border-0 [&>button]:!text-white/70",
              "[&>button:hover]:!bg-white/10 [&>button:hover]:!text-white",
              "[&>button]:!rounded-lg [&>button]:!m-1 [&>button]:!transition-all [&>button]:!duration-200",
              "[&>button:hover]:!shadow-[0_0_12px_hsl(var(--primary)/0.3)]",
              "[&>button>svg]:!fill-current"
            )}
            style={{
              boxShadow: "0 0 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05)",
            }}
          />
        )}

        {/* Mini Map Overview - Executive dark theme */}
        {showMiniMap && (
          <MiniMap
            nodeColor={getMinimapNodeColor}
            nodeStrokeWidth={2}
            nodeBorderRadius={6}
            maskColor="rgba(10, 10, 15, 0.85)"
            className={cn(
              "workflow-minimap-noir",
              "!bg-[#0d0d14]/90 !border !border-white/10 !rounded-xl !shadow-2xl !backdrop-blur-xl",
              "!bottom-4 !right-4"
            )}
            style={{
              boxShadow: "0 0 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05)",
            }}
            pannable
            zoomable
          />
        )}
      </ReactFlow>

      {/* Subtle vignette overlay */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.3) 100%)",
        }}
      />
    </div>
  );
}

export default WorkflowCanvas;
