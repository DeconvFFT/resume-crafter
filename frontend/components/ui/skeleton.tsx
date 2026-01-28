"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Animation variant */
  variant?: "shimmer" | "pulse" | "wave";
}

function Skeleton({ className, variant = "shimmer", ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        // Base skeleton styles
        "rounded-md",
        // Variant styles
        {
          // Shimmer - gradient sweep animation
          "bg-gradient-to-r from-muted via-muted/50 to-muted dark:from-muted dark:via-muted/70 dark:to-muted bg-[length:200%_100%] animate-shimmer":
            variant === "shimmer",
          // Pulse - subtle opacity animation
          "bg-muted animate-pulse-subtle": variant === "pulse",
          // Wave - moving wave effect
          "bg-muted relative overflow-hidden before:absolute before:inset-0 before:bg-gradient-to-r before:from-transparent before:via-white/10 before:to-transparent before:animate-[shimmer_1.5s_infinite]":
            variant === "wave",
        },
        className
      )}
      {...props}
    />
  );
}

// Preset skeleton variants for common use cases
function SkeletonText({ className, ...props }: SkeletonProps) {
  return <Skeleton className={cn("h-4 w-full", className)} {...props} />;
}

function SkeletonCircle({ className, ...props }: SkeletonProps) {
  return <Skeleton className={cn("h-10 w-10 rounded-full", className)} {...props} />;
}

function SkeletonCard({ className, ...props }: SkeletonProps) {
  return (
    <div className={cn("space-y-3", className)} {...props}>
      <Skeleton className="h-32 w-full" />
      <div className="space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    </div>
  );
}

// Skeleton that transitions to content
interface SkeletonWithContentProps {
  isLoading: boolean;
  skeleton: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

function SkeletonWithContent({
  isLoading,
  skeleton,
  children,
  className,
}: SkeletonWithContentProps) {
  return (
    <div className={cn("relative", className)}>
      <AnimatePresence mode="wait">
        {isLoading ? (
          <motion.div
            key="skeleton"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {skeleton}
          </motion.div>
        ) : (
          <motion.div
            key="content"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3, delay: 0.1 }}
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Inline skeleton for text placeholders
interface SkeletonInlineProps {
  width?: string | number;
  height?: string | number;
  className?: string;
}

function SkeletonInline({
  width = "100px",
  height = "1em",
  className,
}: SkeletonInlineProps) {
  return (
    <Skeleton
      className={cn("inline-block align-middle", className)}
      style={{ width, height }}
    />
  );
}

// Skeleton list for loading states
interface SkeletonListProps {
  count?: number;
  className?: string;
  itemClassName?: string;
}

function SkeletonList({
  count = 3,
  className,
  itemClassName,
}: SkeletonListProps) {
  return (
    <div className={cn("space-y-3", className)}>
      {Array.from({ length: count }).map((_, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: i * 0.05 }}
          className={cn("flex items-center gap-3", itemClassName)}
        >
          <Skeleton className="h-10 w-10 rounded-lg shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </motion.div>
      ))}
    </div>
  );
}

// Skeleton table for data table loading
interface SkeletonTableProps {
  rows?: number;
  columns?: number;
  className?: string;
}

function SkeletonTable({
  rows = 5,
  columns = 4,
  className,
}: SkeletonTableProps) {
  return (
    <div className={cn("space-y-4", className)}>
      {/* Header */}
      <div className="flex gap-4 pb-2 border-b border-border">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} className="h-4 flex-1" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <motion.div
          key={rowIndex}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: rowIndex * 0.05 }}
          className="flex gap-4"
        >
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton
              key={colIndex}
              className="h-4 flex-1"
              style={{ width: `${Math.random() * 30 + 50}%` }}
            />
          ))}
        </motion.div>
      ))}
    </div>
  );
}

export {
  Skeleton,
  SkeletonText,
  SkeletonCircle,
  SkeletonCard,
  SkeletonWithContent,
  SkeletonInline,
  SkeletonList,
  SkeletonTable,
};
