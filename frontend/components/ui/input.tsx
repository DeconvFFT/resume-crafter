import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          // Editorial input - bottom border only, transparent bg
          "flex h-11 w-full border-b-2 border-border bg-transparent px-0 py-3",
          "font-body text-base text-foreground",
          "transition-colors duration-200",
          // Placeholder - italic style
          "placeholder:italic placeholder:text-muted-foreground/60",
          // Focus state - terracotta border
          "focus:border-primary focus:outline-none",
          // File input styling
          "file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground",
          // Disabled state
          "disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
