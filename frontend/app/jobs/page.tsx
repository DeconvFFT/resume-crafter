"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { api, handleApiError } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Trash2,
  CheckCircle,
  Clock,
  AlertCircle,
  ExternalLink,
  Target,
  Link as LinkIcon,
  FileText,
  ArrowRight,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";

const statusConfig = {
  pending: { icon: Clock, label: "Queued", color: "text-warning" },
  processing: { icon: Loader2, label: "Processing", color: "text-info" },
  completed: { icon: CheckCircle, label: "Complete", color: "text-success" },
  failed: { icon: AlertCircle, label: "Failed", color: "text-destructive" },
};

export default function JobsPage() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [jobUrl, setJobUrl] = useState("");
  const [jobText, setJobText] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => api.jobs.list(accessToken!),
    enabled: !!accessToken,
  });

  const analyzeMutation = useMutation({
    mutationFn: () =>
      api.jobs.analyze(accessToken!, jobUrl || undefined, jobText || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      toast.success("Job analysis started");
      setJobUrl("");
      setJobText("");
    },
    onError: handleApiError,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.jobs.delete(accessToken!, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      toast.success("Job deleted");
    },
    onError: handleApiError,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!jobUrl && !jobText) {
      toast.error("Please provide a job URL or paste the job description");
      return;
    }
    analyzeMutation.mutate();
  };

  const jobs = data?.items || [];

  return (
    <div className="space-y-12">
      {/* Add Job Section - Editorial Two-Column */}
      <section className="grid gap-8 lg:grid-cols-2">
        {/* URL Input */}
        <div className="border border-border bg-card p-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
                Method 01
              </span>
              <h3 className="font-semibold text-lg mt-1">
                Job URL
              </h3>
            </div>
            <LinkIcon className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
          </div>

          <div className="space-y-6">
            <div className="space-y-3">
              <Label htmlFor="jobUrl">Paste job listing URL</Label>
              <Input
                id="jobUrl"
                type="url"
                placeholder="https://linkedin.com/jobs/..."
                value={jobUrl}
                onChange={(e) => setJobUrl(e.target.value)}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Works with LinkedIn, Indeed, and most job boards
            </p>
          </div>
        </div>

        {/* Text Input */}
        <div className="border border-border bg-card p-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
                Method 02
              </span>
              <h3 className="font-semibold text-lg mt-1">
                Job Description
              </h3>
            </div>
            <FileText className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
          </div>

          <div className="space-y-3">
            <Label htmlFor="jobText">Paste description text</Label>
            <Textarea
              id="jobText"
              placeholder="Paste the full job description here..."
              value={jobText}
              onChange={(e) => setJobText(e.target.value)}
              className="min-h-[120px]"
            />
          </div>
        </div>

        {/* Submit Button - Full Width */}
        <div className="lg:col-span-2">
          <Button
            onClick={handleSubmit}
            disabled={(!jobUrl && !jobText) || analyzeMutation.isPending}
            className="w-full group"
          >
            {analyzeMutation.isPending ? (
              "Analyzing..."
            ) : (
              <>
                Analyze job posting
                <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" aria-hidden="true" />
              </>
            )}
          </Button>
        </div>
      </section>

      {/* Divider */}
      <div className="flex items-center gap-6">
        <div className="flex-1 h-px bg-border" aria-hidden="true" />
        <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
          or
        </span>
        <div className="flex-1 h-px bg-border" aria-hidden="true" />
      </div>

      {/* Job List - Editorial Index Style */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="font-semibold text-xl">Analyzed Jobs</h2>
            <div className="h-1 w-10 bg-foreground mt-3" aria-hidden="true" />
          </div>
          <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
            {jobs.length} job{jobs.length !== 1 ? "s" : ""}
          </span>
        </div>

        {isLoading ? (
          <div className="border border-border bg-card p-12 text-center">
            <Loader2 className="h-6 w-6 mx-auto mb-4 text-muted-foreground animate-spin" aria-hidden="true" />
            <p className="text-sm text-muted-foreground">
              Loading jobs...
            </p>
          </div>
        ) : jobs.length === 0 ? (
          <div className="border border-border bg-card p-12 text-center">
            <Target className="h-8 w-8 mx-auto mb-4 text-muted-foreground" aria-hidden="true" />
            <p className="font-semibold text-lg">No jobs analyzed yet</p>
            <p className="text-sm text-muted-foreground mt-2">
              Add a job posting above to analyze its requirements.
            </p>
          </div>
        ) : (
          <div className="border border-border bg-card divide-y divide-border" role="list">
            {jobs.map((job: any, index: number) => {
              const status = statusConfig[job.processing_status as keyof typeof statusConfig] || statusConfig.pending;
              const StatusIcon = status.icon;
              const isProcessing = job.processing_status === "processing" || job.processing_status === "pending";

              return (
                <div
                  key={job.id}
                  className="p-6 hover:bg-muted/30 transition-colors group"
                  role="listitem"
                >
                  <div className="flex items-start gap-6">
                    {/* Index */}
                    <span className="font-mono text-sm text-muted-foreground w-8 pt-1 flex-shrink-0">
                      {String(index + 1).padStart(2, "0")}
                    </span>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold text-lg truncate group-hover:text-primary transition-colors">
                            {job.role || "Untitled Position"}
                            {job.company && (
                              <span className="text-base font-normal text-muted-foreground ml-2">
                                at {job.company}
                              </span>
                            )}
                          </h3>

                          {/* Meta */}
                          <div className="flex items-center gap-4 mt-2">
                            {job.location && (
                              <span className="font-mono text-2xs uppercase tracking-widest text-muted-foreground">
                                {job.location}
                              </span>
                            )}
                            <span className="font-mono text-2xs uppercase tracking-widest text-muted-foreground">
                              {job.requirements?.length || 0} requirements
                            </span>
                          </div>

                          {/* Requirements Preview */}
                          {job.requirements?.length > 0 && (
                            <div className="mt-4 pl-4 border-l-2 border-border space-y-2">
                              {job.requirements.slice(0, 3).map((req: any, idx: number) => (
                                <div key={req.id} className="flex items-start gap-3">
                                  <span className="font-mono text-2xs text-muted-foreground w-4 flex-shrink-0">
                                    {String(idx + 1).padStart(2, "0")}
                                  </span>
                                  <p className="text-sm text-muted-foreground">
                                    {req.content}
                                  </p>
                                </div>
                              ))}
                              {job.requirements.length > 3 && (
                                <p className="font-mono text-2xs text-muted-foreground">
                                  + {job.requirements.length - 3} more
                                </p>
                              )}
                            </div>
                          )}
                        </div>

                        {/* Status badge */}
                        <span
                          className={cn(
                            "flex items-center gap-2 px-3 py-1.5 border font-mono text-2xs uppercase tracking-widest flex-shrink-0",
                            status.color,
                            job.processing_status === "completed" && "border-success/30 bg-success/5",
                            job.processing_status === "processing" && "border-info/30 bg-info/5",
                            job.processing_status === "pending" && "border-warning/30 bg-warning/5",
                            job.processing_status === "failed" && "border-destructive/30 bg-destructive/5"
                          )}
                        >
                          <StatusIcon
                            className={cn(
                              "h-3 w-3",
                              isProcessing && "animate-spin"
                            )}
                            aria-hidden="true"
                          />
                          {status.label}
                        </span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {job.source_url && (
                        <a
                          href={job.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center justify-center w-10 h-10 border border-transparent hover:border-foreground transition-all"
                          aria-label="Open original job posting"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      )}
                      <button
                        onClick={() => deleteMutation.mutate(job.id)}
                        className="flex items-center justify-center w-10 h-10 border border-transparent hover:border-destructive hover:text-destructive transition-all"
                        aria-label={`Delete ${job.role || "job"}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
