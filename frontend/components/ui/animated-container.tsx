"use client";

import * as React from "react";
import { motion, AnimatePresence, type Variants, type HTMLMotionProps } from "framer-motion";
import { cn } from "@/lib/utils";
import {
  fadeIn,
  fadeInUp,
  staggerContainer,
  staggerItem,
  pageSlideUp,
  scaleIn,
} from "@/lib/animations";

// ============================================
// Page Wrapper - For page-level transitions
// ============================================

interface PageWrapperProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Animation variant */
  variant?: "fade" | "slideUp" | "scale";
}

export function PageWrapper({
  children,
  className,
  variant = "slideUp",
  ...props
}: PageWrapperProps) {
  const variants: Record<string, Variants> = {
    fade: fadeIn,
    slideUp: pageSlideUp,
    scale: scaleIn,
  };

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      exit="exit"
      variants={variants[variant]}
      className={className}
      {...(props as HTMLMotionProps<"div">)}
    >
      {children}
    </motion.div>
  );
}

// ============================================
// Animated List - For staggered list items
// ============================================

interface AnimatedListProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Children to animate */
  children: React.ReactNode;
  /** Stagger delay between items (in seconds) */
  staggerDelay?: number;
  /** Initial delay before animation starts (in seconds) */
  initialDelay?: number;
}

export function AnimatedList({
  children,
  className,
  staggerDelay = 0.08,
  initialDelay = 0.1,
  ...props
}: AnimatedListProps) {
  const containerVariants: Variants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: staggerDelay,
        delayChildren: initialDelay,
      },
    },
  };

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className={className}
      {...(props as HTMLMotionProps<"div">)}
    >
      {children}
    </motion.div>
  );
}

// ============================================
// Animated Item - For use within AnimatedList
// ============================================

interface AnimatedItemProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Animation type */
  animation?: "fadeUp" | "fadeIn" | "scale" | "slideLeft" | "slideRight";
}

export function AnimatedItem({
  children,
  className,
  animation = "fadeUp",
  ...props
}: AnimatedItemProps) {
  const variants: Record<string, Variants> = {
    fadeUp: {
      hidden: { opacity: 0, y: 12 },
      visible: {
        opacity: 1,
        y: 0,
        transition: { duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] },
      },
    },
    fadeIn: {
      hidden: { opacity: 0 },
      visible: {
        opacity: 1,
        transition: { duration: 0.3 },
      },
    },
    scale: {
      hidden: { opacity: 0, scale: 0.95 },
      visible: {
        opacity: 1,
        scale: 1,
        transition: { duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] },
      },
    },
    slideLeft: {
      hidden: { opacity: 0, x: -16 },
      visible: {
        opacity: 1,
        x: 0,
        transition: { duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] },
      },
    },
    slideRight: {
      hidden: { opacity: 0, x: 16 },
      visible: {
        opacity: 1,
        x: 0,
        transition: { duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] },
      },
    },
  };

  return (
    <motion.div
      variants={variants[animation]}
      className={className}
      {...(props as HTMLMotionProps<"div">)}
    >
      {children}
    </motion.div>
  );
}

// ============================================
// Fade In Section - For content sections
// ============================================

interface FadeInSectionProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Delay before animation (in seconds) */
  delay?: number;
  /** Animation direction */
  direction?: "up" | "down" | "left" | "right" | "none";
  /** Distance to travel */
  distance?: number;
}

export function FadeInSection({
  children,
  className,
  delay = 0,
  direction = "up",
  distance = 16,
  ...props
}: FadeInSectionProps) {
  const getInitialPosition = () => {
    switch (direction) {
      case "up":
        return { y: distance };
      case "down":
        return { y: -distance };
      case "left":
        return { x: distance };
      case "right":
        return { x: -distance };
      default:
        return {};
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, ...getInitialPosition() }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{
        duration: 0.4,
        delay,
        ease: [0.25, 0.46, 0.45, 0.94],
      }}
      className={className}
      {...(props as HTMLMotionProps<"div">)}
    >
      {children}
    </motion.div>
  );
}

// ============================================
// Presence Wrapper - For enter/exit animations
// ============================================

interface PresenceWrapperProps {
  /** Control visibility */
  isVisible: boolean;
  /** Children to animate */
  children: React.ReactNode;
  /** Animation mode */
  mode?: "wait" | "sync" | "popLayout";
  /** Animation variant */
  variant?: "fade" | "scale" | "slideUp" | "slideDown";
  /** Optional className */
  className?: string;
}

export function PresenceWrapper({
  isVisible,
  children,
  mode = "wait",
  variant = "fade",
  className,
}: PresenceWrapperProps) {
  const variants: Record<string, Variants> = {
    fade: fadeIn,
    scale: scaleIn,
    slideUp: fadeInUp,
    slideDown: {
      hidden: { opacity: 0, y: -16 },
      visible: {
        opacity: 1,
        y: 0,
        transition: { duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] },
      },
      exit: {
        opacity: 0,
        y: 8,
        transition: { duration: 0.2, ease: "easeIn" },
      },
    },
  };

  return (
    <AnimatePresence mode={mode}>
      {isVisible && (
        <motion.div
          key="presence-content"
          initial="hidden"
          animate="visible"
          exit="exit"
          variants={variants[variant]}
          className={className}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ============================================
// Hover Scale - Simple hover scale wrapper
// ============================================

interface HoverScaleProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Scale factor on hover */
  scale?: number;
  /** Enable tap feedback */
  tapScale?: number;
}

export function HoverScale({
  children,
  className,
  scale = 1.02,
  tapScale = 0.98,
  ...props
}: HoverScaleProps) {
  return (
    <motion.div
      whileHover={{ scale }}
      whileTap={{ scale: tapScale }}
      transition={{ duration: 0.15, ease: "easeOut" }}
      className={className}
      {...(props as HTMLMotionProps<"div">)}
    >
      {children}
    </motion.div>
  );
}

// ============================================
// Collapsible Animation - For expandable sections
// ============================================

interface CollapsibleAnimationProps {
  isOpen: boolean;
  children: React.ReactNode;
  className?: string;
}

export function CollapsibleAnimation({
  isOpen,
  children,
  className,
}: CollapsibleAnimationProps) {
  return (
    <AnimatePresence initial={false}>
      {isOpen && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.2, ease: "easeOut" }}
          className={cn("overflow-hidden", className)}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ============================================
// Number Counter - Animated number transition
// ============================================

interface NumberCounterProps {
  value: number;
  duration?: number;
  className?: string;
  prefix?: string;
  suffix?: string;
}

export function NumberCounter({
  value,
  duration = 0.5,
  className,
  prefix = "",
  suffix = "",
}: NumberCounterProps) {
  const [displayValue, setDisplayValue] = React.useState(0);

  React.useEffect(() => {
    let startTime: number;
    let animationFrame: number;
    const startValue = displayValue;
    const diff = value - startValue;

    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / (duration * 1000), 1);
      const easeProgress = 1 - Math.pow(1 - progress, 3); // easeOutCubic
      setDisplayValue(Math.round(startValue + diff * easeProgress));

      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate);
      }
    };

    animationFrame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrame);
  }, [value, duration]);

  return (
    <span className={className}>
      {prefix}
      {displayValue}
      {suffix}
    </span>
  );
}
