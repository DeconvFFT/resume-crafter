"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface SpinnerProps {
  /** Size of the spinner */
  size?: "sm" | "md" | "lg" | "xl";
  /** Color variant */
  variant?: "default" | "primary" | "gradient" | "white";
  /** Optional className */
  className?: string;
  /** Show loading text */
  label?: string;
}

const sizeClasses = {
  sm: "h-4 w-4",
  md: "h-6 w-6",
  lg: "h-8 w-8",
  xl: "h-12 w-12",
};

const borderSizeClasses = {
  sm: "border-2",
  md: "border-2",
  lg: "border-[3px]",
  xl: "border-4",
};

export function Spinner({
  size = "md",
  variant = "default",
  className,
  label,
}: SpinnerProps) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <motion.div
        animate={{ rotate: 360 }}
        transition={{
          duration: 1,
          repeat: Infinity,
          ease: "linear",
        }}
        className={cn(
          "rounded-full",
          sizeClasses[size],
          borderSizeClasses[size],
          {
            // Default - muted border with foreground accent
            "border-muted-foreground/20 border-t-foreground": variant === "default",
            // Primary - primary color accent
            "border-primary/20 border-t-primary": variant === "primary",
            // White - for dark backgrounds
            "border-white/20 border-t-white": variant === "white",
          },
          // Gradient requires special handling
          variant === "gradient" && "border-transparent"
        )}
        style={
          variant === "gradient"
            ? {
                background: `conic-gradient(from 0deg, transparent 0deg, hsl(var(--primary)) 270deg, transparent 360deg)`,
                WebkitMask: `radial-gradient(farthest-side, transparent calc(100% - ${size === "xl" ? "4px" : size === "lg" ? "3px" : "2px"}), white calc(100% - ${size === "xl" ? "4px" : size === "lg" ? "3px" : "2px"}))`,
                mask: `radial-gradient(farthest-side, transparent calc(100% - ${size === "xl" ? "4px" : size === "lg" ? "3px" : "2px"}), white calc(100% - ${size === "xl" ? "4px" : size === "lg" ? "3px" : "2px"}))`,
              }
            : undefined
        }
      />
      {label && (
        <span className="text-sm text-muted-foreground animate-pulse">{label}</span>
      )}
    </div>
  );
}

// Dots loading animation
interface DotsLoaderProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function DotsLoader({ size = "md", className }: DotsLoaderProps) {
  const dotSizes = {
    sm: "h-1.5 w-1.5",
    md: "h-2 w-2",
    lg: "h-3 w-3",
  };

  const gaps = {
    sm: "gap-1",
    md: "gap-1.5",
    lg: "gap-2",
  };

  return (
    <div className={cn("flex items-center", gaps[size], className)}>
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className={cn("rounded-full bg-primary", dotSizes[size])}
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.5, 1, 0.5],
          }}
          transition={{
            duration: 0.8,
            repeat: Infinity,
            delay: i * 0.15,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
}

// Pulse loader - circular pulse
interface PulseLoaderProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function PulseLoader({ size = "md", className }: PulseLoaderProps) {
  const sizes = {
    sm: "h-8 w-8",
    md: "h-12 w-12",
    lg: "h-16 w-16",
  };

  return (
    <div className={cn("relative", sizes[size], className)}>
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="absolute inset-0 rounded-full border-2 border-primary"
          initial={{ opacity: 0.6, scale: 1 }}
          animate={{
            opacity: 0,
            scale: 1.5,
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            delay: i * 0.5,
            ease: "easeOut",
          }}
        />
      ))}
      <div className="absolute inset-1/4 rounded-full bg-primary/20" />
    </div>
  );
}

// Bar loader - horizontal progress-like
interface BarLoaderProps {
  className?: string;
}

export function BarLoader({ className }: BarLoaderProps) {
  return (
    <div
      className={cn(
        "h-1 w-full bg-primary/20 rounded-full overflow-hidden",
        className
      )}
    >
      <motion.div
        className="h-full w-1/3 bg-primary rounded-full"
        animate={{
          x: ["-100%", "400%"],
        }}
        transition={{
          duration: 1.2,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
    </div>
  );
}

// Full page loader
interface PageLoaderProps {
  message?: string;
}

export function PageLoader({ message = "Loading..." }: PageLoaderProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm"
    >
      <Spinner size="xl" variant="gradient" />
      <motion.p
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="mt-4 text-sm text-muted-foreground"
      >
        {message}
      </motion.p>
    </motion.div>
  );
}

// Inline loading button content
interface ButtonLoaderProps {
  children: React.ReactNode;
  isLoading: boolean;
  loadingText?: string;
}

export function ButtonLoader({
  children,
  isLoading,
  loadingText,
}: ButtonLoaderProps) {
  return (
    <>
      {isLoading ? (
        <span className="flex items-center gap-2">
          <Spinner size="sm" variant="white" />
          {loadingText && <span>{loadingText}</span>}
        </span>
      ) : (
        children
      )}
    </>
  );
}
