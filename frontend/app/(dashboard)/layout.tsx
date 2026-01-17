"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth";
import { useLogout } from "@/hooks/useAuth";
import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { AuthGuard } from "@/components/auth/auth-guard";
import { CommandPalette } from "@/components/navigation/command-palette";
import { Breadcrumbs } from "@/components/navigation/breadcrumbs";

const navSections = [
  {
    title: null,
    items: [
      { href: "/", label: "Dashboard", number: "00" },
    ],
  },
  {
    title: "Content",
    collapsible: true,
    items: [
      { href: "/documents", label: "Documents", number: "01" },
      { href: "/experiences", label: "Experiences", number: "02" },
      { href: "/projects", label: "Projects", number: "03" },
      { href: "/skills", label: "Skills", number: "04" },
      { href: "/publications", label: "Publications", number: "05" },
    ],
  },
  {
    title: "Workflow",
    collapsible: true,
    items: [
      { href: "/jobs", label: "Jobs", number: "06" },
      { href: "/resume", label: "Resume", number: "07" },
    ],
  },
  {
    title: "Account",
    collapsible: true,
    items: [
      { href: "/profile", label: "Profile", number: "08" },
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
      <div className="min-h-screen flex bg-background paper-texture">
        {/* Header - Editorial style */}
        <header className="fixed top-0 left-0 right-0 h-14 bg-background border-b-2 border-foreground z-50 flex items-center justify-between px-6">
          <Link
            href="/"
            className="font-display text-lg tracking-wider uppercase text-foreground hover:text-primary transition-colors"
          >
            Resume Crafter
          </Link>
          <div className="flex items-center gap-6">
            <CommandPalette />
            <span className="font-body text-sm italic text-muted-foreground hidden sm:inline">
              {user?.email}
            </span>
            <button
              onClick={logout}
              className="font-body text-sm text-muted-foreground hover:text-foreground transition-colors underline underline-offset-4"
              aria-label="Sign out of your account"
            >
              Sign out
            </button>
          </div>
        </header>

        {/* Sidebar - Table of contents style */}
        <aside className="fixed top-14 left-0 bottom-0 w-60 border-r-2 border-foreground bg-background overflow-y-auto">
          {/* Vertical rule decoration */}
          <div className="absolute top-0 left-4 bottom-0 w-[2px] bg-border" aria-hidden="true" />

          <nav className="py-8 pl-8 pr-4" role="navigation" aria-label="Main navigation">
            {navSections.map((section, sectionIndex) => (
              <div key={sectionIndex} className="mb-6">
                {section.title && (
                  <button
                    onClick={() => section.collapsible && toggleSection(section.title!)}
                    className="nav-section-title w-full flex items-center justify-between hover:text-foreground transition-colors mb-2"
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
                  <div className="space-y-1">
                    {section.items.map((item) => {
                      const isActive = pathname === item.href;
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          className={`nav-link flex items-center gap-3 ${isActive ? "active" : ""}`}
                          aria-current={isActive ? "page" : undefined}
                        >
                          <span
                            className={`font-mono text-xs ${
                              isActive ? "text-primary" : "text-muted-foreground"
                            }`}
                          >
                            {item.number}
                          </span>
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
        <main className="flex-1 ml-60 mt-14">
          <div className="max-w-3xl mx-auto px-8 py-10">
            {/* Breadcrumbs */}
            <div className="mb-8">
              <Breadcrumbs />
            </div>

            {/* Page content with stagger animation */}
            <div className="stagger-children">
              {children}
            </div>
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
