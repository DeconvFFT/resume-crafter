"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";
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
  Sparkles,
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

// Animated counter hook
function useAnimatedCounter(end: number, duration: number = 1000) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let startTime: number;
    let animationFrame: number;

    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);

      // Easing function for smooth animation
      const easeOutQuart = 1 - Math.pow(1 - progress, 4);
      setCount(Math.floor(easeOutQuart * end));

      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate);
      }
    };

    animationFrame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrame);
  }, [end, duration]);

  return count;
}

// Stagger animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      type: "spring" as const,
      stiffness: 100,
      damping: 15,
    },
  },
};

const cardHoverVariants = {
  rest: { scale: 1 },
  hover: {
    scale: 1.02,
    transition: { type: "spring" as const, stiffness: 400, damping: 17 }
  },
};

function StatCard({
  label,
  value,
  icon: Icon,
  suffix,
  loading,
  index = 0,
  gradient = "from-teal-500/20 to-cyan-500/20",
  iconGradient = "from-teal-500 to-cyan-500",
}: {
  label: string;
  value: number | string;
  icon: React.ElementType;
  suffix?: string;
  loading?: boolean;
  index?: number;
  gradient?: string;
  iconGradient?: string;
}) {
  const numericValue = typeof value === "number" ? value : parseInt(value) || 0;
  const animatedValue = useAnimatedCounter(numericValue, 1200);

  if (loading) {
    return (
      <div className="relative overflow-hidden rounded-xl border border-white/10 bg-white/5 backdrop-blur-xl p-6">
        <div className="flex items-center justify-between mb-3">
          <Skeleton className="h-12 w-12 rounded-xl" />
          <Skeleton className="h-8 w-20" />
        </div>
        <Skeleton className="h-4 w-28" />
      </div>
    );
  }

  return (
    <motion.div
      variants={itemVariants}
      initial="hidden"
      animate="visible"
      whileHover="hover"
      className="group relative"
      custom={index}
    >
      <motion.div
        variants={cardHoverVariants}
        className={cn(
          "relative overflow-hidden rounded-xl",
          "border border-white/10 bg-white/5 backdrop-blur-xl",
          "p-6 transition-all duration-500",
          "hover:border-teal-500/30 hover:shadow-lg hover:shadow-teal-500/10"
        )}
      >
        {/* Gradient background on hover */}
        <div
          className={cn(
            "absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100",
            `bg-gradient-to-br ${gradient}`
          )}
        />

        {/* Content */}
        <div className="relative z-10">
          <div className="flex items-center justify-between mb-4">
            {/* Icon with gradient glow */}
            <div className="relative">
              <div
                className={cn(
                  "absolute inset-0 blur-xl opacity-50 group-hover:opacity-75 transition-opacity",
                  `bg-gradient-to-r ${iconGradient}`
                )}
              />
              <div
                className={cn(
                  "relative p-3 rounded-xl",
                  "bg-gradient-to-br from-white/10 to-white/5",
                  "border border-white/10 group-hover:border-white/20 transition-colors"
                )}
              >
                <Icon className={cn("h-5 w-5 bg-gradient-to-r bg-clip-text", iconGradient)} style={{ color: 'rgb(20, 184, 166)' }} />
              </div>
            </div>

            {/* Value */}
            <div className="flex items-baseline gap-1">
              <span className="text-3xl font-bold bg-gradient-to-r from-white to-white/80 bg-clip-text text-transparent">
                {typeof value === "number" ? animatedValue : value}
              </span>
              {suffix && (
                <span className="text-lg text-teal-300/80 font-medium">
                  {suffix}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-white/60 font-medium tracking-wide">
              {label}
            </span>
            <TrendingUp className="h-4 w-4 text-teal-400/50 opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

interface Campaign {
  id: string;
  name: string;
  status: string;
  last_run_at: string | null;
  next_run_at: string | null;
}

function CampaignCard({ campaign, index }: { campaign: Campaign; index: number }) {
  const isActive = campaign.status === "active";

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1, type: "spring", stiffness: 100 }}
    >
      <Link
        href={`/automations?campaign=${campaign.id}`}
        className={cn(
          "group relative flex items-center gap-4 p-4 rounded-xl overflow-hidden",
          "border border-white/10 bg-white/5 backdrop-blur-sm",
          "transition-all duration-300",
          "hover:border-teal-500/30 hover:bg-white/[0.07]"
        )}
      >
        {/* Gradient border effect on hover */}
        <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <div className="absolute inset-[-1px] rounded-xl bg-gradient-to-r from-teal-500/20 via-cyan-500/20 to-teal-500/20" />
          <div className="absolute inset-[1px] rounded-[10px] bg-card" />
        </div>

        {/* Status indicator with glow */}
        <div className="relative">
          <div
            className={cn(
              "absolute inset-0 blur-md transition-opacity",
              isActive ? "bg-emerald-500/50 opacity-50" : "opacity-0"
            )}
          />
          <div
            className={cn(
              "relative p-2.5 rounded-lg transition-colors",
              isActive
                ? "bg-emerald-500/20 text-emerald-400"
                : "bg-white/10 text-white/40"
            )}
          >
            {isActive ? (
              <Play className="h-4 w-4" />
            ) : (
              <Pause className="h-4 w-4" />
            )}
          </div>
        </div>

        <div className="relative flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="font-semibold text-white/90 truncate group-hover:text-white transition-colors">
              {campaign.name}
            </h4>
            <span
              className={cn(
                "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize",
                "border backdrop-blur-sm",
                isActive
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                  : "border-white/20 bg-white/5 text-white/50"
              )}
            >
              {isActive && (
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1.5 animate-pulse" />
              )}
              {campaign.status}
            </span>
          </div>
          <div className="flex items-center gap-4 mt-2 text-xs text-white/40">
            {campaign.last_run_at && (
              <span className="flex items-center gap-1.5">
                <Clock className="h-3 w-3" />
                Last: {formatRelativeTime(campaign.last_run_at)}
              </span>
            )}
            {campaign.next_run_at && (
              <span className="flex items-center gap-1.5">
                <Calendar className="h-3 w-3" />
                Next: {formatRelativeTime(campaign.next_run_at)}
              </span>
            )}
          </div>
        </div>

        <ChevronRight className="relative h-4 w-4 text-white/20 group-hover:text-teal-400 group-hover:translate-x-1 transition-all" />
      </Link>
    </motion.div>
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

function ExecutionItem({ execution, index }: { execution: Execution; index: number }) {
  const statusConfig: Record<string, { icon: React.ElementType; color: string; glowColor: string }> = {
    completed: { icon: CheckCircle2, color: "text-emerald-400 bg-emerald-500/20", glowColor: "bg-emerald-500/30" },
    running: { icon: Activity, color: "text-blue-400 bg-blue-500/20", glowColor: "bg-blue-500/30" },
    failed: { icon: AlertCircle, color: "text-red-400 bg-red-500/20", glowColor: "bg-red-500/30" },
    pending: { icon: Clock, color: "text-amber-400 bg-amber-500/20", glowColor: "bg-amber-500/30" },
  };

  const config = statusConfig[execution.status] || statusConfig.pending;
  const Icon = config.icon;

  const timestamp = execution.completed_at || execution.started_at;
  const workflowName = execution.workflow_type || "Workflow";

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.08, type: "spring", stiffness: 100 }}
      className="relative group"
    >
      {/* Timeline connector line */}
      {index > 0 && (
        <div className="absolute -top-3 left-5 w-0.5 h-3 bg-gradient-to-b from-white/10 to-transparent" />
      )}

      <div className="flex items-start gap-4 py-3 px-2 rounded-lg hover:bg-white/5 transition-colors">
        {/* Icon with glow */}
        <div className="relative shrink-0">
          <div className={cn("absolute inset-0 blur-md opacity-50", config.glowColor)} />
          <div className={cn("relative p-2 rounded-lg", config.color)}>
            <Icon className="h-4 w-4" />
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-white/90 truncate">
            {workflowName}
          </p>
          <div className="flex items-center gap-2 mt-1">
            <span className={cn(
              "text-xs capitalize",
              execution.status === "completed" ? "text-emerald-400" :
              execution.status === "running" ? "text-blue-400" :
              execution.status === "failed" ? "text-red-400" : "text-amber-400"
            )}>
              {execution.status}
            </span>
            {timestamp && (
              <>
                <span className="text-white/20">-</span>
                <span className="text-xs text-white/40">
                  {formatRelativeTime(timestamp)}
                </span>
              </>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function QuickActionCard({
  title,
  description,
  icon: Icon,
  href,
  gradient = "from-teal-500 to-cyan-500",
  index = 0,
}: {
  title: string;
  description: string;
  icon: React.ElementType;
  href: string;
  gradient?: string;
  index?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 + index * 0.1, type: "spring", stiffness: 100 }}
      whileHover={{ scale: 1.02, y: -2 }}
      whileTap={{ scale: 0.98 }}
    >
      <Link
        href={href}
        className={cn(
          "group relative flex flex-col p-6 rounded-xl overflow-hidden",
          "border border-white/10 bg-white/5 backdrop-blur-sm",
          "transition-all duration-300",
          "hover:border-teal-500/30 hover:shadow-lg hover:shadow-teal-500/10"
        )}
      >
        {/* Gradient background on hover */}
        <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-gradient-to-br from-teal-500/10 to-cyan-500/10" />

        {/* Icon with animation */}
        <div className="relative mb-4">
          <div className={cn(
            "absolute inset-0 blur-xl opacity-0 group-hover:opacity-50 transition-opacity duration-300",
            `bg-gradient-to-r ${gradient}`
          )} />
          <div className={cn(
            "relative p-3 rounded-xl w-fit",
            "bg-gradient-to-br from-white/10 to-white/5",
            "border border-white/10 group-hover:border-white/20",
            "transition-all duration-300 group-hover:scale-110"
          )}>
            <Icon className="h-5 w-5 text-teal-400 group-hover:text-teal-300 transition-colors" />
          </div>
        </div>

        <h3 className="relative font-semibold text-white/90 group-hover:text-white transition-colors">
          {title}
        </h3>
        <p className="relative text-sm text-white/50 mt-1.5 group-hover:text-white/60 transition-colors">
          {description}
        </p>

        {/* Arrow indicator */}
        <ArrowRight className="absolute bottom-6 right-6 h-4 w-4 text-white/20 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
      </Link>
    </motion.div>
  );
}

// Section header component
function SectionHeader({
  icon: Icon,
  title,
  action,
  actionHref
}: {
  icon: React.ElementType;
  title: string;
  action?: string;
  actionHref?: string;
}) {
  return (
    <div className="flex items-center justify-between mb-5">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-teal-500/20">
          <Icon className="h-4 w-4 text-teal-400" />
        </div>
        <div>
          <h2 className="font-semibold text-white/90">{title}</h2>
          <div className="h-0.5 w-8 mt-1.5 bg-gradient-to-r from-teal-500 to-transparent rounded-full" />
        </div>
      </div>
      {action && actionHref && (
        <Link
          href={actionHref}
          className="group flex items-center gap-1.5 text-sm text-teal-400 hover:text-teal-300 transition-colors"
        >
          {action}
          <ArrowRight className="h-3 w-3 group-hover:translate-x-0.5 transition-transform" />
        </Link>
      )}
    </div>
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
    <div className="relative min-h-screen">
      {/* Background gradient mesh */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute top-0 -left-1/4 w-1/2 h-1/2 bg-teal-500/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-0 -right-1/4 w-1/2 h-1/2 bg-cyan-500/10 rounded-full blur-[120px]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1/3 h-1/3 bg-indigo-500/5 rounded-full blur-[100px]" />
        {/* Subtle grid pattern */}
        <div
          className="absolute inset-0 opacity-[0.02]"
          style={{
            backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
                              linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
            backgroundSize: '50px 50px'
          }}
        />
      </div>

      <div className="relative space-y-8 p-1">
        {/* Welcome Section */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, type: "spring" }}
          className="flex items-start justify-between"
        >
          <div>
            <div className="flex items-center gap-3 mb-2">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
              >
                <Sparkles className="h-6 w-6 text-teal-400" />
              </motion.div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-white via-white/90 to-white/70 bg-clip-text text-transparent">
                Welcome back, {userName}
              </h1>
            </div>
            <p className="text-white/50 text-lg">
              Here is what is happening with your job search today.
            </p>
          </div>
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <Button
              asChild
              className="bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-500 hover:to-cyan-500 border-0 shadow-lg shadow-teal-500/25 hover:shadow-teal-500/40 transition-all duration-300"
            >
              <Link href="/resume" className="gap-2">
                <FileOutput className="h-4 w-4" />
                Generate Resume
              </Link>
            </Button>
          </motion.div>
        </motion.div>

        {/* Stats Row */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="grid grid-cols-4 gap-5"
        >
          <StatCard
            label="Profile Completion"
            value={profileCompletion}
            suffix="%"
            icon={BarChart3}
            loading={isLoading}
            index={0}
            gradient="from-teal-500/20 to-cyan-500/20"
            iconGradient="from-teal-500 to-cyan-500"
          />
          <StatCard
            label="Documents"
            value={documentsCount}
            icon={FileText}
            loading={isLoading}
            index={1}
            gradient="from-blue-500/20 to-cyan-500/20"
            iconGradient="from-blue-500 to-cyan-500"
          />
          <StatCard
            label="Experiences"
            value={experiencesCount}
            icon={Briefcase}
            loading={isLoading}
            index={2}
            gradient="from-emerald-500/20 to-teal-500/20"
            iconGradient="from-emerald-500 to-teal-500"
          />
          <StatCard
            label="Active Campaigns"
            value={activeCampaigns}
            icon={Zap}
            loading={campaignsLoading}
            index={3}
            gradient="from-amber-500/20 to-orange-500/20"
            iconGradient="from-amber-500 to-orange-500"
          />
        </motion.div>

        {/* Two Column Layout */}
        <div className="grid grid-cols-5 gap-6">
          {/* Left Column - Automations + Quick Actions */}
          <div className="col-span-3 space-y-6">
            {/* Active Campaigns */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-xl p-6"
            >
              <SectionHeader
                icon={Activity}
                title="Search Campaigns"
                action="View all"
                actionHref="/automations"
              />

              {campaignsLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-20 w-full rounded-xl" />
                  <Skeleton className="h-20 w-full rounded-xl" />
                </div>
              ) : campaignsList.length > 0 ? (
                <div className="space-y-3">
                  {campaignsList.slice(0, 3).map((campaign: Campaign, index: number) => (
                    <CampaignCard key={campaign.id} campaign={campaign} index={index} />
                  ))}
                </div>
              ) : (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.3 }}
                  className="text-center py-10 border border-dashed border-white/10 rounded-xl bg-white/[0.02]"
                >
                  <div className="relative inline-block mb-4">
                    <div className="absolute inset-0 blur-xl bg-teal-500/30" />
                    <Zap className="relative h-12 w-12 text-teal-400" />
                  </div>
                  <h3 className="font-semibold text-white/90">No campaigns yet</h3>
                  <p className="text-sm text-white/50 mt-2 mb-5">
                    Create a search campaign to automate your job search
                  </p>
                  <Button
                    asChild
                    variant="outline"
                    size="sm"
                    className="border-teal-500/30 bg-teal-500/10 text-teal-300 hover:bg-teal-500/20 hover:text-teal-200"
                  >
                    <Link href="/automations">
                      <Plus className="h-4 w-4 mr-1.5" />
                      Create your first campaign
                    </Link>
                  </Button>
                </motion.div>
              )}
            </motion.div>

            {/* Quick Actions Grid */}
            <div>
              <div className="flex items-center gap-3 mb-5">
                <div className="p-2 rounded-lg bg-teal-500/20">
                  <Sparkles className="h-4 w-4 text-teal-400" />
                </div>
                <div>
                  <h2 className="font-semibold text-white/90">Quick Actions</h2>
                  <div className="h-0.5 w-8 mt-1.5 bg-gradient-to-r from-teal-500 to-transparent rounded-full" />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <QuickActionCard
                  title="Generate Resume"
                  description="Create a tailored resume for a job"
                  icon={FileOutput}
                  href="/resume"
                  gradient="from-teal-500 to-cyan-500"
                  index={0}
                />
                <QuickActionCard
                  title="Add Job"
                  description="Analyze a new job posting"
                  icon={Target}
                  href="/jobs"
                  gradient="from-blue-500 to-cyan-500"
                  index={1}
                />
                <QuickActionCard
                  title="Update Profile"
                  description="Add experiences and skills"
                  icon={User}
                  href="/experiences"
                  gradient="from-emerald-500 to-teal-500"
                  index={2}
                />
              </div>
            </div>
          </div>

          {/* Right Column - Activity Feed */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
            className="col-span-2"
          >
            <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-xl p-6 h-fit sticky top-6">
              <SectionHeader
                icon={Clock}
                title="Recent Activity"
                action="View all"
                actionHref="/automations/executions"
              />

              {executionsLoading ? (
                <div className="space-y-4">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <Skeleton className="h-10 w-10 rounded-lg shrink-0" />
                      <div className="flex-1 space-y-2">
                        <Skeleton className="h-4 w-full" />
                        <Skeleton className="h-3 w-24" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : executionsList.length > 0 ? (
                <div className="relative">
                  {/* Timeline line */}
                  <div className="absolute left-5 top-6 bottom-6 w-0.5 bg-gradient-to-b from-teal-500/30 via-white/10 to-transparent" />

                  <div className="space-y-1">
                    {executionsList.map((execution: Execution, index: number) => (
                      <ExecutionItem key={execution.id} execution={execution} index={index} />
                    ))}
                  </div>
                </div>
              ) : (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.4 }}
                  className="text-center py-10"
                >
                  <div className="relative inline-block mb-4">
                    <div className="absolute inset-0 blur-xl bg-white/10" />
                    <Clock className="relative h-12 w-12 text-white/30" />
                  </div>
                  <h3 className="font-medium text-white/70">No activity yet</h3>
                  <p className="text-sm text-white/40 mt-2">
                    Activity will appear here when you run automations
                  </p>
                </motion.div>
              )}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
