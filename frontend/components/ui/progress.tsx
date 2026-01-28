"use client";

import * as React from "react";
import * as ProgressPrimitive from "@radix-ui/react-progress";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface ProgressProps
  extends React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root> {
  /** Show animated gradient effect */
  animated?: boolean;
  /** Show striped pattern */
  striped?: boolean;
  /** Show indeterminate loading */
  indeterminate?: boolean;
  /** Color variant */
  variant?: "default" | "success" | "warning" | "destructive" | "gradient";
  /** Show percentage label */
  showLabel?: boolean;
  /** Size variant */
  size?: "sm" | "md" | "lg";
}

const Progress = React.forwardRef<
  React.ElementRef<typeof ProgressPrimitive.Root>,
  ProgressProps
>(
  (
    {
      className,
      value,
      animated = false,
      striped = false,
      indeterminate = false,
      variant = "default",
      showLabel = false,
      size = "md",
      ...props
    },
    ref
  ) => {
    const sizeClasses = {
      sm: "h-1",
      md: "h-2",
      lg: "h-3",
    };

    const variantClasses = {
      default: "bg-primary",
      success: "bg-success",
      warning: "bg-warning",
      destructive: "bg-destructive",
      gradient: "bg-gradient-to-r from-primary via-primary/80 to-primary",
    };

    return (
      <div className={cn("relative", showLabel && "pb-6")}>
        <ProgressPrimitive.Root
          ref={ref}
          className={cn(
            "relative w-full overflow-hidden rounded-full bg-primary/20",
            sizeClasses[size],
            className
          )}
          {...props}
        >
          {indeterminate ? (
            <motion.div
              className={cn(
                "h-full w-1/3 rounded-full",
                variantClasses[variant]
              )}
              animate={{
                x: ["-100%", "400%"],
              }}
              transition={{
                duration: 1.2,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            />
          ) : (
            <ProgressPrimitive.Indicator
              className={cn(
                "h-full w-full flex-1 rounded-full transition-all duration-500 ease-out",
                variantClasses[variant],
                // Animated shimmer effect
                animated &&
                  "relative overflow-hidden after:absolute after:inset-0 after:bg-gradient-to-r after:from-transparent after:via-white/20 after:to-transparent after:animate-[shimmer_2s_infinite]",
                // Striped pattern
                striped &&
                  "bg-[length:1rem_1rem] bg-[linear-gradient(45deg,rgba(255,255,255,0.15)_25%,transparent_25%,transparent_50%,rgba(255,255,255,0.15)_50%,rgba(255,255,255,0.15)_75%,transparent_75%,transparent)]"
              )}
              style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
            />
          )}
        </ProgressPrimitive.Root>

        {/* Label */}
        {showLabel && !indeterminate && (
          <motion.div
            className="absolute -bottom-0.5 text-xs font-medium text-muted-foreground"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            style={{ left: `${Math.min(value || 0, 95)}%` }}
          >
            {value}%
          </motion.div>
        )}
      </div>
    );
  }
);
Progress.displayName = ProgressPrimitive.Root.displayName;

// Circular progress variant
interface CircularProgressProps {
  value: number;
  size?: number;
  strokeWidth?: number;
  className?: string;
  showLabel?: boolean;
  variant?: "default" | "success" | "warning" | "destructive" | "gradient";
}

function CircularProgress({
  value,
  size = 64,
  strokeWidth = 4,
  className,
  showLabel = false,
  variant = "default",
}: CircularProgressProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (value / 100) * circumference;

  const colorClasses = {
    default: "text-primary",
    success: "text-success",
    warning: "text-warning",
    destructive: "text-destructive",
    gradient: "text-primary",
  };

  return (
    <div className={cn("relative inline-flex", className)}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-primary/20"
        />
        {/* Progress circle */}
        {variant === "gradient" ? (
          <>
            <defs>
              <linearGradient id="progress-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="hsl(var(--primary))" />
                <stop offset="100%" stopColor="hsl(var(--primary) / 0.6)" />
              </linearGradient>
            </defs>
            <motion.circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="url(#progress-gradient)"
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset: offset }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              style={{
                strokeDasharray: circumference,
              }}
            />
          </>
        ) : (
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            className={colorClasses[variant]}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            style={{
              strokeDasharray: circumference,
            }}
          />
        )}
      </svg>
      {showLabel && (
        <div className="absolute inset-0 flex items-center justify-center">
          <motion.span
            className="text-sm font-semibold"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3 }}
          >
            {value}%
          </motion.span>
        </div>
      )}
    </div>
  );
}

export { Progress, CircularProgress };
