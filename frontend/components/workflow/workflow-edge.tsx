"use client";

import { memo } from "react";
import {
  BaseEdge,
  getBezierPath,
  type EdgeProps,
  type Edge,
} from "@xyflow/react";
import { cn } from "@/lib/utils";

export interface WorkflowEdgeData extends Record<string, unknown> {
  animated?: boolean;
  label?: string;
}

export type WorkflowEdgeProps = EdgeProps<Edge<WorkflowEdgeData>>;

function WorkflowEdgeComponent({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  selected,
  data,
  markerEnd,
}: WorkflowEdgeProps) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const isAnimated = data?.animated !== false; // Default to animated

  return (
    <>
      {/* Invisible wider path for easier selection */}
      <path
        id={`${id}-interaction`}
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={20}
        className="cursor-pointer"
      />

      {/* Main edge path */}
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        className={cn(
          "!stroke-2",
          selected
            ? "!stroke-primary"
            : "!stroke-muted-foreground/50"
        )}
        style={{
          strokeDasharray: isAnimated ? "5 5" : "none",
          animation: isAnimated ? "flowPulse 1.5s ease-in-out infinite" : "none",
        }}
      />

      {/* Edge label */}
      {data?.label && (
        <foreignObject
          x={labelX - 40}
          y={labelY - 12}
          width={80}
          height={24}
          className="pointer-events-none"
        >
          <div
            className={cn(
              "flex items-center justify-center h-full",
              "text-xs font-medium px-2 py-0.5 rounded-md",
              "bg-background border border-border shadow-sm",
              selected ? "text-primary" : "text-muted-foreground"
            )}
          >
            {data.label}
          </div>
        </foreignObject>
      )}
    </>
  );
}

// Memoize to prevent unnecessary re-renders
export const WorkflowEdge = memo(WorkflowEdgeComponent);
WorkflowEdge.displayName = "WorkflowEdge";

// Export edge types map for ReactFlow
export const workflowEdgeTypes = {
  workflowEdge: WorkflowEdge,
};

export default WorkflowEdge;
