"use client";

import * as React from "react";
import { motion, type HTMLMotionProps } from "framer-motion";
import { cn } from "@/lib/utils";
import { cardHover } from "@/lib/animations";

// Card variants for different styles
type CardVariant = "default" | "elevated" | "gradient-border" | "glow" | "interactive";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Card style variant */
  variant?: CardVariant;
  /** Enable hover lift animation */
  hoverable?: boolean;
  /** Use motion component for enhanced animations */
  animated?: boolean;
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = "default", hoverable = false, animated = false, ...props }, ref) => {
    const baseClasses = cn(
      // Base card styles
      "rounded-lg border bg-card text-card-foreground",
      // Variant styles
      {
        // Default - subtle shadow
        "border-border shadow-card": variant === "default",
        // Elevated - more prominent shadow
        "border-border shadow-elevated": variant === "elevated",
        // Gradient border - animated gradient border on hover
        "border-transparent bg-gradient-to-b from-card to-card shadow-card relative before:absolute before:inset-0 before:-z-10 before:rounded-lg before:p-[1px] before:bg-gradient-to-br before:from-border before:via-primary/20 before:to-border hover:before:from-primary/30 hover:before:via-primary/50 hover:before:to-primary/30 before:transition-all before:duration-300":
          variant === "gradient-border",
        // Glow - subtle glow effect on hover
        "border-border shadow-card hover:shadow-lg hover:shadow-primary/5 transition-shadow duration-300":
          variant === "glow",
        // Interactive - lift and glow on hover
        "border-border shadow-card hover:border-primary/30 hover:shadow-elevated transition-all duration-200":
          variant === "interactive",
      },
      // Hover lift effect
      hoverable && "hover:-translate-y-1 hover:shadow-elevated transition-all duration-200 cursor-pointer",
      className
    );

    if (animated) {
      return (
        <motion.div
          ref={ref}
          className={baseClasses}
          whileHover={hoverable ? cardHover : undefined}
          transition={{ duration: 0.2, ease: "easeOut" }}
          {...(props as HTMLMotionProps<"div">)}
        />
      );
    }

    return <div ref={ref} className={baseClasses} {...props} />;
  }
);
Card.displayName = "Card";

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-4", className)}
    {...props}
  />
));
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      "font-sans text-lg font-semibold leading-none tracking-tight",
      className
    )}
    {...props}
  />
));
CardTitle.displayName = "CardTitle";

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
));
CardDescription.displayName = "CardDescription";

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-4 pt-0", className)} {...props} />
));
CardContent.displayName = "CardContent";

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-4 pt-0", className)}
    {...props}
  />
));
CardFooter.displayName = "CardFooter";

// Animated card wrapper for staggered list animations
interface AnimatedCardProps extends CardProps {
  /** Index for staggered animations */
  index?: number;
  /** Custom delay for animation */
  delay?: number;
}

const AnimatedCard = React.forwardRef<HTMLDivElement, AnimatedCardProps>(
  ({ index = 0, delay, className, variant = "default", hoverable = false, ...props }, ref) => {
    const animationDelay = delay ?? index * 0.08;

    return (
      <motion.div
        ref={ref}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{
          duration: 0.4,
          delay: animationDelay,
          ease: [0.25, 0.46, 0.45, 0.94],
        }}
        whileHover={hoverable ? cardHover : undefined}
        className={cn(
          "rounded-lg border bg-card text-card-foreground",
          {
            "border-border shadow-card": variant === "default",
            "border-border shadow-elevated": variant === "elevated",
            "border-border shadow-card hover:border-primary/30 hover:shadow-elevated transition-all duration-200":
              variant === "interactive",
          },
          hoverable && "cursor-pointer",
          className
        )}
        {...(props as HTMLMotionProps<"div">)}
      />
    );
  }
);
AnimatedCard.displayName = "AnimatedCard";

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardDescription,
  CardContent,
  AnimatedCard,
};
