import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap font-body text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        // Primary - Terracotta red, uppercase, editorial style
        default:
          "bg-primary text-primary-foreground uppercase tracking-wider hover:-translate-y-px hover:shadow-elevated active:translate-y-0",
        // Destructive - Burgundy
        destructive:
          "bg-destructive text-destructive-foreground uppercase tracking-wider hover:-translate-y-px hover:shadow-elevated active:translate-y-0",
        // Outline - Black border, inverts on hover
        outline:
          "border-2 border-foreground bg-transparent text-foreground uppercase tracking-wider hover:bg-foreground hover:text-background",
        // Secondary - Subtle, card background
        secondary:
          "bg-card text-card-foreground border border-border hover:border-foreground",
        // Ghost - Minimal, underline style
        ghost:
          "text-foreground hover:text-primary underline-offset-4 hover:underline",
        // Link - Editorial underline animation
        link:
          "text-primary relative after:absolute after:bottom-0 after:left-0 after:h-[2px] after:w-0 after:bg-primary after:transition-all after:duration-300 hover:after:w-full",
      },
      size: {
        default: "h-11 px-7 py-3",
        sm: "h-9 px-4 py-2 text-xs",
        lg: "h-12 px-10 py-4 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
