"use client";

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
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

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
  loading,
}: {
  label: string;
  value: number | string;
  icon: React.ElementType;
  suffix?: string;
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
      </div>
    </div>
  );
}

interface Campaign {
  id: string;
  name: string;
  status: string;
  last_run_at: string | null;
  next_run_at: string | null;
}

function CampaignCard({ campaign }: { campaign: Campaign }) {
  const isActive = campaign.status === "active";

  return (
    <Link
      href={`/automations?campaign=${campaign.id}`}
      className="flex items-center gap-4 p-4 rounded-lg border border-border bg-card hover:border-primary/30 transition-all group"
    >
      <div
        className={cn(
          "p-2 rounded-lg",
          isActive
            ? "bg-green-500/10 text-green-600"
            : "bg-muted text-muted-foreground"
        )}
      >
        {isActive ? (
          <Play className="h-4 w-4" />
        ) : (
          <Pause className="h-4 w-4" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h4 className="font-medium truncate">{campaign.name}</h4>
          <span
            className={cn(
              "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize",
              isActive
                ? "bg-green-500/10 text-green-600"
                : "bg-muted text-muted-foreground"
            )}
          >
            {campaign.status}
          </span>
        </div>
        <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
          {campaign.last_run_at && (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Last: {formatRelativeTime(campaign.last_run_at)}
            </span>
          )}
          {campaign.next_run_at && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              Next: {formatRelativeTime(campaign.next_run_at)}
            </span>
          )}
        </div>
      </div>
      <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
    </Link>
  );
}

interface Execution {
  id: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  workflow_type?: string;
  results?: Record<string, unknown>;
}

function ExecutionItem({ execution }: { execution: Execution }) {
  const statusIcons: Record<string, React.ElementType> = {
    completed: CheckCircle2,
    running: Activity,
    failed: AlertCircle,
    pending: Clock,
  };
  const statusColors: Record<string, string> = {
    completed: "text-green-600 bg-green-500/10",
    running: "text-blue-600 bg-blue-500/10",
    failed: "text-red-600 bg-red-500/10",
    pending: "text-amber-600 bg-amber-500/10",
  };

  const Icon = statusIcons[execution.status] || Clock;
  const colorClass = statusColors[execution.status] || statusColors.pending;

  const timestamp = execution.completed_at || execution.started_at;
  const workflowName = execution.workflow_type || "Workflow";

  return (
    <div className="flex items-start gap-3 py-3">
      <div className={cn("p-2 rounded-lg shrink-0", colorClass)}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">
          {workflowName} - {execution.status}
        </p>
        {timestamp && (
          <p className="text-xs text-muted-foreground mt-0.5">
            {formatRelativeTime(timestamp)}
          </p>
        )}
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

export default function DashboardClient() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const user = useAuthStore((state) => state.user);

  // Fetch real data from API
  const { data: documents, isLoading: docsLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.documents.list(accessToken!),
    enabled: !!accessToken,
  });

  const { data: experiences, isLoading: expLoading } = useQuery({
    queryKey: ["experiences"],
    queryFn: () => api.experiences.list(accessToken!),
    enabled: !!accessToken,
  });

  const { data: projects, isLoading: projLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.projects.list(accessToken!),
    enabled: !!accessToken,
  });

  const { data: jobs, isLoading: jobsLoading } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => api.jobs.list(accessToken!),
    enabled: !!accessToken,
  });

  const { data: skills, isLoading: skillsLoading } = useQuery({
    queryKey: ["skills"],
    queryFn: () => api.skills.list(accessToken!),
    enabled: !!accessToken,
  });

  // Fetch campaigns (automations)
  const { data: campaigns, isLoading: campaignsLoading } = useQuery({
    queryKey: ["campaigns"],
    queryFn: () => api.automation.campaigns.list(accessToken!),
    enabled: !!accessToken,
  });

  // Fetch recent executions for activity feed
  const { data: executions, isLoading: executionsLoading } = useQuery({
    queryKey: ["executions", { page: 1, page_size: 5 }],
    queryFn: () => api.automation.executions.list(accessToken!, { page: 1, page_size: 5 }),
    enabled: !!accessToken,
  });

  const isLoading =
    docsLoading ||
    expLoading ||
    projLoading ||
    jobsLoading ||
    skillsLoading ||
    campaignsLoading;

  const documentsCount = documents?.items?.length || 0;
  const experiencesCount = experiences?.items?.length || 0;
  const projectsCount = projects?.items?.length || 0;
  const jobsCount = jobs?.items?.length || 0;
  const skillsCount = skills?.items?.length || 0;

  const campaignsList = campaigns?.items || [];
  const activeCampaigns = campaignsList.filter(
    (c: Campaign) => c.status === "active"
  ).length;
  const executionsList = executions?.items || [];

  const userName = user?.email ? user.email.split("@")[0] : "there";

  // Calculate profile completion based on real data
  const profileCompletion = Math.min(
    100,
    Math.round(
      ((documentsCount > 0 ? 20 : 0) +
        (experiencesCount > 0 ? 20 : 0) +
        (projectsCount > 0 ? 20 : 0) +
        (skillsCount > 0 ? 20 : 0) +
        (jobsCount > 0 ? 20 : 0))
    )
  );

  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Welcome back, {userName}</h1>
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
          label="Documents"
          value={documentsCount}
          icon={FileText}
          loading={isLoading}
        />
        <StatCard
          label="Experiences"
          value={experiencesCount}
          icon={Briefcase}
          loading={isLoading}
        />
        <StatCard
          label="Active Campaigns"
          value={activeCampaigns}
          icon={Zap}
          loading={campaignsLoading}
        />
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-5 gap-6">
        {/* Left Column - Automations + Quick Actions */}
        <div className="col-span-3 space-y-6">
          {/* Active Campaigns */}
          <div className="simple-card">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-primary" />
                <h2 className="font-semibold">Search Campaigns</h2>
              </div>
              <Link
                href="/automations"
                className="text-sm text-primary hover:text-primary/80 flex items-center gap-1 transition-colors"
              >
                View all
                <ArrowRight className="h-3 w-3" />
              </Link>
            </div>

            {campaignsLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-20 w-full rounded-lg" />
                <Skeleton className="h-20 w-full rounded-lg" />
              </div>
            ) : campaignsList.length > 0 ? (
              <div className="space-y-3">
                {campaignsList.slice(0, 3).map((campaign: Campaign) => (
                  <CampaignCard key={campaign.id} campaign={campaign} />
                ))}
              </div>
            ) : (
              <div className="text-center py-8 border border-dashed border-border rounded-lg">
                <Zap className="h-10 w-10 mx-auto text-muted-foreground/50 mb-3" />
                <h3 className="font-medium">No campaigns yet</h3>
                <p className="text-sm text-muted-foreground mt-1 mb-4">
                  Create a search campaign to automate your job search
                </p>
                <Button asChild variant="outline" size="sm">
                  <Link href="/automations">
                    <Plus className="h-4 w-4 mr-1" />
                    Create your first campaign
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
                title="Add Job"
                description="Analyze a new job posting"
                icon={Target}
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
                href="/automations/executions"
                className="text-sm text-primary hover:text-primary/80 flex items-center gap-1 transition-colors"
              >
                View all
                <ArrowRight className="h-3 w-3" />
              </Link>
            </div>

            {executionsLoading ? (
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
            ) : executionsList.length > 0 ? (
              <div className="divide-y divide-border">
                {executionsList.map((execution: Execution) => (
                  <ExecutionItem key={execution.id} execution={execution} />
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Clock className="h-10 w-10 mx-auto text-muted-foreground/50 mb-3" />
                <h3 className="font-medium">No activity yet</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Activity will appear here when you run automations
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
