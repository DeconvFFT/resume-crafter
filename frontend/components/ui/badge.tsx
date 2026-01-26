import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  // Modern SaaS badge - rounded pill style
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        // Default - primary color fill
        default:
          "border-transparent bg-primary text-primary-foreground shadow-sm hover:bg-primary/80",
        // Secondary - subtle background
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        // Success - uses CSS variable
        success:
          "border-transparent bg-success/10 text-success",
        // Warning - uses CSS variable
        warning:
          "border-transparent bg-warning/10 text-warning",
        // Destructive - red
        destructive:
          "border-transparent bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/80",
        // Outline - border only
        outline:
          "text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
