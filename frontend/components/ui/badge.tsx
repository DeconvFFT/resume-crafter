import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  // Editorial badge - mono font, uppercase, bordered style
  "inline-flex items-center border px-3 py-1 font-mono text-xs uppercase tracking-wider transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        // Default - ink border
        default:
          "border-foreground text-foreground",
        // Secondary - muted border
        secondary:
          "border-muted-foreground/50 text-muted-foreground",
        // Success - forest green
        success:
          "border-success text-success",
        // Warning - amber
        warning:
          "border-warning text-warning",
        // Destructive - burgundy
        destructive:
          "border-destructive text-destructive",
        // Gold - champagne accent for premium
        gold:
          "border-accent text-accent",
        // Outline - subtle
        outline:
          "border-border text-muted-foreground",
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
