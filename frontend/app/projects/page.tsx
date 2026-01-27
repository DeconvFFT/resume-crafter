"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { api, handleApiError } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ExternalLink, Github, Plus, Trash2, Sparkles, Loader2, CheckCircle2 } from "lucide-react";
import type { TaskStatusResponse } from "@/lib/types/api";

export default function ProjectsPage() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isEnrichDialogOpen, setIsEnrichDialogOpen] = useState(false);
  const [enrichProjectId, setEnrichProjectId] = useState<string | null>(null);
  const [githubUrl, setGithubUrl] = useState("");

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [technologies, setTechnologies] = useState("");
  const [githubRepoUrl, setGithubRepoUrl] = useState("");
  const [bullets, setBullets] = useState<string[]>([""]);

  // Task status tracking for enrichment
  const [taskStatuses, setTaskStatuses] = useState<Record<string, TaskStatusResponse>>({});

  const { data, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.projects.list(accessToken!),
    enabled: !!accessToken,
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => api.projects.create(accessToken!, data),
    onSuccess: (response, variables) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      const hasGithub = variables.links?.some((l: any) => l.link_type === "github");
      if (hasGithub) {
        toast.success("Project added! Enriching from GitHub...", {
          description: "Resume bullets will be generated automatically",
        });
        // Start polling for enrichment status
        setTimeout(() => pollTaskStatus(response.id), 1500);
      } else {
        toast.success("Project added successfully");
      }
      setIsDialogOpen(false);
      resetForm();
    },
    onError: handleApiError,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.projects.delete(accessToken!, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      toast.success("Project deleted");
    },
    onError: handleApiError,
  });

  const enrichMutation = useMutation({
    mutationFn: ({ projectId, githubUrl }: { projectId: string; githubUrl: string }) =>
      api.projects.enrich(accessToken!, projectId, githubUrl),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      toast.success(data.message);
      setIsEnrichDialogOpen(false);
      setEnrichProjectId(null);
      setGithubUrl("");
    },
    onError: handleApiError,
  });

  // Poll for enrichment task status
  const pollTaskStatus = useCallback(async (projectId: string) => {
    console.log("[Progress] Polling task status for project:", projectId);
    if (!accessToken) {
      console.log("[Progress] No access token, skipping poll");
      return;
    }
    try {
      const status = await api.tasks.getByEntity(accessToken, projectId, "enrich_project");
      console.log("[Progress] Got status:", status);
      if (status) {
        setTaskStatuses((prev) => ({ ...prev, [projectId]: status }));
        // If task is still in progress, continue polling
        if (status.status === "pending" || status.status === "processing") {
          console.log("[Progress] Task in progress, polling again in 2s");
          setTimeout(() => pollTaskStatus(projectId), 2000);
        } else if (status.status === "completed") {
          console.log("[Progress] Task completed!");
          // Refresh projects to get new bullets
          queryClient.invalidateQueries({ queryKey: ["projects"] });
          toast.success("GitHub analysis complete!", {
            description: "New bullet points have been added",
          });
        }
      } else {
        console.log("[Progress] No status returned, trying again in 1s");
        setTimeout(() => pollTaskStatus(projectId), 1000);
      }
    } catch (error) {
      console.error("[Progress] Failed to poll task status:", error);
    }
  }, [accessToken, queryClient]);

  // Check for active enrichment tasks when projects load
  useEffect(() => {
    if (!data?.items || !accessToken) return;

    // Check ALL projects for active enrichment tasks
    // (enrichment starts automatically during document processing)
    data.items.forEach((project: any) => {
      api.tasks.getByEntity(accessToken, project.id, "enrich_project").then((status) => {
        if (status && (status.status === "pending" || status.status === "processing")) {
          console.log("[Progress] Found active task for project:", project.id, status);
          setTaskStatuses((prev) => ({ ...prev, [project.id]: status }));
          pollTaskStatus(project.id);
        } else if (status) {
          setTaskStatuses((prev) => ({ ...prev, [project.id]: status }));
        }
      }).catch(() => {});
    });
  }, [data?.items, accessToken, pollTaskStatus]);

  // Start polling when enrichment is triggered
  const handleEnrichWithPolling = () => {
    console.log("[Progress] handleEnrichWithPolling called", { enrichProjectId, githubUrl });
    if (!enrichProjectId || !githubUrl) return;

    // Capture the project ID before mutation resets state
    const projectIdToEnrich = enrichProjectId;
    console.log("[Progress] Starting enrichment for project:", projectIdToEnrich);

    // Set initial pending status immediately for UI feedback
    setTaskStatuses((prev) => {
      console.log("[Progress] Setting initial pending status");
      return {
        ...prev,
        [projectIdToEnrich]: {
          id: `temp-${projectIdToEnrich}`,
          task_type: "enrich_project",
          status: "pending" as const,
          progress: 0,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      };
    });

    enrichMutation.mutate(
      { projectId: projectIdToEnrich, githubUrl },
      {
        onSuccess: () => {
          console.log("[Progress] Mutation succeeded, starting poll in 500ms");
          // Start polling for this project (using captured ID)
          setTimeout(() => pollTaskStatus(projectIdToEnrich), 500);
        },
        onError: (error) => {
          console.error("[Progress] Mutation failed:", error);
        },
      }
    );
  };

  const openEnrichDialog = (projectId: string, existingGithubUrl?: string) => {
    setEnrichProjectId(projectId);
    setGithubUrl(existingGithubUrl || "");
    setIsEnrichDialogOpen(true);
  };

  const handleEnrich = () => {
    handleEnrichWithPolling();
  };

  const resetForm = () => {
    setName("");
    setDescription("");
    setTechnologies("");
    setGithubRepoUrl("");
    setBullets([""]);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const techArray = technologies
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t.length > 0);

    const bulletPoints = bullets
      .filter((b) => b.trim().length >= 10)
      .map((content, index) => ({ content: content.trim(), order_index: index }));

    // Include GitHub link if provided - this will auto-trigger enrichment
    const links = githubRepoUrl.trim()
      ? [{ url: githubRepoUrl.trim(), link_type: "github", title: "GitHub" }]
      : [];

    createMutation.mutate({
      name,
      description: description || null,
      technologies: techArray.length > 0 ? techArray : null,
      bullets: bulletPoints,
      links,
    });
  };

  const addBullet = () => setBullets([...bullets, ""]);

  const updateBullet = (index: number, value: string) => {
    const newBullets = [...bullets];
    newBullets[index] = value;
    setBullets(newBullets);
  };

  const removeBullet = (index: number) => {
    if (bullets.length > 1) {
      setBullets(bullets.filter((_, i) => i !== index));
    }
  };

  const getLinkIcon = (type: string) => {
    if (type === "github") return Github;
    return ExternalLink;
  };

  // Render enrichment status for a project
  const renderEnrichmentStatus = (projectId: string) => {
    const status = taskStatuses[projectId];
    if (!status) return null;

    if (status.status === "pending" || status.status === "processing") {
      return (
        <div className="mt-3 p-3 bg-primary/5 border border-primary/20 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <span className="text-sm font-medium text-primary">
              Analyzing GitHub repository...
            </span>
          </div>
          <Progress value={status.progress} className="h-2" />
          <p className="text-xs text-muted-foreground mt-1">
            {status.progress}% complete
          </p>
        </div>
      );
    }

    if (status.status === "completed") {
      return (
        <div className="mt-3 p-2 bg-success/10 border border-success/20 rounded-lg flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-success" />
          <span className="text-sm text-success">
            GitHub analysis complete
          </span>
        </div>
      );
    }

    if (status.status === "failed") {
      return (
        <div className="mt-3 p-2 bg-destructive/10 border border-destructive/20 rounded-lg">
          <p className="text-sm text-destructive">
            Analysis failed: {status.error_message || "Unknown error"}
          </p>
        </div>
      );
    }

    return null;
  };

  return (
    <div className="space-y-12">
      {/* Actions */}
      <div className="flex justify-end">
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button size="sm" className="btn-primary">
              <Plus className="h-4 w-4 mr-1" />
              Add project
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Add New Project</DialogTitle>
              <DialogDescription>
                Add a project manually. If you have a resume or document with projects,
                upload it in Documents - projects will be extracted automatically.
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name" className="text-sm">Project Name *</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., E-commerce Platform, Portfolio Website"
                  required
                  className="bg-card border-border text-foreground"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description" className="text-sm">Description</Label>
                <Textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Brief description of the project and its purpose"
                  rows={2}
                  className="bg-card border-border text-foreground"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="technologies" className="text-sm">Technologies (comma-separated)</Label>
                <Input
                  id="technologies"
                  value={technologies}
                  onChange={(e) => setTechnologies(e.target.value)}
                  placeholder="e.g., React, Node.js, PostgreSQL, AWS"
                  className="bg-card border-border text-foreground"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="githubRepoUrl" className="text-sm flex items-center gap-2">
                  <Github className="h-4 w-4" />
                  GitHub Repository URL
                </Label>
                <Input
                  id="githubRepoUrl"
                  type="url"
                  value={githubRepoUrl}
                  onChange={(e) => setGithubRepoUrl(e.target.value)}
                  placeholder="https://github.com/username/repository"
                  className="bg-card border-border text-foreground"
                />
                <p className="text-xs text-muted-foreground">
                  If provided, we&apos;ll automatically analyze your repository and generate resume-ready bullet points.
                </p>
              </div>

              <div className="space-y-2">
                <Label className="text-sm">Key Accomplishments / Features</Label>
                <p className="text-xs text-muted-foreground">
                  Add bullet points highlighting what you built or achieved (min 10 characters each)
                </p>
                {bullets.map((bullet, index) => (
                  <div key={index} className="flex gap-2">
                    <Input
                      value={bullet}
                      onChange={(e) => updateBullet(index, e.target.value)}
                      placeholder="e.g., Built a real-time notification system serving 10k+ users"
                      className="bg-card border-border text-foreground"
                    />
                    {bullets.length > 1 && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => removeBullet(index)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                ))}
                <Button type="button" variant="outline" size="sm" onClick={addBullet}>
                  <Plus className="h-4 w-4 mr-1" />
                  Add Bullet
                </Button>
              </div>

              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createMutation.isPending} className="btn-primary">
                  {createMutation.isPending ? "Adding..." : "Add Project"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Projects List */}
      <section>
        {isLoading ? (
          <p className="text-muted-foreground">Loading...</p>
        ) : data?.items.length === 0 ? (
          <div className="simple-card text-center py-12">
            <p className="text-muted-foreground mb-4">No projects yet.</p>
            <Button onClick={() => setIsDialogOpen(true)} size="sm" className="btn-primary">
              <Plus className="h-4 w-4 mr-1" />
              Add your first project
            </Button>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {data?.items.map((project: any) => (
              <div key={project.id} className="simple-card">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="truncate">{project.name}</h3>
                    {project.description && (
                      <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                        {project.description}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-1 ml-2">
                    {project.links?.some((l: any) => l.link_type === "github") && (
                      <button
                        onClick={() => {
                          const githubLink = project.links?.find(
                            (l: any) => l.link_type === "github"
                          );
                          openEnrichDialog(project.id, githubLink?.url);
                        }}
                        className="p-1 text-muted-foreground hover:text-primary transition-colors"
                        title="Re-analyze from GitHub"
                        aria-label={`Re-analyze ${project.name} from GitHub`}
                        disabled={taskStatuses[project.id]?.status === "processing"}
                      >
                        <Sparkles className="h-4 w-4" aria-hidden="true" />
                      </button>
                    )}
                    <button
                      onClick={() => deleteMutation.mutate(project.id)}
                      className="p-1 text-muted-foreground hover:text-destructive transition-colors"
                      aria-label={`Delete ${project.name}`}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </div>
                </div>

                {/* Enrichment Status */}
                {renderEnrichmentStatus(project.id)}

                {project.technologies?.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1">
                    {project.technologies.map((tech: string) => (
                      <span
                        key={tech}
                        className="px-2 py-0.5 bg-primary/10 text-primary text-xs rounded"
                      >
                        {tech}
                      </span>
                    ))}
                  </div>
                )}

                {project.bullets?.length > 0 && (
                  <ul className="mt-3 space-y-1">
                    {project.bullets.map((bullet: any) => (
                      <li key={bullet.id} className="text-sm flex gap-2">
                        <span className="text-muted-foreground">•</span>
                        <span>{bullet.content}</span>
                      </li>
                    ))}
                  </ul>
                )}

                {project.links?.length > 0 && (
                  <div className="flex gap-2 mt-3">
                    {project.links.map((link: any) => {
                      const Icon = getLinkIcon(link.link_type);
                      return (
                        <a
                          key={link.id}
                          href={link.url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Button variant="outline" size="sm">
                            <Icon className="h-3 w-3 mr-1" />
                            {link.title || link.link_type}
                          </Button>
                        </a>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Re-analyze from GitHub Dialog */}
      <Dialog open={isEnrichDialogOpen} onOpenChange={setIsEnrichDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              Re-analyze from GitHub
            </DialogTitle>
            <DialogDescription>
              Re-analyze your GitHub repository to regenerate bullet points.
              New bullets will be added alongside existing ones.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="githubUrl" className="text-sm">GitHub Repository URL</Label>
              <Input
                id="githubUrl"
                type="url"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                placeholder="https://github.com/username/repository"
                className="bg-card border-border text-foreground"
              />
              <p className="text-xs text-muted-foreground">
                We&apos;ll re-analyze the repository&apos;s README, languages, stars,
                and other metrics to generate updated bullet points.
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsEnrichDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleEnrich}
              disabled={enrichMutation.isPending || !githubUrl}
              className="btn-primary"
            >
              {enrichMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Re-analyze
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
