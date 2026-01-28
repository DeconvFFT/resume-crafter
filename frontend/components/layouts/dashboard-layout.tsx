"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth";
import { useLogout } from "@/hooks/useAuth";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
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
  Menu,
  LogOut,
  Sparkles,
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
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
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
        "group relative flex items-center gap-3 px-3 py-2.5 text-sm rounded-lg transition-all duration-300 ease-out",
        "text-slate-400 hover:text-white",
        isActive ? "text-white" : "hover:bg-white/5"
      )}
      aria-current={isActive ? "page" : undefined}
    >
      {/* Active indicator - animated gradient bar */}
      <AnimatePresence>
        {isActive && (
          <motion.span
            initial={{ opacity: 0, scaleY: 0 }}
            animate={{ opacity: 1, scaleY: 1 }}
            exit={{ opacity: 0, scaleY: 0 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 rounded-r-full bg-gradient-to-b from-violet-500 via-purple-500 to-fuchsia-500"
          />
        )}
      </AnimatePresence>

      {/* Background fill on hover/active */}
      <motion.span
        className={cn(
          "absolute inset-0 rounded-lg -z-10",
          isActive && "bg-gradient-to-r from-violet-500/15 via-purple-500/10 to-transparent"
        )}
        initial={false}
        animate={{
          opacity: isActive ? 1 : 0,
        }}
        transition={{ duration: 0.2 }}
      />

      {/* Icon with hover animation */}
      <motion.span
        whileHover={{ scale: 1.1 }}
        transition={{ type: "spring", stiffness: 400, damping: 17 }}
      >
        <Icon
          className={cn(
            "h-4 w-4 flex-shrink-0 transition-colors duration-300",
            isActive ? "text-violet-400" : "text-slate-500 group-hover:text-violet-400"
          )}
        />
      </motion.span>

      <span className="font-medium">{label}</span>
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
    <nav className="py-5 px-3" role="navigation" aria-label="Main navigation">
      {navSections.map((section, sectionIndex) => (
        <div key={sectionIndex} className="mb-2">
          {section.title && (
            <>
              {/* Section separator */}
              {sectionIndex > 0 && (
                <div className="mx-3 my-4 h-px bg-gradient-to-r from-transparent via-slate-700/50 to-transparent" />
              )}
              <button
                onClick={() => section.collapsible && toggleSection(section.title!)}
                className={cn(
                  "w-full flex items-center justify-between px-3 py-2 mb-2",
                  "text-[10px] font-semibold uppercase tracking-[0.15em]",
                  "text-slate-500 hover:text-slate-300 transition-colors duration-200"
                )}
                aria-expanded={!collapsed[section.title]}
              >
                <span>{section.title}</span>
                {section.collapsible && (
                  <motion.span
                    animate={{ rotate: collapsed[section.title] ? -90 : 0 }}
                    transition={{ duration: 0.2, ease: "easeOut" }}
                  >
                    <ChevronDown
                      className="h-3 w-3"
                      aria-hidden="true"
                    />
                  </motion.span>
                )}
              </button>
            </>
          )}
          <AnimatePresence initial={false}>
            {!collapsed[section.title || ""] && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
                className="space-y-1 overflow-hidden"
              >
                {section.items.map((item, itemIndex) => {
                  const isActive = pathname === item.href ||
                    (item.href !== "/dashboard" && pathname.startsWith(item.href));
                  return (
                    <motion.div
                      key={item.href}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: itemIndex * 0.05, duration: 0.2 }}
                    >
                      <NavItem
                        href={item.href}
                        label={item.label}
                        icon={item.icon}
                        isActive={isActive}
                        onClick={onItemClick}
                      />
                    </motion.div>
                  );
                })}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ))}
    </nav>
  );
}

export function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
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
        {/* Skip navigation link for keyboard users */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[100] focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
        >
          Skip to main content
        </a>

        {/* Header */}
        <header className="fixed top-0 left-0 right-0 h-14 bg-background/95 backdrop-blur-xl supports-[backdrop-filter]:bg-background/60 border-b border-border/50 z-50 flex items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
              <SheetTrigger asChild>
                <button
                  className="md:hidden p-2 -ml-2 hover:bg-muted rounded-md transition-colors"
                  aria-label="Open navigation menu"
                >
                  <Menu className="h-5 w-5" />
                </button>
              </SheetTrigger>
              <SheetContent
                side="left"
                className="w-64 p-0 bg-slate-900/95 backdrop-blur-xl border-r border-slate-800/50"
              >
                <SheetHeader className="p-4 border-b border-slate-800/50">
                  <SheetTitle className="text-left">
                    <span className="flex items-center gap-2">
                      <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 shadow-lg shadow-violet-500/25">
                        <Sparkles className="h-4 w-4 text-white" />
                      </span>
                      <span className="font-bold text-lg bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                        Resume Crafter
                      </span>
                    </span>
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
              href="/dashboard"
              className="flex items-center gap-2 group"
            >
              <span className="hidden md:flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 shadow-lg shadow-violet-500/25 group-hover:shadow-violet-500/40 transition-shadow duration-300">
                <Sparkles className="h-4 w-4 text-white" />
              </span>
              <span className="font-bold text-lg bg-gradient-to-r from-foreground via-foreground to-muted-foreground bg-clip-text text-transparent group-hover:from-violet-400 group-hover:to-fuchsia-400 transition-all duration-300">
                Resume Crafter
              </span>
            </Link>
          </div>

          <div className="flex items-center gap-3">
            <CommandPalette />
            <ThemeToggle />

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

        {/* Sidebar - Executive Noir Design */}
        <aside className="hidden md:flex flex-col fixed top-14 left-0 bottom-0 w-60 bg-slate-900/80 backdrop-blur-xl border-r border-slate-800/50 overflow-hidden transition-all duration-300 ease-out">
          {/* Gradient border effect on right edge */}
          <div className="absolute top-0 right-0 bottom-0 w-px bg-gradient-to-b from-violet-500/20 via-purple-500/10 to-transparent" />

          {/* Navigation area with scroll */}
          <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-track-transparent scrollbar-thumb-slate-700/50 hover:scrollbar-thumb-slate-600/50">
            <SidebarNav
              collapsed={collapsed}
              toggleSection={toggleSection}
            />
          </div>

          {/* User Profile Section - Glassmorphism Card */}
          <motion.div
            className="p-3 border-t border-slate-800/50"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.4 }}
          >
            <motion.div
              className="relative group p-3 rounded-xl bg-slate-800/40 backdrop-blur-sm border border-slate-700/30 cursor-pointer overflow-hidden"
              whileHover={{
                y: -2,
                transition: { duration: 0.2, ease: "easeOut" }
              }}
            >
              {/* Subtle gradient overlay on hover */}
              <div className="absolute inset-0 bg-gradient-to-r from-violet-500/5 via-purple-500/5 to-fuchsia-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

              <div className="relative flex items-center gap-3">
                {/* Avatar with gradient ring */}
                <div className="relative">
                  <div className="absolute -inset-0.5 rounded-full bg-gradient-to-r from-violet-500 via-purple-500 to-fuchsia-500 opacity-50 group-hover:opacity-75 blur-sm transition-opacity duration-300" />
                  <Avatar size="sm" className="relative border-2 border-slate-900">
                    <AvatarFallback
                      size="sm"
                      className="bg-gradient-to-br from-violet-600 to-fuchsia-600 text-white font-semibold"
                    >
                      {userInitials}
                    </AvatarFallback>
                  </Avatar>
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-white truncate">
                    {user?.email?.split('@')[0] || 'User'}
                  </p>
                  <p className="text-xs text-slate-400 truncate">
                    {user?.email || ''}
                  </p>
                </div>
              </div>
            </motion.div>
          </motion.div>
        </aside>

        <main id="main-content" className="flex-1 md:ml-60 mt-14" tabIndex={-1}>
          <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6">
            <div className="mb-6">
              <Breadcrumbs />
            </div>

            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, ease: "easeOut" }}
            >
              {children}
            </motion.div>
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
