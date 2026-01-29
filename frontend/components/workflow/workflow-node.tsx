"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";
import { cn } from "@/lib/utils";
import {
  Zap,
  Play,
  GitBranch,
  CheckCircle2,
  type LucideIcon,
} from "lucide-react";

// Node type definitions
export type WorkflowNodeType = "trigger" | "action" | "condition" | "output";

export interface WorkflowNodeData extends Record<string, unknown> {
  type: WorkflowNodeType;
  title: string;
  description?: string;
  icon?: LucideIcon;
}

export type WorkflowNodeProps = NodeProps<Node<WorkflowNodeData>>;

// Default icons for each node type
const defaultIcons: Record<WorkflowNodeType, LucideIcon> = {
  trigger: Zap,
  action: Play,
  condition: GitBranch,
  output: CheckCircle2,
};

// Node type configurations - Executive Noir with glow colors
const nodeTypeConfig: Record<
  WorkflowNodeType,
  {
    glowColor: string;
    borderColor: string;
    iconBgColor: string;
    iconColor: string;
    handleColor: string;
    shadowColor: string;
    hasInputHandle: boolean;
    hasOutputHandle: boolean;
    outputHandleCount?: number;
  }
> = {
  trigger: {
    glowColor: "rgba(245, 158, 11, 0.4)",   // Amber glow
    borderColor: "rgba(245, 158, 11, 0.5)",
    iconBgColor: "rgba(245, 158, 11, 0.15)",
    iconColor: "#F59E0B",
    handleColor: "#F59E0B",
    shadowColor: "0 0 20px rgba(245, 158, 11, 0.3), 0 0 40px rgba(245, 158, 11, 0.1)",
    hasInputHandle: false,
    hasOutputHandle: true,
  },
  action: {
    glowColor: "rgba(20, 184, 166, 0.4)",   // Teal glow
    borderColor: "rgba(20, 184, 166, 0.5)",
    iconBgColor: "rgba(20, 184, 166, 0.15)",
    iconColor: "#14B8A6",
    handleColor: "#14B8A6",
    shadowColor: "0 0 20px rgba(20, 184, 166, 0.3), 0 0 40px rgba(20, 184, 166, 0.1)",
    hasInputHandle: true,
    hasOutputHandle: true,
  },
  condition: {
    glowColor: "rgba(20, 184, 166, 0.4)",   // Teal glow
    borderColor: "rgba(20, 184, 166, 0.5)",
    iconBgColor: "rgba(20, 184, 166, 0.15)",
    iconColor: "#14B8A6",
    handleColor: "#14B8A6",
    shadowColor: "0 0 20px rgba(20, 184, 166, 0.3), 0 0 40px rgba(20, 184, 166, 0.1)",
    hasInputHandle: true,
    hasOutputHandle: true,
    outputHandleCount: 2, // true/false branches
  },
  output: {
    glowColor: "rgba(34, 197, 94, 0.4)",    // Green glow
    borderColor: "rgba(34, 197, 94, 0.5)",
    iconBgColor: "rgba(34, 197, 94, 0.15)",
    iconColor: "#22C55E",
    handleColor: "#22C55E",
    shadowColor: "0 0 20px rgba(34, 197, 94, 0.3), 0 0 40px rgba(34, 197, 94, 0.1)",
    hasInputHandle: true,
    hasOutputHandle: false,
  },
};

function WorkflowNodeComponent({ data, selected }: WorkflowNodeProps) {
  const { type, title, description, icon } = data;
  const config = nodeTypeConfig[type];
  const Icon = icon || defaultIcons[type];

  return (
    <div
      className={cn(
        // Base styles - Glassmorphism
        "relative group min-w-[200px] max-w-[240px]",
        "rounded-xl p-[1px]",
        // Transition for smooth animations
        "transition-all duration-300 ease-out",
        // Hover state
        "hover:scale-[1.02]",
        // Selected state
        selected && "scale-[1.02]"
      )}
      style={{
        // Gradient border
        background: selected
          ? `linear-gradient(135deg, ${config.borderColor}, rgba(255,255,255,0.2), ${config.borderColor})`
          : `linear-gradient(135deg, ${config.borderColor} 0%, rgba(255,255,255,0.1) 50%, ${config.borderColor} 100%)`,
        boxShadow: selected
          ? `${config.shadowColor}, 0 8px 32px rgba(0,0,0,0.4)`
          : `0 4px 24px rgba(0,0,0,0.3)`,
      }}
    >
      {/* Inner content with glass effect */}
      <div
        className={cn(
          "relative rounded-xl p-4",
          "backdrop-blur-xl",
          "transition-all duration-300"
        )}
        style={{
          background: "linear-gradient(135deg, rgba(20, 20, 30, 0.9) 0%, rgba(10, 10, 15, 0.95) 100%)",
          boxShadow: "inset 0 1px 0 rgba(255,255,255,0.05), inset 0 -1px 0 rgba(0,0,0,0.3)",
        }}
      >
        {/* Glow effect on hover/selected */}
        <div
          className={cn(
            "absolute inset-0 rounded-xl opacity-0 transition-opacity duration-300",
            "group-hover:opacity-100",
            selected && "opacity-100"
          )}
          style={{
            background: `radial-gradient(ellipse at 50% 0%, ${config.glowColor} 0%, transparent 60%)`,
          }}
        />

        {/* Input Handle */}
        {config.hasInputHandle && (
          <Handle
            type="target"
            position={Position.Left}
            className={cn(
              "!w-3.5 !h-3.5 !rounded-full !border-2 !-left-[7px]",
              "!transition-all !duration-200",
              "hover:!scale-125"
            )}
            style={{
              background: "#14141f",
              borderColor: config.handleColor,
              boxShadow: `0 0 8px ${config.glowColor}`,
            }}
          />
        )}

        {/* Node Content */}
        <div className="relative z-10">
          {/* Header with icon and title */}
          <div className="flex items-center gap-3 mb-2">
            <div
              className="flex items-center justify-center w-9 h-9 rounded-lg transition-transform duration-200 group-hover:scale-110"
              style={{
                background: config.iconBgColor,
                boxShadow: `0 0 12px ${config.glowColor}`,
              }}
            >
              <Icon
                className="w-5 h-5 transition-all duration-200"
                style={{ color: config.iconColor }}
              />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-white/95 truncate">
                {title}
              </div>
            </div>
          </div>

          {/* Description */}
          {description && (
            <p className="text-xs text-white/50 truncate pl-12 -mt-1">
              {description}
            </p>
          )}
        </div>

        {/* Output Handle(s) */}
        {config.hasOutputHandle && (
          <>
            {config.outputHandleCount === 2 ? (
              // Condition node has two output handles
              <>
                <Handle
                  type="source"
                  position={Position.Right}
                  id="true"
                  className={cn(
                    "!w-3.5 !h-3.5 !rounded-full !border-2 !-right-[7px] !top-[35%]",
                    "!transition-all !duration-200",
                    "hover:!scale-125"
                  )}
                  style={{
                    background: "#14141f",
                    borderColor: config.handleColor,
                    boxShadow: `0 0 8px ${config.glowColor}`,
                  }}
                />
                <Handle
                  type="source"
                  position={Position.Right}
                  id="false"
                  className={cn(
                    "!w-3.5 !h-3.5 !rounded-full !border-2 !-right-[7px] !top-[65%]",
                    "!transition-all !duration-200",
                    "hover:!scale-125"
                  )}
                  style={{
                    background: "#14141f",
                    borderColor: "rgba(148, 163, 184, 0.6)",
                    boxShadow: "0 0 8px rgba(148, 163, 184, 0.3)",
                  }}
                />
                {/* Handle labels */}
                <div className="absolute -right-1 top-[35%] translate-x-full -translate-y-1/2 text-[9px] text-white/40 pl-3 pointer-events-none">
                  True
                </div>
                <div className="absolute -right-1 top-[65%] translate-x-full -translate-y-1/2 text-[9px] text-white/40 pl-3 pointer-events-none">
                  False
                </div>
              </>
            ) : (
              <Handle
                type="source"
                position={Position.Right}
                className={cn(
                  "!w-3.5 !h-3.5 !rounded-full !border-2 !-right-[7px]",
                  "!transition-all !duration-200",
                  "hover:!scale-125"
                )}
                style={{
                  background: "#14141f",
                  borderColor: config.handleColor,
                  boxShadow: `0 0 8px ${config.glowColor}`,
                }}
              />
            )}
          </>
        )}

        {/* Type indicator pill */}
        <div
          className="absolute -top-2 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded-full text-[9px] font-medium uppercase tracking-wider"
          style={{
            background: config.iconBgColor,
            color: config.iconColor,
            boxShadow: `0 2px 8px ${config.glowColor}`,
          }}
        >
          {type}
        </div>
      </div>
    </div>
  );
}

// Memoize to prevent unnecessary re-renders
export const WorkflowNode = memo(WorkflowNodeComponent);
WorkflowNode.displayName = "WorkflowNode";

// Export node types map for ReactFlow
export const workflowNodeTypes = {
  workflowNode: WorkflowNode,
};

export default WorkflowNode;
