"use client";

import * as React from "react";
import { Sun, Moon, Monitor } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useThemeStore } from "@/lib/stores/theme";
import { cn } from "@/lib/utils";

interface ThemeToggleProps {
  className?: string;
}

/**
 * Theme toggle button that cycles through light, dark, and system modes.
 * Displays the current theme mode with an appropriate icon.
 */
export function ThemeToggle({ className }: ThemeToggleProps) {
  const { mode, toggleMode, _hasHydrated } = useThemeStore();

  // Prevent hydration mismatch by not rendering until hydrated
  if (!_hasHydrated) {
    return (
      <Button
        variant="ghost"
        size="icon"
        className={cn("h-9 w-9", className)}
        disabled
        aria-label="Loading theme"
      >
        <Sun className="h-4 w-4" />
      </Button>
    );
  }

  const getIcon = () => {
    switch (mode) {
      case "light":
        return <Sun className="h-4 w-4" />;
      case "dark":
        return <Moon className="h-4 w-4" />;
      case "system":
        return <Monitor className="h-4 w-4" />;
    }
  };

  const getLabel = () => {
    switch (mode) {
      case "light":
        return "Light mode (click for dark)";
      case "dark":
        return "Dark mode (click for system)";
      case "system":
        return "System mode (click for light)";
    }
  };

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggleMode}
      className={cn("h-9 w-9", className)}
      aria-label={getLabel()}
      title={getLabel()}
    >
      {getIcon()}
      <span className="sr-only">{getLabel()}</span>
    </Button>
  );
}
