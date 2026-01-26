"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth";
import { useLogout } from "@/hooks/useAuth";
import { useState } from "react";
import {
  ChevronDown,
  Home,
  FileText,
  Briefcase,
  FolderKanban,
  Lightbulb,
  BookOpen,
  Target,
  FileOutput,
  User,
} from "lucide-react";
import { AuthGuard } from "@/components/auth/auth-guard";
import { CommandPalette } from "@/components/navigation/command-palette";
import { Breadcrumbs } from "@/components/navigation/breadcrumbs";
import { ThemeToggle } from "@/components/theme-toggle";

const navSections = [
  {
    title: null,
    items: [
      { href: "/", label: "Dashboard", icon: Home },
    ],
  },
  {
    title: "Content",
    collapsible: true,
    items: [
      { href: "/documents", label: "Documents", icon: FileText },
      { href: "/experiences", label: "Experiences", icon: Briefcase },
      { href: "/projects", label: "Projects", icon: FolderKanban },
      { href: "/skills", label: "Skills", icon: Lightbulb },
      { href: "/publications", label: "Publications", icon: BookOpen },
    ],
  },
  {
    title: "Workflow",
    collapsible: true,
    items: [
      { href: "/jobs", label: "Jobs", icon: Target },
      { href: "/resume", label: "Resume", icon: FileOutput },
    ],
  },
  {
    title: "Account",
    collapsible: true,
    items: [
      { href: "/profile", label: "Profile", icon: User },
    ],
  },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const user = useAuthStore((state) => state.user);
  const logout = useLogout();
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const toggleSection = (title: string) => {
    setCollapsed((prev) => ({ ...prev, [title]: !prev[title] }));
  };

  return (
    <AuthGuard>
      <div className="min-h-screen flex bg-background">
        {/* Header - Modern SaaS style */}
        <header className="fixed top-0 left-0 right-0 h-14 bg-background border-b border-border z-50 flex items-center justify-between px-4">
          <Link
            href="/"
            className="font-semibold text-lg text-foreground hover:text-primary transition-colors"
          >
            Resume Crafter
          </Link>
          <div className="flex items-center gap-4">
            <CommandPalette />
            <ThemeToggle />
            <span className="text-sm text-muted-foreground hidden sm:inline">
              {user?.email}
            </span>
            <button
              onClick={logout}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Sign out of your account"
            >
              Sign out
            </button>
          </div>
        </header>

        {/* Sidebar - Modern icon + label style */}
        <aside className="fixed top-14 left-0 bottom-0 w-56 border-r border-border bg-card overflow-y-auto scrollbar-thin">
          <nav className="py-4 px-3" role="navigation" aria-label="Main navigation">
            {navSections.map((section, sectionIndex) => (
              <div key={sectionIndex} className="mb-4">
                {section.title && (
                  <button
                    onClick={() => section.collapsible && toggleSection(section.title!)}
                    className="nav-section-title w-full flex items-center justify-between hover:text-foreground transition-colors mb-1"
                    aria-expanded={!collapsed[section.title]}
                  >
                    <span>{section.title}</span>
                    {section.collapsible && (
                      <ChevronDown
                        className={`h-3 w-3 transition-transform duration-200 ${
                          collapsed[section.title] ? "-rotate-90" : ""
                        }`}
                        aria-hidden="true"
                      />
                    )}
                  </button>
                )}
                {!collapsed[section.title || ""] && (
                  <div className="space-y-0.5">
                    {section.items.map((item) => {
                      const isActive = pathname === item.href;
                      const Icon = item.icon;
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          className={`nav-link ${isActive ? "active" : ""}`}
                          aria-current={isActive ? "page" : undefined}
                        >
                          <Icon className="nav-link-icon" />
                          <span>{item.label}</span>
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </nav>
        </aside>

        {/* Main content */}
        <main className="flex-1 ml-56 mt-14">
          <div className="max-w-4xl mx-auto px-6 py-6">
            {/* Breadcrumbs */}
            <div className="mb-6">
              <Breadcrumbs />
            </div>

            {/* Page content */}
            <div className="animate-fade-up">
              {children}
            </div>
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
