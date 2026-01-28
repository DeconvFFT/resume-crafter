"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { CheckCircle2, AlertCircle, XCircle } from "lucide-react";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
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
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      type,
      success,
      error,
      errorMessage,
      successMessage,
      glow = false,
      ...props
    },
    ref
  ) => {
    const [isFocused, setIsFocused] = React.useState(false);

    return (
      <div className="relative">
        <input
          type={type}
          className={cn(
            // Modern SaaS input - rounded with border
            "flex h-9 w-full rounded-md border bg-transparent px-3 py-1",
            "text-sm shadow-sm",
            // Smooth transitions for all states
            "transition-all duration-200 ease-out",
            // Placeholder style
            "placeholder:text-muted-foreground",
            // Focus state - ring style with glow
            "focus-visible:outline-none focus-visible:ring-2",
            // Glow effect on focus
            glow && "focus-visible:shadow-lg focus-visible:shadow-primary/20",
            // Default focus ring
            !error && !success && "border-input focus-visible:ring-ring focus-visible:border-primary/50",
            // Success state
            success && "border-success/50 focus-visible:ring-success/50 focus-visible:border-success",
            // Error state
            error && "border-destructive/50 focus-visible:ring-destructive/50 focus-visible:border-destructive",
            // File input styling
            "file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground",
            // Disabled state
            "disabled:cursor-not-allowed disabled:opacity-50",
            className
          )}
          ref={ref}
          onFocus={(e) => {
            setIsFocused(true);
            props.onFocus?.(e);
          }}
          onBlur={(e) => {
            setIsFocused(false);
            props.onBlur?.(e);
          }}
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
              className="absolute right-3 top-1/2 -translate-y-1/2"
            >
              {success && (
                <CheckCircle2 className="h-4 w-4 text-success" />
              )}
              {error && (
                <XCircle className="h-4 w-4 text-destructive" />
              )}
            </motion.div>
          )}
        </AnimatePresence>

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
Input.displayName = "Input";

// Floating label input variant
interface FloatingInputProps extends InputProps {
  label: string;
}

const FloatingInput = React.forwardRef<HTMLInputElement, FloatingInputProps>(
  ({ className, label, id, ...props }, ref) => {
    const [isFocused, setIsFocused] = React.useState(false);
    const [hasValue, setHasValue] = React.useState(false);

    const isFloating = isFocused || hasValue;

    return (
      <div className="relative">
        <input
          id={id}
          type={props.type}
          className={cn(
            "peer flex h-12 w-full rounded-md border border-input bg-transparent px-3 pt-4 pb-1",
            "text-sm shadow-sm transition-all duration-200",
            "placeholder:text-transparent",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:border-primary/50",
            "disabled:cursor-not-allowed disabled:opacity-50",
            className
          )}
          ref={ref}
          placeholder={label}
          onFocus={(e) => {
            setIsFocused(true);
            props.onFocus?.(e);
          }}
          onBlur={(e) => {
            setIsFocused(false);
            setHasValue(!!e.target.value);
            props.onBlur?.(e);
          }}
          onChange={(e) => {
            setHasValue(!!e.target.value);
            props.onChange?.(e);
          }}
          {...props}
        />
        <label
          htmlFor={id}
          className={cn(
            "absolute left-3 transition-all duration-200 pointer-events-none",
            "text-muted-foreground",
            isFloating
              ? "top-1.5 text-xs text-primary"
              : "top-1/2 -translate-y-1/2 text-sm"
          )}
        >
          {label}
        </label>
      </div>
    );
  }
);
FloatingInput.displayName = "FloatingInput";

export { Input, FloatingInput };
