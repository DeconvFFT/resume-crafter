"use client";

import * as React from "react";
import { useState, useMemo, CSSProperties } from "react";
import {
  Zap,
  Calendar,
  MousePointer,
  FileText,
  FormInput,
  Mail,
  GitBranch,
  Clock,
  Filter,
  Send,
  Save,
  Bell,
  ChevronDown,
  ChevronRight,
  Search,
  GripVertical,
  LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

// Node category types
export type NodeCategory = "trigger" | "action" | "logic" | "output";

// Node type definition
export interface NodeType {
  id: string;
  label: string;
  category: NodeCategory;
  icon: LucideIcon;
  description: string;
  color: string;
}

// Executive Noir color configuration
const categoryColors: Record<NodeCategory, {
  bg: string;
  text: string;
  glow: string;
  border: string;
}> = {
  trigger: {
    bg: "rgba(245, 158, 11, 0.12)",
    text: "#F59E0B",
    glow: "rgba(245, 158, 11, 0.3)",
    border: "rgba(245, 158, 11, 0.3)",
  },
  action: {
    bg: "rgba(139, 92, 246, 0.12)",
    text: "#8B5CF6",
    glow: "rgba(139, 92, 246, 0.3)",
    border: "rgba(139, 92, 246, 0.3)",
  },
  logic: {
    bg: "rgba(20, 184, 166, 0.12)",
    text: "#14B8A6",
    glow: "rgba(20, 184, 166, 0.3)",
    border: "rgba(20, 184, 166, 0.3)",
  },
  output: {
    bg: "rgba(34, 197, 94, 0.12)",
    text: "#22C55E",
    glow: "rgba(34, 197, 94, 0.3)",
    border: "rgba(34, 197, 94, 0.3)",
  },
};

// All available node types
export const nodeTypes: NodeType[] = [
  // Triggers
  {
    id: "new-job-found",
    label: "New Job Found",
    category: "trigger",
    icon: Zap,
    description: "Triggers when a new job posting is detected",
    color: "node-trigger",
  },
  {
    id: "schedule",
    label: "Schedule",
    category: "trigger",
    icon: Calendar,
    description: "Triggers on a recurring schedule",
    color: "node-trigger",
  },
  {
    id: "manual-trigger",
    label: "Manual Trigger",
    category: "trigger",
    icon: MousePointer,
    description: "Triggers manually when you start the workflow",
    color: "node-trigger",
  },
  // Actions
  {
    id: "generate-resume",
    label: "Generate Resume",
    category: "action",
    icon: FileText,
    description: "Creates a tailored resume for the job",
    color: "node-action",
  },
  {
    id: "fill-application",
    label: "Fill Application",
    category: "action",
    icon: FormInput,
    description: "Auto-fills job application forms",
    color: "node-action",
  },
  {
    id: "send-email-draft",
    label: "Send Email Draft",
    category: "action",
    icon: Mail,
    description: "Creates an email draft for follow-up",
    color: "node-action",
  },
  // Logic
  {
    id: "condition",
    label: "Condition",
    category: "logic",
    icon: GitBranch,
    description: "Branch workflow based on conditions",
    color: "node-condition",
  },
  {
    id: "delay",
    label: "Delay",
    category: "logic",
    icon: Clock,
    description: "Wait for a specified time before continuing",
    color: "node-condition",
  },
  {
    id: "filter",
    label: "Filter",
    category: "logic",
    icon: Filter,
    description: "Filter data based on criteria",
    color: "node-condition",
  },
  // Outputs
  {
    id: "apply-to-job",
    label: "Apply to Job",
    category: "output",
    icon: Send,
    description: "Submits the job application",
    color: "node-output",
  },
  {
    id: "save-draft",
    label: "Save Draft",
    category: "output",
    icon: Save,
    description: "Saves the resume or application as a draft",
    color: "node-output",
  },
  {
    id: "notify-user",
    label: "Notify User",
    category: "output",
    icon: Bell,
    description: "Sends a notification to the user",
    color: "node-output",
  },
];

// Category configuration
interface CategoryConfig {
  id: NodeCategory;
  label: string;
  description: string;
}

const categories: CategoryConfig[] = [
  { id: "trigger", label: "Triggers", description: "Start your workflow" },
  { id: "action", label: "Actions", description: "Process data" },
  { id: "logic", label: "Logic", description: "Control flow" },
  { id: "output", label: "Outputs", description: "Complete tasks" },
];

// Draggable node item props
interface DraggableNodeItemProps {
  nodeType: NodeType;
  onDragStart?: (nodeType: NodeType) => void;
}

function DraggableNodeItem({ nodeType, onDragStart }: DraggableNodeItemProps) {
  const Icon = nodeType.icon;
  const colors = categoryColors[nodeType.category];

  const handleDragStart = (e: React.DragEvent<HTMLDivElement>) => {
    // Set drag data for the workflow canvas
    e.dataTransfer.setData("application/workflow-node", JSON.stringify(nodeType));
    e.dataTransfer.effectAllowed = "copy";

    // Optional callback
    onDragStart?.(nodeType);
  };

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      className={cn(
        "group flex items-center gap-3 p-3 rounded-lg cursor-grab",
        "transition-all duration-200",
        "active:cursor-grabbing active:scale-[0.98]",
      )}
      style={{
        background: "rgba(255, 255, 255, 0.02)",
        border: "1px solid rgba(255, 255, 255, 0.06)",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)";
        e.currentTarget.style.borderColor = colors.border;
        e.currentTarget.style.boxShadow = `0 0 20px ${colors.glow}`;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "rgba(255, 255, 255, 0.02)";
        e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.06)";
        e.currentTarget.style.boxShadow = "none";
      }}
      role="button"
      aria-label={`Drag ${nodeType.label} node to canvas`}
      tabIndex={0}
    >
      <div className="flex items-center gap-2.5 flex-1 min-w-0">
        <div
          className="flex items-center justify-center w-8 h-8 rounded-lg transition-transform duration-200 group-hover:scale-110"
          style={{
            background: colors.bg,
            boxShadow: `0 0 12px ${colors.glow}`,
          }}
        >
          <Icon
            className="h-4 w-4"
            style={{ color: colors.text }}
          />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-white/90 truncate">{nodeType.label}</p>
          <p className="text-[11px] text-white/40 truncate">
            {nodeType.description}
          </p>
        </div>
      </div>
      <GripVertical className="h-4 w-4 text-white/20 opacity-0 group-hover:opacity-100 transition-opacity" />
    </div>
  );
}

// Category section props
interface CategorySectionProps {
  category: CategoryConfig;
  nodes: NodeType[];
  isOpen: boolean;
  onToggle: () => void;
  onDragStart?: (nodeType: NodeType) => void;
}

function CategorySection({
  category,
  nodes,
  isOpen,
  onToggle,
  onDragStart,
}: CategorySectionProps) {
  const colors = categoryColors[category.id];

  return (
    <Collapsible open={isOpen} onOpenChange={onToggle}>
      <CollapsibleTrigger
        className="flex items-center justify-between w-full p-3 rounded-lg transition-all duration-200 group"
        style={{
          background: isOpen ? "rgba(255, 255, 255, 0.03)" : "transparent",
        }}
        onMouseEnter={(e) => {
          if (!isOpen) {
            e.currentTarget.style.background = "rgba(255, 255, 255, 0.03)";
          }
        }}
        onMouseLeave={(e) => {
          if (!isOpen) {
            e.currentTarget.style.background = "transparent";
          }
        }}
      >
        <div className="flex items-center gap-2">
          {isOpen ? (
            <ChevronDown className="h-4 w-4 text-white/50" />
          ) : (
            <ChevronRight className="h-4 w-4 text-white/50" />
          )}
          <div className="text-left">
            <span
              className="font-mono text-[10px] uppercase tracking-widest font-medium"
              style={{ color: colors.text }}
            >
              {category.label}
            </span>
            <p className="text-[11px] text-white/40">{category.description}</p>
          </div>
        </div>
        <span
          className="text-[10px] font-medium px-2 py-0.5 rounded-full"
          style={{
            background: colors.bg,
            color: colors.text,
          }}
        >
          {nodes.length}
        </span>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="pl-6 pr-2 pb-2 space-y-1.5 mt-1">
          {nodes.map((node) => (
            <DraggableNodeItem
              key={node.id}
              nodeType={node}
              onDragStart={onDragStart}
            />
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

// Main NodePanel props
export interface NodePanelProps {
  className?: string;
  style?: CSSProperties;
  onDragStart?: (nodeType: NodeType) => void;
  onNodeSelect?: (nodeType: NodeType) => void;
}

export function NodePanel({ className, style, onDragStart, onNodeSelect }: NodePanelProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [openCategories, setOpenCategories] = useState<Set<NodeCategory>>(
    new Set<NodeCategory>(["trigger", "action", "logic", "output"])
  );

  // Filter nodes based on search query
  const filteredNodes = useMemo(() => {
    if (!searchQuery.trim()) {
      return nodeTypes;
    }
    const query = searchQuery.toLowerCase();
    return nodeTypes.filter(
      (node) =>
        node.label.toLowerCase().includes(query) ||
        node.description.toLowerCase().includes(query)
    );
  }, [searchQuery]);

  // Group filtered nodes by category
  const nodesByCategory = useMemo(() => {
    const grouped: Record<NodeCategory, NodeType[]> = {
      trigger: [],
      action: [],
      logic: [],
      output: [],
    };
    filteredNodes.forEach((node) => {
      grouped[node.category].push(node);
    });
    return grouped;
  }, [filteredNodes]);

  const toggleCategory = (category: NodeCategory) => {
    setOpenCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  const handleDragStart = (nodeType: NodeType) => {
    onDragStart?.(nodeType);
  };

  return (
    <div
      className={cn(
        "flex flex-col h-full w-64",
        className
      )}
      style={{
        background: "linear-gradient(180deg, rgba(15, 15, 20, 0.98) 0%, rgba(10, 10, 15, 0.98) 100%)",
        ...style,
      }}
    >
      {/* Header */}
      <div
        className="p-4"
        style={{
          borderBottom: "1px solid rgba(255, 255, 255, 0.06)",
        }}
      >
        <h2 className="font-semibold text-base text-white/95">Nodes</h2>
        <p className="text-xs text-white/40 mt-0.5">
          Drag nodes to the canvas
        </p>
      </div>

      {/* Search */}
      <div
        className="p-3"
        style={{
          borderBottom: "1px solid rgba(255, 255, 255, 0.06)",
        }}
      >
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30" />
          <Input
            type="text"
            placeholder="Search nodes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 h-9 text-sm bg-white/5 border-white/10 text-white placeholder:text-white/30 focus:border-primary/50"
          />
        </div>
      </div>

      {/* Node Categories */}
      <div className="flex-1 overflow-y-auto p-2 scrollbar-thin">
        {filteredNodes.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Search className="h-8 w-8 text-white/20 mb-2" />
            <p className="text-sm text-white/50">No nodes found</p>
            <p className="text-[11px] text-white/30 mt-1">
              Try a different search term
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {categories.map((category) => {
              const nodes = nodesByCategory[category.id];
              if (nodes.length === 0) return null;
              return (
                <CategorySection
                  key={category.id}
                  category={category}
                  nodes={nodes}
                  isOpen={openCategories.has(category.id)}
                  onToggle={() => toggleCategory(category.id)}
                  onDragStart={handleDragStart}
                />
              );
            })}
          </div>
        )}
      </div>

      {/* Footer hint */}
      <div
        className="p-3"
        style={{
          borderTop: "1px solid rgba(255, 255, 255, 0.06)",
          background: "rgba(255, 255, 255, 0.02)",
        }}
      >
        <p className="text-[11px] text-white/30 text-center">
          Drag and drop nodes onto the canvas to build your workflow
        </p>
      </div>
    </div>
  );
}

export default NodePanel;
