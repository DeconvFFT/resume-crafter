import * as React from "react"

import { cn } from "@/lib/utils"

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          // Editorial textarea - bottom border style, matching input
          "flex min-h-[120px] w-full border-b-2 border-border bg-transparent px-0 py-3",
          "font-body text-base text-foreground",
          "transition-colors duration-200 resize-y",
          // Placeholder - italic style
          "placeholder:italic placeholder:text-muted-foreground/60",
          // Focus state - terracotta border
          "focus:border-primary focus:outline-none",
          // Disabled state
          "disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Textarea.displayName = "Textarea"

export { Textarea }
