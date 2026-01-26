"use client";

import Link from "next/link";
import {
  FileText,
  Briefcase,
  FolderKanban,
  Target,
  FileOutput,
  Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface ActivityItem {
  id: string;
  type: "document" | "experience" | "project" | "job" | "match";
  title: string;
  subtitle?: string;
  createdAt: string;
  href: string;
}

interface ActivityFeedProps {
  items: ActivityItem[];
}

const typeConfig = {
  document: {
    icon: <FileText className="h-4 w-4" />,
    label: "Document",
    color: "text-info",
  },
  experience: {
    icon: <Briefcase className="h-4 w-4" />,
    label: "Experience",
    color: "text-success",
  },
  project: {
    icon: <FolderKanban className="h-4 w-4" />,
    label: "Project",
    color: "text-accent",
  },
  job: {
    icon: <Target className="h-4 w-4" />,
    label: "Job",
    color: "text-warning",
  },
  match: {
    icon: <FileOutput className="h-4 w-4" />,
    label: "Resume",
    color: "text-primary",
  },
};

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

export function ActivityFeed({ items }: ActivityFeedProps) {
  if (items.length === 0) {
    return (
      <div className="border border-border bg-card p-8 text-center">
        <Clock className="h-8 w-8 mx-auto text-muted-foreground mb-4" aria-hidden="true" />
        <p className="font-semibold text-lg text-foreground">
          No activity yet
        </p>
        <p className="text-sm text-muted-foreground mt-2">
          Start by uploading a document or adding content.
        </p>
      </div>
    );
  }

  return (
    <div className="border border-border bg-card">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-lg">Recent Activity</h3>
        </div>
        <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
          {items.length} item{items.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Activity List - Editorial table-of-contents style */}
      <div className="divide-y divide-border" role="list">
        {items.slice(0, 8).map((item, index) => {
          const config = typeConfig[item.type];
          return (
            <Link
              key={item.id}
              href={item.href}
              className="flex items-center gap-4 px-6 py-4 hover:bg-muted/50 transition-colors group"
              role="listitem"
            >
              {/* Index number */}
              <span className="font-mono text-xs text-muted-foreground w-6">
                {String(index + 1).padStart(2, "0")}
              </span>

              {/* Icon */}
              <span className={cn("flex-shrink-0", config.color)}>
                {config.icon}
              </span>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate group-hover:text-primary transition-colors">
                  {item.title}
                </p>
              </div>

              {/* Type badge */}
              <span className={cn(
                "font-mono text-2xs uppercase tracking-widest flex-shrink-0",
                config.color
              )}>
                {config.label}
              </span>

              {/* Timestamp */}
              <span className="font-mono text-xs text-muted-foreground flex-shrink-0 w-16 text-right">
                {formatRelativeTime(item.createdAt)}
              </span>
            </Link>
          );
        })}
      </div>

      {/* Footer - more items indicator */}
      {items.length > 8 && (
        <div className="px-6 py-3 border-t border-border text-center">
          <span className="font-mono text-xs text-muted-foreground">
            + {items.length - 8} more
          </span>
        </div>
      )}
    </div>
  );
}
