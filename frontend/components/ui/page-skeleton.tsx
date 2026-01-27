import * as React from "react";
import { cn } from "@/lib/utils";
import { Skeleton } from "./skeleton";

// ============================================================================
// Page Skeleton Variants
// ============================================================================

export type PageSkeletonVariant = "list" | "card-grid" | "form" | "table";

export interface PageSkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /** The layout variant for the skeleton */
  variant: PageSkeletonVariant;
  /** Number of items to show (applies to list, card-grid, table rows) */
  count?: number;
  /** Whether to show the page header skeleton */
  showHeader?: boolean;
  /** Custom header title width (e.g., "w-40", "w-64") */
  headerWidth?: string;
}

// ============================================================================
// Sub-components
// ============================================================================

interface PageHeaderSkeletonProps {
  titleWidth?: string;
  showDescription?: boolean;
  showAction?: boolean;
}

function PageHeaderSkeleton({
  titleWidth = "w-40",
  showDescription = true,
  showAction = false,
}: PageHeaderSkeletonProps) {
  return (
    <div className="flex items-center justify-between">
      <div className="space-y-2">
        <Skeleton className={cn("h-8", titleWidth)} />
        {showDescription && <Skeleton className="h-4 w-64" />}
      </div>
      {showAction && <Skeleton className="h-9 w-24" />}
    </div>
  );
}

// ============================================================================
// List Skeleton
// ============================================================================

interface ListSkeletonProps {
  count: number;
}

function ListSkeleton({ count }: ListSkeletonProps) {
  return (
    <div className="border border-border bg-card divide-y divide-border">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="p-6 flex items-start gap-6">
          {/* Index number */}
          <Skeleton className="h-5 w-8 flex-shrink-0" />

          {/* Content */}
          <div className="flex-1 min-w-0 space-y-3">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 space-y-2">
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
              {/* Status badge */}
              <Skeleton className="h-7 w-24 flex-shrink-0" />
            </div>
            {/* Additional content preview */}
            <div className="pl-4 border-l-2 border-border space-y-2">
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-4/5" />
            </div>
          </div>

          {/* Actions */}
          <Skeleton className="h-10 w-10 flex-shrink-0" />
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// Card Grid Skeleton
// ============================================================================

interface CardGridSkeletonProps {
  count: number;
}

function CardGridSkeleton({ count }: CardGridSkeletonProps) {
  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="border border-border bg-card p-6 space-y-4">
          {/* Card header */}
          <div className="flex items-center justify-between">
            <Skeleton className="h-5 w-2/3" />
            <Skeleton className="h-6 w-20" />
          </div>

          {/* Card content */}
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-4/5" />
          </div>

          {/* Card meta */}
          <div className="flex items-center gap-4 pt-2">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-3 w-20" />
          </div>

          {/* Card actions */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
            <Skeleton className="h-8 w-20" />
            <Skeleton className="h-8 w-8" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// Form Skeleton
// ============================================================================

function FormSkeleton() {
  return (
    <div className="border border-border bg-card p-8 space-y-8 max-w-2xl">
      {/* Form section 1 */}
      <div className="space-y-4">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-3 w-48" />
      </div>

      {/* Form section 2 */}
      <div className="space-y-4">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-24 w-full" />
      </div>

      {/* Form section 3 - two columns */}
      <div className="grid gap-6 sm:grid-cols-2">
        <div className="space-y-4">
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-10 w-full" />
        </div>
        <div className="space-y-4">
          <Skeleton className="h-5 w-28" />
          <Skeleton className="h-10 w-full" />
        </div>
      </div>

      {/* Form actions */}
      <div className="flex items-center justify-end gap-4 pt-4 border-t border-border">
        <Skeleton className="h-10 w-24" />
        <Skeleton className="h-10 w-32" />
      </div>
    </div>
  );
}

// ============================================================================
// Table Skeleton
// ============================================================================

interface TableSkeletonProps {
  count: number;
}

function TableSkeleton({ count }: TableSkeletonProps) {
  return (
    <div className="border border-border bg-card overflow-hidden">
      {/* Table header */}
      <div className="p-4 border-b border-border bg-muted/30 flex items-center gap-4">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-16 ml-auto" />
      </div>

      {/* Table filters */}
      <div className="p-4 border-b border-border flex gap-4">
        <Skeleton className="h-9 w-40" />
        <Skeleton className="h-9 w-40" />
      </div>

      {/* Table rows */}
      <div className="divide-y divide-border">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="p-4 flex items-center gap-4">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-6 w-24" />
            <Skeleton className="h-2 w-24" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-8 w-8 ml-auto" />
          </div>
        ))}
      </div>

      {/* Table pagination */}
      <div className="p-4 border-t border-border flex items-center justify-between">
        <Skeleton className="h-4 w-32" />
        <div className="flex gap-2">
          <Skeleton className="h-8 w-20" />
          <Skeleton className="h-8 w-20" />
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Main PageSkeleton Component
// ============================================================================

/**
 * A reusable page loading skeleton component with multiple layout variants.
 *
 * @example
 * ```tsx
 * // List layout (for document lists, job lists, etc.)
 * <PageSkeleton variant="list" count={5} />
 *
 * // Card grid layout (for dashboards, galleries)
 * <PageSkeleton variant="card-grid" count={6} />
 *
 * // Form layout (for settings, edit pages)
 * <PageSkeleton variant="form" showHeader />
 *
 * // Table layout (for data tables, executions list)
 * <PageSkeleton variant="table" count={10} />
 * ```
 */
export function PageSkeleton({
  variant,
  count = 5,
  showHeader = true,
  headerWidth = "w-40",
  className,
  ...props
}: PageSkeletonProps) {
  return (
    <div className={cn("space-y-8", className)} {...props}>
      {showHeader && (
        <PageHeaderSkeleton
          titleWidth={headerWidth}
          showDescription={variant !== "form"}
          showAction={variant === "table" || variant === "card-grid"}
        />
      )}

      {variant === "list" && <ListSkeleton count={count} />}
      {variant === "card-grid" && <CardGridSkeleton count={count} />}
      {variant === "form" && <FormSkeleton />}
      {variant === "table" && <TableSkeleton count={count} />}
    </div>
  );
}

// ============================================================================
// Export sub-components for custom compositions
// ============================================================================

export {
  PageHeaderSkeleton,
  ListSkeleton,
  CardGridSkeleton,
  FormSkeleton,
  TableSkeleton,
};
