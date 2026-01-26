import { cn } from "@/lib/utils"

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {}

function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        // Base skeleton styles
        "rounded-md",
        // Light mode shimmer
        "bg-gradient-to-r from-muted via-muted/50 to-muted",
        // Dark mode shimmer - slightly different gradient for visibility
        "dark:from-muted dark:via-muted/70 dark:to-muted",
        // Background size for shimmer animation
        "bg-[length:200%_100%]",
        // Shimmer animation
        "animate-shimmer",
        className
      )}
      {...props}
    />
  )
}

// Preset skeleton variants for common use cases
function SkeletonText({ className, ...props }: SkeletonProps) {
  return (
    <Skeleton
      className={cn("h-4 w-full", className)}
      {...props}
    />
  )
}

function SkeletonCircle({ className, ...props }: SkeletonProps) {
  return (
    <Skeleton
      className={cn("h-10 w-10 rounded-full", className)}
      {...props}
    />
  )
}

function SkeletonCard({ className, ...props }: SkeletonProps) {
  return (
    <div className={cn("space-y-3", className)} {...props}>
      <Skeleton className="h-32 w-full" />
      <div className="space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    </div>
  )
}

export { Skeleton, SkeletonText, SkeletonCircle, SkeletonCard }
