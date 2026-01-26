"use client";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  FileText,
  Briefcase,
  FolderKanban,
  Target,
  FileOutput,
  Play,
  Pause,
  Zap,
  Clock,
  CheckCircle2,
  Calendar,
  Send,
  User,
  Plus,
  ArrowRight,
  ChevronRight,
  TrendingUp,
  Activity,
  BarChart3,
} from "lucide-react";
import { cn } from "@/lib/utils";

// Mock data for automations (will be replaced with real API data)
const mockAutomations = [
  {
    id: "1",
    name: "Daily Job Scan",
    status: "running" as const,
    lastRun: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    successRate: 98,
    runsToday: 3,
  },
  {
    id: "2",
    name: "Resume Tailoring",
    status: "paused" as const,
    lastRun: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    successRate: 100,
    runsToday: 0,
  },
];

// Mock data for activities
const mockActivities = [
  {
    id: "1",
    type: "resume" as const,
    title: "Resume generated for Software Engineer at Google",
    timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    icon: FileOutput,
  },
  {
    id: "2",
    type: "application" as const,
    title: "Application submitted to Microsoft",
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    icon: Send,
  },
  {
    id: "3",
    type: "interview" as const,
    title: "Interview scheduled with Amazon",
    timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    icon: Calendar,
  },
  {
    id: "4",
    type: "job" as const,
    title: "New job match: Senior Developer at Meta",
    timestamp: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
    icon: Target,
  },
  {
    id: "5",
    type: "profile" as const,
    title: "Profile updated with new skills",
    timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    icon: User,
  },
];

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

function StatCard({
  label,
  value,
  icon: Icon,
  suffix,
  trend,
  loading,
}: {
  label: string;
  value: number | string;
  icon: React.ElementType;
  suffix?: string;
  trend?: { value: number; positive: boolean };
  loading?: boolean;
}) {
  if (loading) {
    return (
      <div className="simple-card">
        <div className="flex items-center justify-between mb-3">
          <Skeleton className="h-8 w-8 rounded-lg" />
          <Skeleton className="h-6 w-16" />
        </div>
        <Skeleton className="h-4 w-24" />
      </div>
    );
  }

  return (
    <div className="simple-card group hover:border-primary/30 transition-all duration-200">
      <div className="flex items-center justify-between mb-3">
        <div className="p-2 rounded-lg bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
          <Icon className="h-4 w-4" />
        </div>
        <div className="flex items-baseline gap-1">
          <span className="text-2xl font-semibold">{value}</span>
          {suffix && (
            <span className="text-sm text-muted-foreground">{suffix}</span>
          )}
        </div>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">{label}</span>
        {trend && (
          <span
            className={cn(
              "text-xs font-medium flex items-center gap-0.5",
              trend.positive ? "text-green-600" : "text-red-500"
            )}
          >
            <TrendingUp
              className={cn("h-3 w-3", !trend.positive && "rotate-180")}
            />
            {trend.value}%
          </span>
        )}
      </div>
    </div>
  );
}

function AutomationCard({
  automation,
}: {
  automation: (typeof mockAutomations)[0];
}) {
  const isRunning = automation.status === "running";

  return (
    <div className="flex items-center gap-4 p-4 rounded-lg border border-border bg-card hover:border-primary/30 transition-all group">
      <div
        className={cn(
          "p-2 rounded-lg",
          isRunning ? "bg-green-500/10 text-green-600" : "bg-muted text-muted-foreground"
        )}
      >
        {isRunning ? (
          <Play className="h-4 w-4" />
        ) : (
          <Pause className="h-4 w-4" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h4 className="font-medium truncate">{automation.name}</h4>
          <span
            className={cn(
              "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
              isRunning
                ? "bg-green-500/10 text-green-600"
                : "bg-muted text-muted-foreground"
            )}
          >
            {isRunning ? "Running" : "Paused"}
          </span>
        </div>
        <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatRelativeTime(automation.lastRun)}
          </span>
          <span className="flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" />
            {automation.successRate}% success
          </span>
        </div>
      </div>
      <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
    </div>
  );
}

function ActivityItem({
  activity,
}: {
  activity: (typeof mockActivities)[0];
}) {
  const Icon = activity.icon;

  const typeColors: Record<string, string> = {
    resume: "text-primary bg-primary/10",
    application: "text-blue-600 bg-blue-500/10",
    interview: "text-green-600 bg-green-500/10",
    job: "text-amber-600 bg-amber-500/10",
    profile: "text-purple-600 bg-purple-500/10",
  };

  return (
    <div className="flex items-start gap-3 py-3">
      <div className={cn("p-2 rounded-lg shrink-0", typeColors[activity.type])}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{activity.title}</p>
        <p className="text-xs text-muted-foreground mt-0.5">
          {formatRelativeTime(activity.timestamp)}
        </p>
      </div>
    </div>
  );
}

function QuickActionCard({
  title,
  description,
  icon: Icon,
  href,
}: {
  title: string;
  description: string;
  icon: React.ElementType;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="simple-card group hover:border-primary/30 hover:shadow-md transition-all duration-200"
    >
      <div className="p-2 rounded-lg bg-muted text-muted-foreground group-hover:bg-primary group-hover:text-primary-foreground transition-colors w-fit mb-4">
        <Icon className="h-5 w-5" />
      </div>
      <h3 className="font-medium group-hover:text-primary transition-colors">
        {title}
      </h3>
      <p className="text-sm text-muted-foreground mt-1">{description}</p>
    </Link>
  );
}

export default function DashboardPage() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const user = useAuthStore((state) => state.user);
  const [isLoading, setIsLoading] = useState(true);

  // Simulate loading state
  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 1000);
    return () => clearTimeout(timer);
  }, []);

  const { data: documents } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.documents.list(accessToken!),
    enabled: !!accessToken,
  });

  const { data: experiences } = useQuery({
    queryKey: ["experiences"],
    queryFn: () => api.experiences.list(accessToken!),
    enabled: !!accessToken,
  });

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.projects.list(accessToken!),
    enabled: !!accessToken,
  });

  const { data: jobs } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => api.jobs.list(accessToken!),
    enabled: !!accessToken,
  });

  const { data: matches } = useQuery({
    queryKey: ["matches"],
    queryFn: () => api.resume.listMatches(accessToken!),
    enabled: !!accessToken,
  });

  const documentsCount = documents?.items.length || 0;
  const experiencesCount = experiences?.items.length || 0;
  const projectsCount = projects?.items.length || 0;
  const jobsCount = jobs?.items.length || 0;
  const matchesCount = matches?.items.length || 0;

  const userName = user?.email ? user.email.split("@")[0] : "there";

  // Calculate profile completion
  const profileCompletion = Math.min(
    100,
    Math.round(
      ((documentsCount > 0 ? 25 : 0) +
        (experiencesCount > 0 ? 25 : 0) +
        (projectsCount > 0 ? 25 : 0) +
        (jobsCount > 0 ? 25 : 0))
    )
  );

  // Mock stats for demo
  const activeAutomations = mockAutomations.filter(
    (a) => a.status === "running"
  ).length;
  const applicationsSent = 12;
  const interviewsScheduled = 3;

  const hasAutomations = mockAutomations.length > 0;

  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold">
            Welcome back, {userName}
          </h1>
          <p className="text-muted-foreground mt-1">
            Here is what is happening with your job search today.
          </p>
        </div>
        <Button asChild>
          <Link href="/resume">
            <FileOutput className="h-4 w-4 mr-2" />
            Generate Resume
          </Link>
        </Button>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          label="Profile Completion"
          value={profileCompletion}
          suffix="%"
          icon={BarChart3}
          loading={isLoading}
        />
        <StatCard
          label="Active Automations"
          value={activeAutomations}
          icon={Zap}
          trend={{ value: 12, positive: true }}
          loading={isLoading}
        />
        <StatCard
          label="Applications Sent"
          value={applicationsSent}
          icon={Send}
          trend={{ value: 8, positive: true }}
          loading={isLoading}
        />
        <StatCard
          label="Interviews Scheduled"
          value={interviewsScheduled}
          icon={Calendar}
          loading={isLoading}
        />
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-5 gap-6">
        {/* Left Column - Automations + Quick Actions */}
        <div className="col-span-3 space-y-6">
          {/* Active Automations */}
          <div className="simple-card">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-primary" />
                <h2 className="font-semibold">Active Automations</h2>
              </div>
              <Link
                href="/automations"
                className="text-sm text-primary hover:text-primary/80 flex items-center gap-1 transition-colors"
              >
                View all
                <ArrowRight className="h-3 w-3" />
              </Link>
            </div>

            {isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-20 w-full rounded-lg" />
                <Skeleton className="h-20 w-full rounded-lg" />
              </div>
            ) : hasAutomations ? (
              <div className="space-y-3">
                {mockAutomations.map((automation) => (
                  <AutomationCard key={automation.id} automation={automation} />
                ))}
              </div>
            ) : (
              <div className="text-center py-8 border border-dashed border-border rounded-lg">
                <Zap className="h-10 w-10 mx-auto text-muted-foreground/50 mb-3" />
                <h3 className="font-medium">No automations yet</h3>
                <p className="text-sm text-muted-foreground mt-1 mb-4">
                  Automate your job search workflow
                </p>
                <Button asChild variant="outline" size="sm">
                  <Link href="/automations">
                    <Plus className="h-4 w-4 mr-1" />
                    Set up your first automation
                  </Link>
                </Button>
              </div>
            )}
          </div>

          {/* Quick Actions Grid */}
          <div>
            <h2 className="font-semibold mb-4">Quick Actions</h2>
            <div className="grid grid-cols-3 gap-4">
              <QuickActionCard
                title="Generate Resume"
                description="Create a tailored resume for a job"
                icon={FileOutput}
                href="/resume"
              />
              <QuickActionCard
                title="View Applications"
                description="Track your job applications"
                icon={Briefcase}
                href="/jobs"
              />
              <QuickActionCard
                title="Update Profile"
                description="Add experiences and skills"
                icon={User}
                href="/experiences"
              />
            </div>
          </div>
        </div>

        {/* Right Column - Activity Feed */}
        <div className="col-span-2">
          <div className="simple-card h-fit">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-primary" />
                <h2 className="font-semibold">Recent Activity</h2>
              </div>
              <Link
                href="#"
                className="text-sm text-primary hover:text-primary/80 flex items-center gap-1 transition-colors"
              >
                View all
                <ArrowRight className="h-3 w-3" />
              </Link>
            </div>

            {isLoading ? (
              <div className="space-y-4">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <Skeleton className="h-8 w-8 rounded-lg shrink-0" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-4 w-full" />
                      <Skeleton className="h-3 w-20" />
                    </div>
                  </div>
                ))}
              </div>
            ) : mockActivities.length > 0 ? (
              <div className="divide-y divide-border">
                {mockActivities.slice(0, 5).map((activity) => (
                  <ActivityItem key={activity.id} activity={activity} />
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Clock className="h-10 w-10 mx-auto text-muted-foreground/50 mb-3" />
                <h3 className="font-medium">No activity yet</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Start by generating your first resume
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
