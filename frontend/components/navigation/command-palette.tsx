"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import {
  FileText,
  Briefcase,
  FolderKanban,
  Code2,
  BookOpen,
  Target,
  FileOutput,
  User,
  Home,
  Search,
  Command,
  ArrowRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon: React.ReactNode;
  action: () => void;
  keywords?: string[];
  section: string;
}

const sections = [
  { id: "navigation", label: "Navigation" },
  { id: "actions", label: "Quick Actions" },
];

export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const [selectedIndex, setSelectedIndex] = React.useState(0);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const commands: CommandItem[] = React.useMemo(
    () => [
      // Navigation
      {
        id: "dashboard",
        label: "Dashboard",
        description: "View your overview",
        icon: <Home className="h-4 w-4" />,
        action: () => router.push("/"),
        keywords: ["home", "overview", "main"],
        section: "navigation",
      },
      {
        id: "documents",
        label: "Documents",
        description: "Manage uploaded files",
        icon: <FileText className="h-4 w-4" />,
        action: () => router.push("/documents"),
        keywords: ["files", "upload", "pdf", "resume"],
        section: "navigation",
      },
      {
        id: "experiences",
        label: "Experiences",
        description: "Work history and roles",
        icon: <Briefcase className="h-4 w-4" />,
        action: () => router.push("/experiences"),
        keywords: ["work", "jobs", "employment", "career"],
        section: "navigation",
      },
      {
        id: "projects",
        label: "Projects",
        description: "Portfolio and side projects",
        icon: <FolderKanban className="h-4 w-4" />,
        action: () => router.push("/projects"),
        keywords: ["portfolio", "side projects", "github"],
        section: "navigation",
      },
      {
        id: "skills",
        label: "Skills",
        description: "Technical and soft skills",
        icon: <Code2 className="h-4 w-4" />,
        action: () => router.push("/skills"),
        keywords: ["programming", "languages", "technologies"],
        section: "navigation",
      },
      {
        id: "publications",
        label: "Publications",
        description: "Papers and articles",
        icon: <BookOpen className="h-4 w-4" />,
        action: () => router.push("/publications"),
        keywords: ["papers", "research", "articles"],
        section: "navigation",
      },
      {
        id: "jobs",
        label: "Jobs",
        description: "Target job descriptions",
        icon: <Target className="h-4 w-4" />,
        action: () => router.push("/jobs"),
        keywords: ["job descriptions", "applications", "targets"],
        section: "navigation",
      },
      {
        id: "resume",
        label: "Resume",
        description: "Generate tailored resumes",
        icon: <FileOutput className="h-4 w-4" />,
        action: () => router.push("/resume"),
        keywords: ["cv", "generate", "export", "match"],
        section: "navigation",
      },
      {
        id: "profile",
        label: "Profile",
        description: "Account settings",
        icon: <User className="h-4 w-4" />,
        action: () => router.push("/profile"),
        keywords: ["account", "settings", "user"],
        section: "navigation",
      },
      // Quick Actions
      {
        id: "upload-document",
        label: "Upload Document",
        description: "Add a new file",
        icon: <FileText className="h-4 w-4" />,
        action: () => router.push("/documents?action=upload"),
        keywords: ["add", "import", "file"],
        section: "actions",
      },
      {
        id: "add-job",
        label: "Add Job Description",
        description: "Analyze a new job posting",
        icon: <Target className="h-4 w-4" />,
        action: () => router.push("/jobs?action=add"),
        keywords: ["new", "job", "posting", "analyze"],
        section: "actions",
      },
      {
        id: "generate-resume",
        label: "Generate Resume",
        description: "Create a tailored resume",
        icon: <FileOutput className="h-4 w-4" />,
        action: () => router.push("/resume?action=generate"),
        keywords: ["create", "export", "match"],
        section: "actions",
      },
    ],
    [router]
  );

  const filteredCommands = React.useMemo(() => {
    if (!query) return commands;
    const lowerQuery = query.toLowerCase();
    return commands.filter(
      (cmd) =>
        cmd.label.toLowerCase().includes(lowerQuery) ||
        cmd.description?.toLowerCase().includes(lowerQuery) ||
        cmd.keywords?.some((k) => k.toLowerCase().includes(lowerQuery))
    );
  }, [commands, query]);

  const groupedCommands = React.useMemo(() => {
    const groups: Record<string, CommandItem[]> = {};
    filteredCommands.forEach((cmd) => {
      if (!groups[cmd.section]) groups[cmd.section] = [];
      groups[cmd.section].push(cmd);
    });
    return groups;
  }, [filteredCommands]);

  const flatCommands = React.useMemo(() => {
    return sections.flatMap((s) => groupedCommands[s.id] || []);
  }, [groupedCommands]);

  // Keyboard shortcuts
  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  // Reset on open
  React.useEffect(() => {
    if (open) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  // Keyboard navigation within palette
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((i) => (i + 1) % flatCommands.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((i) => (i - 1 + flatCommands.length) % flatCommands.length);
    } else if (e.key === "Enter" && flatCommands[selectedIndex]) {
      e.preventDefault();
      flatCommands[selectedIndex].action();
      setOpen(false);
    }
  };

  return (
    <>
      {/* Trigger Button - Editorial style */}
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground hover:text-foreground border border-border hover:border-foreground transition-all"
        aria-label="Open command palette"
      >
        <Search className="h-4 w-4" />
        <span className="hidden sm:inline">Search</span>
        <kbd className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 font-mono text-2xs text-muted-foreground border border-border ml-2">
          <Command className="h-3 w-3" aria-hidden="true" />
          <span>K</span>
        </kbd>
      </button>

      {/* Command Palette Dialog - Editorial style */}
      <DialogPrimitive.Root open={open} onOpenChange={setOpen}>
        <DialogPrimitive.Portal>
          <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-foreground/60 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
          <DialogPrimitive.Content
            className="fixed left-[50%] top-[20%] z-50 w-full max-w-lg translate-x-[-50%] border-2 border-foreground bg-background shadow-floating data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=open]:slide-in-from-left-1/2"
            onKeyDown={handleKeyDown}
          >
            {/* Corner marks */}
            <div className="absolute -top-2 -left-2 w-4 h-4 border-l-2 border-t-2 border-foreground" aria-hidden="true" />
            <div className="absolute -bottom-2 -right-2 w-4 h-4 border-r-2 border-b-2 border-foreground" aria-hidden="true" />

            {/* Search Input */}
            <div className="flex items-center gap-4 px-6 py-4 border-b-2 border-foreground">
              <Search className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
              <input
                ref={inputRef}
                type="text"
                placeholder="Search commands..."
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setSelectedIndex(0);
                }}
                className="flex-1 bg-transparent text-base outline-none placeholder:italic placeholder:text-muted-foreground/60"
                aria-label="Search commands"
              />
              <kbd className="px-2 py-1 font-mono text-2xs text-muted-foreground border border-border">
                ESC
              </kbd>
            </div>

            {/* Commands List */}
            <div className="max-h-[320px] overflow-y-auto py-4">
              {flatCommands.length === 0 ? (
                <div className="px-6 py-10 text-center">
                  <p className="text-sm text-muted-foreground">
                    No results found.
                  </p>
                </div>
              ) : (
                sections.map((section) => {
                  const items = groupedCommands[section.id];
                  if (!items?.length) return null;
                  return (
                    <div key={section.id} className="mb-4">
                      <div className="px-6 py-2 font-mono text-xs uppercase tracking-widest text-muted-foreground">
                        {section.label}
                      </div>
                      {items.map((cmd) => {
                        const isSelected = flatCommands[selectedIndex]?.id === cmd.id;
                        return (
                          <button
                            key={cmd.id}
                            onClick={() => {
                              cmd.action();
                              setOpen(false);
                            }}
                            onMouseEnter={() =>
                              setSelectedIndex(flatCommands.findIndex((c) => c.id === cmd.id))
                            }
                            className={cn(
                              "w-full flex items-center gap-4 px-6 py-3 text-left transition-colors",
                              isSelected
                                ? "bg-primary/10 border-l-2 border-primary"
                                : "hover:bg-muted border-l-2 border-transparent"
                            )}
                          >
                            <span
                              className={cn(
                                "flex items-center justify-center w-8 h-8",
                                isSelected ? "text-primary" : "text-muted-foreground"
                              )}
                            >
                              {cmd.icon}
                            </span>
                            <div className="flex-1 min-w-0">
                              <div className={cn(
                                "text-sm",
                                isSelected ? "font-semibold text-foreground" : "text-foreground"
                              )}>
                                {cmd.label}
                              </div>
                              {cmd.description && (
                                <div className="text-xs text-muted-foreground">
                                  {cmd.description}
                                </div>
                              )}
                            </div>
                            {isSelected && (
                              <ArrowRight className="h-4 w-4 text-primary" aria-hidden="true" />
                            )}
                          </button>
                        );
                      })}
                    </div>
                  );
                })
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between px-6 py-3 border-t border-border font-mono text-2xs text-muted-foreground">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-2">
                  <kbd className="px-1.5 py-0.5 border border-border">
                    ↑↓
                  </kbd>
                  navigate
                </span>
                <span className="flex items-center gap-2">
                  <kbd className="px-1.5 py-0.5 border border-border">
                    ↵
                  </kbd>
                  select
                </span>
              </div>
              <span className="flex items-center gap-2">
                <kbd className="px-1.5 py-0.5 border border-border">
                  esc
                </kbd>
                close
              </span>
            </div>
          </DialogPrimitive.Content>
        </DialogPrimitive.Portal>
      </DialogPrimitive.Root>
    </>
  );
}
