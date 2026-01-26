"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { api, handleApiError } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth";
import { Button } from "@/components/ui/button";
import {
  Download,
  FileJson,
  FileText,
  CheckCircle,
  Clock,
  FileOutput,
  ArrowRight,
  Loader2,
  Target,
  Trash2,
} from "lucide-react";
import { cn } from "@/lib/utils";

export default function ResumePage() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [selectedJob, setSelectedJob] = useState<string | null>(null);

  const { data: jobs } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => api.jobs.list(accessToken!),
    enabled: !!accessToken,
  });

  const { data: matches, isLoading: matchesLoading } = useQuery({
    queryKey: ["matches"],
    queryFn: () => api.resume.listMatches(accessToken!),
    enabled: !!accessToken,
  });

  const createMatchMutation = useMutation({
    mutationFn: (jobId: string) => api.resume.createMatch(accessToken!, jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["matches"] });
      toast.success("Match generation started");
      setSelectedJob(null);
    },
    onError: handleApiError,
  });

  const generateMutation = useMutation({
    mutationFn: ({
      matchId,
      format,
    }: {
      matchId: string;
      format: "json" | "markdown";
    }) => api.resume.generate(accessToken!, matchId, format),
    onSuccess: (data) => {
      if (data.format === "markdown") {
        const blob = new Blob([data.content as string], { type: "text/markdown" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "resume.md";
        a.click();
        URL.revokeObjectURL(url);
        toast.success("Resume downloaded");
      } else {
        console.log("Generated resume:", data.content);
        toast.success("Resume generated (check console)");
      }
    },
    onError: handleApiError,
  });

  const deleteMutation = useMutation({
    mutationFn: (matchId: string) => api.resume.deleteMatch(accessToken!, matchId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["matches"] });
      toast.success("Match deleted");
    },
    onError: handleApiError,
  });

  const handleDelete = (matchId: string, jobTitle: string) => {
    if (window.confirm(`Are you sure you want to delete the match for "${jobTitle}"?`)) {
      deleteMutation.mutate(matchId);
    }
  };

  const completedJobs = jobs?.items.filter(
    (j: any) => j.processing_status === "completed"
  );

  const matchList = matches?.items || [];

  return (
    <div className="space-y-12">
      {/* Create Match Section */}
      <section className="border border-border bg-card p-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
              Step 01
            </span>
            <h2 className="font-semibold text-xl mt-1">
              Select Target Job
            </h2>
            <div className="h-1 w-10 bg-foreground mt-3" aria-hidden="true" />
          </div>
          <Target className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
        </div>

        <p className="text-sm text-muted-foreground mb-6">
          Choose a job to match your experience against and generate a tailored resume.
        </p>

        {completedJobs?.length === 0 ? (
          <div className="border-2 border-dashed border-border p-8 text-center">
            <Target className="h-8 w-8 mx-auto mb-4 text-muted-foreground" aria-hidden="true" />
            <p className="font-semibold text-lg">No analyzed jobs available</p>
            <p className="text-sm text-muted-foreground mt-2">
              Add and analyze a job first to create matches.
            </p>
          </div>
        ) : (
          <>
            {/* Job Selection - Editorial Radio Style */}
            <div className="space-y-3 mb-6" role="radiogroup" aria-label="Select a job">
              {completedJobs?.map((job: any, index: number) => (
                <label
                  key={job.id}
                  className={cn(
                    "flex items-center gap-4 p-4 border cursor-pointer transition-all group",
                    selectedJob === job.id
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-foreground"
                  )}
                >
                  <input
                    type="radio"
                    name="job"
                    value={job.id}
                    checked={selectedJob === job.id}
                    onChange={() => setSelectedJob(job.id)}
                    className="sr-only"
                  />

                  {/* Index */}
                  <span className="font-mono text-sm text-muted-foreground w-6">
                    {String(index + 1).padStart(2, "0")}
                  </span>

                  {/* Radio indicator */}
                  <div
                    className={cn(
                      "w-5 h-5 border-2 flex items-center justify-center flex-shrink-0 transition-colors",
                      selectedJob === job.id
                        ? "border-primary"
                        : "border-muted-foreground group-hover:border-foreground"
                    )}
                  >
                    {selectedJob === job.id && (
                      <div className="w-2.5 h-2.5 bg-primary" />
                    )}
                  </div>

                  {/* Job info */}
                  <div className="flex-1 min-w-0">
                    <p className={cn(
                      "text-sm font-medium truncate transition-colors",
                      selectedJob === job.id ? "text-primary" : "group-hover:text-foreground"
                    )}>
                      {job.role || "Untitled"}
                      {job.company && (
                        <span className="font-normal text-muted-foreground ml-2">
                          at {job.company}
                        </span>
                      )}
                    </p>
                    <p className="font-mono text-2xs text-muted-foreground uppercase tracking-widest mt-1">
                      {job.requirements?.length || 0} requirements
                    </p>
                  </div>
                </label>
              ))}
            </div>

            <Button
              onClick={() => selectedJob && createMatchMutation.mutate(selectedJob)}
              disabled={!selectedJob || createMatchMutation.isPending}
              className="w-full group"
            >
              {createMatchMutation.isPending ? (
                "Generating match..."
              ) : (
                <>
                  Generate match
                  <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" aria-hidden="true" />
                </>
              )}
            </Button>
          </>
        )}
      </section>

      {/* Matches List */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <div>
            <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
              Step 02
            </span>
            <h2 className="font-semibold text-xl mt-1">
              Your Resume Matches
            </h2>
            <div className="h-1 w-10 bg-foreground mt-3" aria-hidden="true" />
          </div>
          <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
            {matchList.length} match{matchList.length !== 1 ? "es" : ""}
          </span>
        </div>

        {matchesLoading ? (
          <div className="border border-border bg-card p-12 text-center">
            <Loader2 className="h-6 w-6 mx-auto mb-4 text-muted-foreground animate-spin" aria-hidden="true" />
            <p className="text-sm text-muted-foreground">
              Loading matches...
            </p>
          </div>
        ) : matchList.length === 0 ? (
          <div className="border border-border bg-card p-12 text-center">
            <FileOutput className="h-8 w-8 mx-auto mb-4 text-muted-foreground" aria-hidden="true" />
            <p className="font-semibold text-lg">No matches yet</p>
            <p className="text-sm text-muted-foreground mt-2">
              Select a job above to generate your first match.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {matchList.map((match: any, index: number) => {
              const isCompleted = match.processing_status === "completed";
              const isProcessing = match.processing_status === "processing" || match.processing_status === "pending";

              return (
                <div
                  key={match.id}
                  className="border border-border bg-card hover:border-foreground transition-colors group"
                >
                  <div className="p-6">
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
                              {match.job_role || "Match"}
                              {match.job_company && (
                                <span className="text-base font-normal text-muted-foreground ml-2">
                                  at {match.job_company}
                                </span>
                              )}
                            </h3>

                            {/* Status and Scores */}
                            <div className="flex items-center gap-4 mt-3">
                              {isCompleted ? (
                                <>
                                  <span className="flex items-center gap-1.5 font-mono text-2xs uppercase tracking-widest text-success">
                                    <CheckCircle className="h-3 w-3" aria-hidden="true" />
                                    Complete
                                  </span>
                                  <span className="font-mono text-2xs text-muted-foreground">
                                    Score:{" "}
                                    <span className="text-foreground font-medium">
                                      {Math.round(match.overall_match_score * 100)}%
                                    </span>
                                  </span>
                                  <span className="font-mono text-2xs text-muted-foreground">
                                    Coverage:{" "}
                                    <span className="text-foreground font-medium">
                                      {Math.round(match.skill_coverage * 100)}%
                                    </span>
                                  </span>
                                </>
                              ) : (
                                <span className="flex items-center gap-1.5 font-mono text-2xs uppercase tracking-widest text-info">
                                  <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
                                  Processing
                                </span>
                              )}
                            </div>
                          </div>

                          {/* Score Badge (for completed) */}
                          {isCompleted && (
                            <div className="flex flex-col items-center justify-center w-16 h-16 border-2 border-primary bg-primary/5 flex-shrink-0">
                              <span className="text-2xl font-bold text-primary">
                                {Math.round(match.overall_match_score * 100)}
                              </span>
                              <span className="font-mono text-2xs text-muted-foreground uppercase">
                                Match
                              </span>
                            </div>
                          )}

                          {/* Delete Button */}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(match.id, match.job_role || "this match")}
                            disabled={deleteMutation.isPending}
                            className="text-muted-foreground hover:text-destructive hover:bg-destructive/10 flex-shrink-0"
                            title="Delete match"
                          >
                            <Trash2 className="h-4 w-4" aria-hidden="true" />
                          </Button>
                        </div>
                      </div>
                    </div>

                    {/* Export Actions */}
                    {isCompleted && (
                      <div className="flex items-center gap-3 mt-6 pt-6 border-t border-border pl-14">
                        <span className="font-mono text-2xs uppercase tracking-widest text-muted-foreground mr-2">
                          Export
                        </span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() =>
                            generateMutation.mutate({
                              matchId: match.id,
                              format: "json",
                            })
                          }
                          disabled={generateMutation.isPending}
                        >
                          <FileJson className="h-4 w-4 mr-2" aria-hidden="true" />
                          JSON
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() =>
                            generateMutation.mutate({
                              matchId: match.id,
                              format: "markdown",
                            })
                          }
                          disabled={generateMutation.isPending}
                        >
                          <FileText className="h-4 w-4 mr-2" aria-hidden="true" />
                          Markdown
                        </Button>
                        <Button
                          size="sm"
                          onClick={() =>
                            generateMutation.mutate({
                              matchId: match.id,
                              format: "markdown",
                            })
                          }
                          disabled={generateMutation.isPending}
                          className="group"
                        >
                          <Download className="h-4 w-4 mr-2" aria-hidden="true" />
                          Download
                          <ArrowRight className="ml-2 h-4 w-4 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" aria-hidden="true" />
                        </Button>
                      </div>
                    )}
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
