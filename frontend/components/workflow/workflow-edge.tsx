"use client";

import { memo, useMemo } from "react";
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
  sourceType?: "trigger" | "action" | "condition" | "output";
  targetType?: "trigger" | "action" | "condition" | "output";
}

export type WorkflowEdgeProps = EdgeProps<Edge<WorkflowEdgeData>>;

// Edge color configurations based on source node type
const edgeColors: Record<string, { start: string; end: string; glow: string }> = {
  trigger: {
    start: "#F59E0B",
    end: "#F97316",
    glow: "rgba(245, 158, 11, 0.4)",
  },
  action: {
    start: "#8B5CF6",
    end: "#A855F7",
    glow: "rgba(139, 92, 246, 0.4)",
  },
  condition: {
    start: "#14B8A6",
    end: "#06B6D4",
    glow: "rgba(20, 184, 166, 0.4)",
  },
  output: {
    start: "#22C55E",
    end: "#10B981",
    glow: "rgba(34, 197, 94, 0.4)",
  },
  default: {
    start: "#6366F1",
    end: "#8B5CF6",
    glow: "rgba(99, 102, 241, 0.4)",
  },
};

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
  sourceHandleId,
}: WorkflowEdgeProps) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    curvature: 0.25,
  });

  const isAnimated = data?.animated !== false; // Default to animated
  const sourceType = data?.sourceType || "default";
  const colors = edgeColors[sourceType] || edgeColors.default;

  // Unique gradient ID for this edge
  const gradientId = `edge-gradient-${id}`;
  const glowFilterId = `edge-glow-${id}`;

  // Check if this is the "false" branch of a condition
  const isFalseBranch = sourceHandleId === "false";
  const edgeOpacity = isFalseBranch ? 0.5 : 1;

  // Animation styles
  const animationStyle = useMemo(() => {
    if (!isAnimated) return {};
    return {
      strokeDasharray: "8 6",
      animation: "edgeFlowAnimation 1.5s linear infinite",
    };
  }, [isAnimated]);

  return (
    <>
      {/* SVG Defs for gradient and glow */}
      <defs>
        {/* Gradient for the edge */}
        <linearGradient
          id={gradientId}
          gradientUnits="userSpaceOnUse"
          x1={sourceX}
          y1={sourceY}
          x2={targetX}
          y2={targetY}
        >
          <stop offset="0%" stopColor={isFalseBranch ? "#64748B" : colors.start} stopOpacity={edgeOpacity} />
          <stop offset="100%" stopColor={isFalseBranch ? "#475569" : colors.end} stopOpacity={edgeOpacity * 0.8} />
        </linearGradient>

        {/* Glow filter */}
        <filter id={glowFilterId} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Glow/blur effect underneath (only when selected or hovered) */}
      <path
        d={edgePath}
        fill="none"
        stroke={isFalseBranch ? "rgba(100, 116, 139, 0.4)" : colors.glow}
        strokeWidth={selected ? 12 : 8}
        strokeOpacity={selected ? 0.6 : 0.3}
        className="transition-all duration-300"
        style={{
          filter: `blur(${selected ? 6 : 4}px)`,
        }}
      />

      {/* Invisible wider path for easier selection */}
      <path
        id={`${id}-interaction`}
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={24}
        className="cursor-pointer"
      />

      {/* Main edge path with gradient */}
      <path
        d={edgePath}
        fill="none"
        stroke={`url(#${gradientId})`}
        strokeWidth={selected ? 3 : 2.5}
        strokeLinecap="round"
        className={cn(
          "transition-all duration-300",
          selected && "stroke-[3.5px]"
        )}
        style={{
          ...animationStyle,
          filter: selected ? `url(#${glowFilterId})` : undefined,
        }}
        markerEnd={markerEnd}
      />

      {/* Animated particles along the edge (only when animated) */}
      {isAnimated && (
        <circle r="3" fill={isFalseBranch ? "#94A3B8" : colors.start}>
          <animateMotion
            dur="2s"
            repeatCount="indefinite"
            path={edgePath}
          />
        </circle>
      )}

      {/* Edge label */}
      {data?.label && (
        <foreignObject
          x={labelX - 50}
          y={labelY - 14}
          width={100}
          height={28}
          className="pointer-events-none"
        >
          <div
            className={cn(
              "flex items-center justify-center h-full",
              "text-[10px] font-medium px-3 py-1 rounded-full",
              "backdrop-blur-md",
              "transition-all duration-200",
              selected ? "text-white" : "text-white/70"
            )}
            style={{
              background: "rgba(20, 20, 30, 0.85)",
              border: `1px solid ${selected ? colors.start : "rgba(255,255,255,0.1)"}`,
              boxShadow: selected ? `0 0 12px ${colors.glow}` : "0 2px 8px rgba(0,0,0,0.3)",
            }}
          >
            {data.label}
          </div>
        </foreignObject>
      )}

      {/* CSS for edge animation */}
      <style>
        {`
          @keyframes edgeFlowAnimation {
            0% {
              stroke-dashoffset: 28;
            }
            100% {
              stroke-dashoffset: 0;
            }
          }
        `}
      </style>
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
