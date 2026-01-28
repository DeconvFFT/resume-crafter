"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { motion, type HTMLMotionProps } from "framer-motion";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  // Base styles with improved transitions
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md font-sans text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 select-none",
  {
    variants: {
      variant: {
        // Primary - Gradient with animated glow
        default:
          "bg-gradient-to-r from-primary to-primary/90 text-primary-foreground shadow-sm hover:from-primary/95 hover:to-primary hover:shadow-md active:scale-[0.98] relative overflow-hidden",
        // Destructive - Red with pulse on hover
        destructive:
          "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90 hover:shadow-md active:scale-[0.98]",
        // Outline - Border with hover background and glow
        outline:
          "border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground hover:border-accent-foreground/20 active:scale-[0.98]",
        // Secondary - Subtle background with lift
        secondary:
          "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80 hover:shadow-md active:scale-[0.98]",
        // Ghost - Minimal, smooth background transition
        ghost:
          "hover:bg-accent hover:text-accent-foreground active:scale-[0.98]",
        // Link - Underline animation
        link:
          "text-primary underline-offset-4 hover:underline",
        // Premium gradient variant
        gradient:
          "bg-gradient-to-r from-primary via-primary/90 to-primary/80 text-primary-foreground shadow-sm hover:shadow-lg hover:shadow-primary/25 active:scale-[0.98] relative overflow-hidden before:absolute before:inset-0 before:bg-gradient-to-r before:from-transparent before:via-white/10 before:to-transparent before:translate-x-[-200%] hover:before:translate-x-[200%] before:transition-transform before:duration-700",
        // Glow variant - subtle glow effect
        glow:
          "bg-primary text-primary-foreground shadow-sm hover:shadow-lg hover:shadow-primary/30 active:scale-[0.98] transition-shadow",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
        xl: "h-12 rounded-lg px-10 text-base",
        icon: "h-9 w-9",
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
  /** Enable ripple effect on click */
  ripple?: boolean;
  /** Use motion component for enhanced animations */
  animated?: boolean;
}

// Ripple effect component
function RippleEffect({
  x,
  y,
  size,
}: {
  x: number;
  y: number;
  size: number;
}) {
  return (
    <motion.span
      initial={{ scale: 0, opacity: 0.5 }}
      animate={{ scale: 1, opacity: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="absolute rounded-full bg-white/30 pointer-events-none"
      style={{
        left: x - size / 2,
        top: y - size / 2,
        width: size,
        height: size,
      }}
    />
  );
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({
    className,
    variant,
    size,
    asChild = false,
    ripple = false,
    animated = false,
    onClick,
    ...props
  }, ref) => {
    const [ripples, setRipples] = React.useState<
      Array<{ id: number; x: number; y: number; size: number }>
    >([]);

    const handleClick = React.useCallback(
      (e: React.MouseEvent<HTMLButtonElement>) => {
        if (ripple) {
          const button = e.currentTarget;
          const rect = button.getBoundingClientRect();
          const size = Math.max(rect.width, rect.height) * 2;
          const x = e.clientX - rect.left;
          const y = e.clientY - rect.top;
          const id = Date.now();

          setRipples((prev) => [...prev, { id, x, y, size }]);

          // Clean up ripple after animation
          setTimeout(() => {
            setRipples((prev) => prev.filter((r) => r.id !== id));
          }, 600);
        }

        onClick?.(e);
      },
      [ripple, onClick]
    );

    if (asChild) {
      return (
        <Slot
          className={cn(buttonVariants({ variant, size, className }))}
          ref={ref}
          {...props}
        />
      );
    }

    // Use motion component for animated buttons
    if (animated) {
      return (
        <motion.button
          className={cn(buttonVariants({ variant, size, className }), "relative overflow-hidden")}
          ref={ref}
          onClick={handleClick}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          transition={{ duration: 0.15, ease: "easeOut" }}
          {...(props as HTMLMotionProps<"button">)}
        >
          {props.children}
          {ripples.map((ripple) => (
            <RippleEffect key={ripple.id} {...ripple} />
          ))}
        </motion.button>
      );
    }

    return (
      <button
        className={cn(buttonVariants({ variant, size, className }), ripple && "relative overflow-hidden")}
        ref={ref}
        onClick={handleClick}
        {...props}
      >
        {props.children}
        {ripples.map((ripple) => (
          <RippleEffect key={ripple.id} {...ripple} />
        ))}
      </button>
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
