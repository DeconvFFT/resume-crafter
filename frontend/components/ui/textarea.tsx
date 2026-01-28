"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { CheckCircle2, XCircle } from "lucide-react";

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  /** Show success state with green ring */
  success?: boolean;
  /** Show error state with red ring */
  error?: boolean;
  /** Error message to display */
  errorMessage?: string;
  /** Success message to display */
  successMessage?: string;
  /** Enable glow effect on focus */
  glow?: boolean;
  /** Show character count */
  showCount?: boolean;
  /** Maximum character count */
  maxCount?: number;
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      className,
      success,
      error,
      errorMessage,
      successMessage,
      glow = false,
      showCount = false,
      maxCount,
      onChange,
      ...props
    },
    ref
  ) => {
    const [charCount, setCharCount] = React.useState(
      props.value?.toString().length || props.defaultValue?.toString().length || 0
    );

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setCharCount(e.target.value.length);
      onChange?.(e);
    };

    const isOverLimit = maxCount ? charCount > maxCount : false;

    return (
      <div className="relative">
        <textarea
          className={cn(
            // Modern SaaS textarea - rounded with border
            "flex min-h-[80px] w-full rounded-md border bg-transparent px-3 py-2",
            "text-sm shadow-sm resize-none",
            // Smooth transitions for all states
            "transition-all duration-200 ease-out",
            // Placeholder style
            "placeholder:text-muted-foreground",
            // Focus state - ring style with optional glow
            "focus-visible:outline-none focus-visible:ring-2",
            // Glow effect on focus
            glow && "focus-visible:shadow-lg focus-visible:shadow-primary/20",
            // Default focus ring
            !error && !success && !isOverLimit && "border-input focus-visible:ring-ring focus-visible:border-primary/50",
            // Success state
            success && !isOverLimit && "border-success/50 focus-visible:ring-success/50 focus-visible:border-success",
            // Error state
            (error || isOverLimit) && "border-destructive/50 focus-visible:ring-destructive/50 focus-visible:border-destructive",
            // Disabled state
            "disabled:cursor-not-allowed disabled:opacity-50",
            className
          )}
          ref={ref}
          onChange={handleChange}
          {...props}
        />

        {/* Status icon */}
        <AnimatePresence>
          {(success || error) && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.15 }}
              className="absolute right-3 top-3"
            >
              {success && !error && (
                <CheckCircle2 className="h-4 w-4 text-success" />
              )}
              {error && (
                <XCircle className="h-4 w-4 text-destructive" />
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Character count */}
        {showCount && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className={cn(
              "absolute right-3 bottom-2 text-xs",
              isOverLimit ? "text-destructive" : "text-muted-foreground"
            )}
          >
            {charCount}
            {maxCount && ` / ${maxCount}`}
          </motion.div>
        )}

        {/* Error/Success message */}
        <AnimatePresence>
          {(errorMessage || successMessage) && (
            <motion.p
              initial={{ opacity: 0, y: -4, height: 0 }}
              animate={{ opacity: 1, y: 0, height: "auto" }}
              exit={{ opacity: 0, y: -4, height: 0 }}
              transition={{ duration: 0.2 }}
              className={cn(
                "text-xs mt-1.5",
                error && "text-destructive",
                success && "text-success"
              )}
            >
              {errorMessage || successMessage}
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    );
  }
);
Textarea.displayName = "Textarea";

export { Textarea };
