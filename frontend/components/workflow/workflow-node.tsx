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

// Node type configurations
const nodeTypeConfig: Record<
  WorkflowNodeType,
  {
    borderColor: string;
    iconColor: string;
    handleColor: string;
    hasInputHandle: boolean;
    hasOutputHandle: boolean;
    outputHandleCount?: number;
  }
> = {
  trigger: {
    borderColor: "border-node-trigger",
    iconColor: "text-node-trigger",
    handleColor: "!bg-node-trigger",
    hasInputHandle: false,
    hasOutputHandle: true,
  },
  action: {
    borderColor: "border-node-action",
    iconColor: "text-node-action",
    handleColor: "!bg-node-action",
    hasInputHandle: true,
    hasOutputHandle: true,
  },
  condition: {
    borderColor: "border-node-condition",
    iconColor: "text-node-condition",
    handleColor: "!bg-node-condition",
    hasInputHandle: true,
    hasOutputHandle: true,
    outputHandleCount: 2, // true/false branches
  },
  output: {
    borderColor: "border-node-output",
    iconColor: "text-node-output",
    handleColor: "!bg-node-output",
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
        "workflow-node",
        config.borderColor,
        selected && "workflow-node-selected",
        "animate-node-appear"
      )}
    >
      {/* Input Handle */}
      {config.hasInputHandle && (
        <Handle
          type="target"
          position={Position.Left}
          className={cn(
            "workflow-handle",
            config.handleColor,
            "!-left-1.5"
          )}
        />
      )}

      {/* Node Content */}
      <div className="workflow-node-header">
        <div
          className={cn(
            "flex items-center justify-center w-7 h-7 rounded-md",
            "bg-muted"
          )}
        >
          <Icon className={cn("workflow-node-icon", config.iconColor)} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="workflow-node-title">{title}</div>
        </div>
      </div>

      {description && (
        <p className="workflow-node-description">{description}</p>
      )}

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
                  "workflow-handle",
                  config.handleColor,
                  "!-right-1.5 !top-1/3"
                )}
              />
              <Handle
                type="source"
                position={Position.Right}
                id="false"
                className={cn(
                  "workflow-handle",
                  "!bg-muted-foreground",
                  "!-right-1.5 !top-2/3"
                )}
              />
            </>
          ) : (
            <Handle
              type="source"
              position={Position.Right}
              className={cn(
                "workflow-handle",
                config.handleColor,
                "!-right-1.5"
              )}
            />
          )}
        </>
      )}
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
