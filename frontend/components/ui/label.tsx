"use client";

import * as React from "react";
import * as LabelPrimitive from "@radix-ui/react-label";
import { cva, type VariantProps } from "class-variance-authority";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

const labelVariants = cva(
  // Modern SaaS label - clean, medium weight with smooth transitions
  "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 transition-colors duration-200"
);

const Label = React.forwardRef<
  React.ElementRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root> &
    VariantProps<typeof labelVariants> & {
      /** Show required indicator */
      required?: boolean;
      /** Optional helper text */
      helperText?: string;
      /** Error state */
      error?: boolean;
    }
>(({ className, required, helperText, error, children, ...props }, ref) => (
  <div className="space-y-1">
    <LabelPrimitive.Root
      ref={ref}
      className={cn(
        labelVariants(),
        error && "text-destructive",
        className
      )}
      {...props}
    >
      {children}
      {required && (
        <span className="ml-1 text-destructive" aria-hidden="true">
          *
        </span>
      )}
    </LabelPrimitive.Root>
    <AnimatePresence>
      {helperText && (
        <motion.p
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.15 }}
          className={cn(
            "text-xs",
            error ? "text-destructive" : "text-muted-foreground"
          )}
        >
          {helperText}
        </motion.p>
      )}
    </AnimatePresence>
  </div>
));
Label.displayName = LabelPrimitive.Root.displayName;

// Animated floating label for inputs
interface FloatingLabelProps {
  htmlFor?: string;
  children: React.ReactNode;
  isFloating: boolean;
  className?: string;
}

const FloatingLabel = React.forwardRef<HTMLLabelElement, FloatingLabelProps>(
  ({ htmlFor, children, isFloating, className }, ref) => (
    <motion.label
      ref={ref}
      htmlFor={htmlFor}
      className={cn(
        "absolute left-3 pointer-events-none origin-left",
        "text-muted-foreground transition-colors",
        isFloating && "text-primary",
        className
      )}
      animate={{
        top: isFloating ? "0.375rem" : "50%",
        y: isFloating ? 0 : "-50%",
        scale: isFloating ? 0.85 : 1,
        color: isFloating ? "hsl(var(--primary))" : "hsl(var(--muted-foreground))",
      }}
      transition={{ duration: 0.15, ease: "easeOut" }}
    >
      {children}
    </motion.label>
  )
);
FloatingLabel.displayName = "FloatingLabel";

export { Label, FloatingLabel };
