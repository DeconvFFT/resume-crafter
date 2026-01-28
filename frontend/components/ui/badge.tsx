"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { motion, AnimatePresence, type HTMLMotionProps } from "framer-motion";
import { cn } from "@/lib/utils";
import { X } from "lucide-react";

const badgeVariants = cva(
  // Modern SaaS badge - rounded pill style with smooth transitions
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        // Default - primary color fill
        default:
          "border-transparent bg-primary text-primary-foreground shadow-sm hover:bg-primary/80",
        // Secondary - subtle background
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        // Success - green tint
        success:
          "border-transparent bg-success/10 text-success hover:bg-success/20",
        // Warning - amber tint
        warning:
          "border-transparent bg-warning/10 text-warning hover:bg-warning/20",
        // Destructive - red
        destructive:
          "border-transparent bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/80",
        // Info - blue tint
        info: "border-transparent bg-info/10 text-info hover:bg-info/20",
        // Outline - border only
        outline:
          "text-foreground hover:bg-accent",
        // Glow - with subtle glow effect
        glow:
          "border-transparent bg-primary text-primary-foreground shadow-sm hover:shadow-md hover:shadow-primary/25",
      },
      size: {
        sm: "px-2 py-0.5 text-[10px]",
        default: "px-2.5 py-0.5 text-xs",
        lg: "px-3 py-1 text-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  /** Enable animated entrance */
  animated?: boolean;
  /** Show dismiss button */
  dismissible?: boolean;
  /** Called when dismiss button is clicked */
  onDismiss?: () => void;
  /** Pulse animation for attention */
  pulse?: boolean;
}

function Badge({
  className,
  variant,
  size,
  animated = false,
  dismissible = false,
  onDismiss,
  pulse = false,
  children,
  ...props
}: BadgeProps) {
  const content = (
    <>
      {pulse && (
        <span className="relative flex h-2 w-2 mr-1.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-current" />
        </span>
      )}
      {children}
      {dismissible && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDismiss?.();
          }}
          className="ml-1 -mr-1 rounded-full p-0.5 hover:bg-white/20 transition-colors"
          aria-label="Dismiss"
        >
          <X className="h-3 w-3" />
        </button>
      )}
    </>
  );

  if (animated) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.8 }}
        transition={{ duration: 0.15, ease: "easeOut" }}
        className={cn(badgeVariants({ variant, size }), className)}
        {...(props as HTMLMotionProps<"div">)}
      >
        {content}
      </motion.div>
    );
  }

  return (
    <div className={cn(badgeVariants({ variant, size }), className)} {...props}>
      {content}
    </div>
  );
}

// Animated badge group for lists
interface BadgeGroupProps {
  children: React.ReactNode;
  className?: string;
}

function BadgeGroup({ children, className }: BadgeGroupProps) {
  return (
    <motion.div
      className={cn("flex flex-wrap gap-1.5", className)}
      initial="hidden"
      animate="visible"
      variants={{
        hidden: { opacity: 0 },
        visible: {
          opacity: 1,
          transition: {
            staggerChildren: 0.05,
          },
        },
      }}
    >
      {React.Children.map(children, (child, index) => (
        <motion.div
          key={index}
          variants={{
            hidden: { opacity: 0, scale: 0.8, y: 4 },
            visible: {
              opacity: 1,
              scale: 1,
              y: 0,
              transition: { duration: 0.2 },
            },
          }}
        >
          {child}
        </motion.div>
      ))}
    </motion.div>
  );
}

export { Badge, BadgeGroup, badgeVariants };
