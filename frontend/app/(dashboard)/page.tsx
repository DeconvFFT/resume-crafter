"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth";
import { WorkflowStepper } from "@/components/dashboard/workflow-stepper";
import { QuickActionsPanel } from "@/components/dashboard/quick-actions";
import { ActivityFeed } from "@/components/dashboard/activity-feed";
import { FileText, Briefcase, FolderKanban, Target, FileOutput } from "lucide-react";

export default function DashboardPage() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const user = useAuthStore((state) => state.user);

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

  const userName = user?.email ? user.email.split("@")[0] : "";

  // Build activity feed from all data sources
  const activityItems = [
    ...(documents?.items.map((doc: any) => ({
      id: `doc-${doc.id}`,
      type: "document" as const,
      title: doc.filename || "Untitled Document",
      subtitle: doc.document_class || undefined,
      createdAt: doc.created_at,
      href: "/documents",
    })) || []),
    ...(experiences?.items.map((exp: any) => ({
      id: `exp-${exp.id}`,
      type: "experience" as const,
      title: exp.role || "Untitled Experience",
      subtitle: exp.company || undefined,
      createdAt: exp.created_at,
      href: "/experiences",
    })) || []),
    ...(projects?.items.map((proj: any) => ({
      id: `proj-${proj.id}`,
      type: "project" as const,
      title: proj.name || "Untitled Project",
      subtitle: proj.short_description || undefined,
      createdAt: proj.created_at,
      href: "/projects",
    })) || []),
    ...(jobs?.items.map((job: any) => ({
      id: `job-${job.id}`,
      type: "job" as const,
      title: job.role || "Untitled Job",
      subtitle: job.company || undefined,
      createdAt: job.created_at,
      href: "/jobs",
    })) || []),
    ...(matches?.items.map((match: any) => ({
      id: `match-${match.id}`,
      type: "match" as const,
      title: match.job_role || "Resume Match",
      subtitle: match.job_company || undefined,
      createdAt: match.created_at,
      href: "/resume",
    })) || []),
  ].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

  const stats = [
    { label: "Documents", value: documentsCount, href: "/documents", icon: <FileText className="h-4 w-4" /> },
    { label: "Experiences", value: experiencesCount, href: "/experiences", icon: <Briefcase className="h-4 w-4" /> },
    { label: "Projects", value: projectsCount, href: "/projects", icon: <FolderKanban className="h-4 w-4" /> },
    { label: "Jobs", value: jobsCount, href: "/jobs", icon: <Target className="h-4 w-4" /> },
    { label: "Resumes", value: matchesCount, href: "/resume", icon: <FileOutput className="h-4 w-4" /> },
  ];

  return (
    <div className="space-y-8">
      {/* Welcome Header */}
      <div>
        <h1 className="text-2xl">
          Welcome{userName ? `, ${userName}` : ""}
        </h1>
        <p className="text-muted-foreground mt-1">
          Your resume crafting workspace
        </p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-5 gap-3">
        {stats.map((stat) => (
          <Link
            key={stat.label}
            href={stat.href}
            className="simple-card hover:border-primary/50 transition-all hover:scale-[1.02] group"
          >
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground group-hover:text-primary transition-colors">
                {stat.icon}
              </span>
              <span className="text-2xl font-mono font-bold">{stat.value}</span>
            </div>
            <div className="text-xs text-muted-foreground mt-2">{stat.label}</div>
          </Link>
        ))}
      </div>

      {/* Workflow Stepper */}
      <WorkflowStepper
        documentsCount={documentsCount}
        experiencesCount={experiencesCount}
        projectsCount={projectsCount}
        jobsCount={jobsCount}
        matchesCount={matchesCount}
      />

      {/* Two Column Layout */}
      <div className="grid grid-cols-5 gap-6">
        {/* Quick Actions - 3 columns */}
        <div className="col-span-3">
          <h2 className="text-sm font-medium mb-4">Quick Actions</h2>
          <QuickActionsPanel
            documentsCount={documentsCount}
            experiencesCount={experiencesCount}
            projectsCount={projectsCount}
            jobsCount={jobsCount}
            matchesCount={matchesCount}
          />
        </div>

        {/* Activity Feed - 2 columns */}
        <div className="col-span-2">
          <h2 className="text-sm font-medium mb-4">Recent Activity</h2>
          <ActivityFeed items={activityItems} />
        </div>
      </div>
    </div>
  );
}
