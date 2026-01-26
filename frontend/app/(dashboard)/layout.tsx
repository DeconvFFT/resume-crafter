"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth";
import { useLogout } from "@/hooks/useAuth";
import { useState } from "react";
import {
  ChevronDown,
  LayoutDashboard,
  FileText,
  Briefcase,
  FolderKanban,
  Star,
  BookOpen,
  Target,
  User,
  Zap,
  Activity,
  Settings,
  Menu,
  LogOut,
} from "lucide-react";
import { AuthGuard } from "@/components/auth/auth-guard";
import { CommandPalette } from "@/components/navigation/command-palette";
import { Breadcrumbs } from "@/components/navigation/breadcrumbs";
import { ThemeToggle } from "@/components/theme-toggle";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

const navSections = [
  {
    title: null,
    items: [
      { href: "/", label: "Dashboard", icon: LayoutDashboard },
    ],
  },
  {
    title: "Profile",
    collapsible: true,
    items: [
      { href: "/profile", label: "Profile", icon: User },
      { href: "/experiences", label: "Experiences", icon: Briefcase },
      { href: "/projects", label: "Projects", icon: FolderKanban },
      { href: "/skills", label: "Skills", icon: Star },
      { href: "/publications", label: "Publications", icon: BookOpen },
    ],
  },
  {
    title: "Automations",
    collapsible: true,
    items: [
      { href: "/automations", label: "Workflows", icon: Zap },
      { href: "/automations/executions", label: "Executions", icon: Activity },
    ],
  },
  {
    title: "Documents",
    collapsible: true,
    items: [
      { href: "/documents", label: "My Resumes", icon: FileText },
      { href: "/jobs", label: "Jobs", icon: Target },
    ],
  },
];

interface NavItemProps {
  href: string;
  label: string;
  icon: React.ElementType;
  isActive: boolean;
  onClick?: () => void;
}

function NavItem({ href, label, icon: Icon, isActive, onClick }: NavItemProps) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className={cn(
        "group relative flex items-center gap-3 px-3 py-2 text-sm rounded-md transition-all duration-200",
        "text-muted-foreground hover:text-foreground hover:bg-muted",
        isActive && "bg-primary/10 text-primary font-medium"
      )}
      aria-current={isActive ? "page" : undefined}
    >
      {/* Active indicator */}
      {isActive && (
        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-primary rounded-r-full" />
      )}
      <Icon className="h-4 w-4 flex-shrink-0" />
      <span>{label}</span>
    </Link>
  );
}

interface SidebarNavProps {
  collapsed: Record<string, boolean>;
  toggleSection: (title: string) => void;
  onItemClick?: () => void;
}

function SidebarNav({ collapsed, toggleSection, onItemClick }: SidebarNavProps) {
  const pathname = usePathname();

  return (
    <nav className="py-4 px-3" role="navigation" aria-label="Main navigation">
      {navSections.map((section, sectionIndex) => (
        <div key={sectionIndex} className="mb-4">
          {section.title && (
            <button
              onClick={() => section.collapsible && toggleSection(section.title!)}
              className={cn(
                "w-full flex items-center justify-between px-3 py-2 mb-1",
                "text-xs font-semibold uppercase tracking-wider",
                "text-muted-foreground hover:text-foreground transition-colors"
              )}
              aria-expanded={!collapsed[section.title]}
            >
              <span>{section.title}</span>
              {section.collapsible && (
                <ChevronDown
                  className={cn(
                    "h-3 w-3 transition-transform duration-200",
                    collapsed[section.title] && "-rotate-90"
                  )}
                  aria-hidden="true"
                />
              )}
            </button>
          )}
          {!collapsed[section.title || ""] && (
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const isActive = pathname === item.href ||
                  (item.href !== "/" && pathname.startsWith(item.href));
                return (
                  <NavItem
                    key={item.href}
                    href={item.href}
                    label={item.label}
                    icon={item.icon}
                    isActive={isActive}
                    onClick={onItemClick}
                  />
                );
              })}
            </div>
          )}
        </div>
      ))}
    </nav>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const user = useAuthStore((state) => state.user);
  const logout = useLogout();
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const toggleSection = (title: string) => {
    setCollapsed((prev) => ({ ...prev, [title]: !prev[title] }));
  };

  const userInitials = user?.email
    ? user.email.substring(0, 2).toUpperCase()
    : "U";

  return (
    <AuthGuard>
      <div className="min-h-screen flex bg-background">
        {/* Header - Modern SaaS style */}
        <header className="fixed top-0 left-0 right-0 h-14 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b border-border z-50 flex items-center justify-between px-4">
          <div className="flex items-center gap-3">
            {/* Mobile menu trigger */}
            <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
              <SheetTrigger asChild>
                <button
                  className="md:hidden p-2 -ml-2 hover:bg-muted rounded-md transition-colors"
                  aria-label="Open navigation menu"
                >
                  <Menu className="h-5 w-5" />
                </button>
              </SheetTrigger>
              <SheetContent side="left" className="w-64 p-0">
                <SheetHeader className="p-4 border-b border-border">
                  <SheetTitle className="text-left font-semibold">
                    Resume Crafter
                  </SheetTitle>
                </SheetHeader>
                <div className="overflow-y-auto h-[calc(100vh-5rem)]">
                  <SidebarNav
                    collapsed={collapsed}
                    toggleSection={toggleSection}
                    onItemClick={() => setMobileMenuOpen(false)}
                  />
                </div>
              </SheetContent>
            </Sheet>

            <Link
              href="/"
              className="font-semibold text-lg text-foreground hover:text-primary transition-colors"
            >
              Resume Crafter
            </Link>
          </div>

          <div className="flex items-center gap-3">
            <CommandPalette />
            <ThemeToggle />

            {/* User menu */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground hidden sm:inline max-w-[150px] truncate">
                {user?.email}
              </span>
              <button
                onClick={logout}
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors p-2 hover:bg-muted rounded-md"
                aria-label="Sign out of your account"
              >
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Sign out</span>
              </button>
            </div>
          </div>
        </header>

        {/* Desktop Sidebar - Modern icon + label style */}
        <aside className="hidden md:block fixed top-14 left-0 bottom-0 w-56 border-r border-border bg-card/50 overflow-y-auto scrollbar-thin">
          <SidebarNav
            collapsed={collapsed}
            toggleSection={toggleSection}
          />

          {/* User section at bottom */}
          <div className="absolute bottom-0 left-0 right-0 p-3 border-t border-border bg-card/50">
            <div className="flex items-center gap-3 px-3 py-2">
              <Avatar size="sm">
                <AvatarFallback size="sm">{userInitials}</AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">
                  {user?.email?.split('@')[0] || 'User'}
                </p>
                <p className="text-xs text-muted-foreground truncate">
                  {user?.email || ''}
                </p>
              </div>
            </div>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 md:ml-56 mt-14">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6">
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
