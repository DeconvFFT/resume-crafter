import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import {
  Clock,
  Loader2,
  Play,
  Pause,
  CheckCircle2,
  AlertCircle,
  XCircle,
  FileEdit,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ============================================================================
// Status Type Definition
// ============================================================================

export type StatusType =
  | "pending"
  | "processing"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "paused"
  | "active"
  | "draft";

// ============================================================================
// Status Configuration
// ============================================================================

interface StatusConfig {
  icon: LucideIcon;
  label: string;
  /** Whether the icon should animate (spin) */
  animate?: boolean;
}

/**
 * Status configuration with WCAG AA compliant colors.
 * Colors use explicit values for better contrast ratios:
 * - Light mode: darker text colors (600 level)
 * - Dark mode: lighter text colors (400 level)
 * - Background: semi-transparent (10% opacity)
 * - Border: semi-transparent (30% opacity)
 */
const statusConfig: Record<StatusType, StatusConfig> = {
  pending: {
    icon: Clock,
    label: "Pending",
  },
  processing: {
    icon: Loader2,
    label: "Processing",
    animate: true,
  },
  running: {
    icon: Play,
    label: "Running",
    animate: true,
  },
  completed: {
    icon: CheckCircle2,
    label: "Completed",
  },
  failed: {
    icon: AlertCircle,
    label: "Failed",
  },
  cancelled: {
    icon: XCircle,
    label: "Cancelled",
  },
  paused: {
    icon: Pause,
    label: "Paused",
  },
  active: {
    icon: Zap,
    label: "Active",
  },
  draft: {
    icon: FileEdit,
    label: "Draft",
  },
};

// ============================================================================
// Status Badge Variants (using class-variance-authority)
// ============================================================================

const statusBadgeVariants = cva(
  // Base styles - consistent across all variants
  "inline-flex items-center gap-1.5 border font-medium transition-colors",
  {
    variants: {
      status: {
        // Pending: Amber/Yellow - WCAG AA compliant
        pending:
          "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/30",
        // Processing: Blue - WCAG AA compliant
        processing:
          "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/30",
        // Running: Blue (same as processing) - WCAG AA compliant
        running:
          "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/30",
        // Completed: Green - WCAG AA compliant
        completed:
          "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30",
        // Failed: Red - WCAG AA compliant
        failed:
          "bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/30",
        // Cancelled: Gray - WCAG AA compliant
        cancelled:
          "bg-gray-500/10 text-gray-700 dark:text-gray-400 border-gray-500/30",
        // Paused: Amber/Orange - WCAG AA compliant
        paused:
          "bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/30",
        // Active: Green (same as completed) - WCAG AA compliant
        active:
          "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30",
        // Draft: Slate/Gray - WCAG AA compliant
        draft:
          "bg-slate-500/10 text-slate-700 dark:text-slate-400 border-slate-500/30",
      },
      size: {
        sm: "px-2 py-0.5 text-xs rounded",
        md: "px-2.5 py-1 text-xs rounded-md",
      },
    },
    defaultVariants: {
      size: "md",
    },
  }
);

// ============================================================================
// Component Props
// ============================================================================

export interface StatusBadgeProps
  extends Omit<React.HTMLAttributes<HTMLSpanElement>, "children">,
    VariantProps<typeof statusBadgeVariants> {
  /** The status to display */
  status: StatusType;
  /** Size variant: sm or md (default: md) */
  size?: "sm" | "md";
  /** Whether to show the status icon (default: true) */
  showIcon?: boolean;
  /** Custom label override (uses default label if not provided) */
  label?: string;
}

// ============================================================================
// StatusBadge Component
// ============================================================================

/**
 * A unified status badge component for displaying various statuses
 * throughout the application with consistent styling and accessibility.
 *
 * @example
 * ```tsx
 * <StatusBadge status="completed" />
 * <StatusBadge status="processing" size="sm" />
 * <StatusBadge status="failed" showIcon={false} />
 * <StatusBadge status="pending" label="Queued" />
 * ```
 */
export function StatusBadge({
  status,
  size = "md",
  showIcon = true,
  label,
  className,
  ...props
}: StatusBadgeProps) {
  const config = statusConfig[status];
  const Icon = config.icon;
  const displayLabel = label ?? config.label;
  const shouldAnimate = config.animate;

  // Icon size based on badge size
  const iconSize = size === "sm" ? "h-3 w-3" : "h-3.5 w-3.5";

  return (
    <span
      className={cn(statusBadgeVariants({ status, size }), className)}
      role="status"
      aria-label={`Status: ${displayLabel}`}
      {...props}
    >
      {showIcon && (
        <Icon
          className={cn(iconSize, shouldAnimate && "animate-spin")}
          aria-hidden="true"
        />
      )}
      <span className="font-mono uppercase tracking-wider">{displayLabel}</span>
    </span>
  );
}

// ============================================================================
// Utility: Get status config (for custom implementations)
// ============================================================================

/**
 * Returns the configuration for a given status.
 * Useful when you need to access status metadata outside the component.
 */
export function getStatusConfig(status: StatusType): StatusConfig {
  return statusConfig[status];
}

/**
 * Type guard to check if a string is a valid StatusType
 */
export function isValidStatus(value: string): value is StatusType {
  return Object.keys(statusConfig).includes(value);
}
