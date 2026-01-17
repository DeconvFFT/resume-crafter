"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { api, handleApiError } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Plus, Trash2, Briefcase, ArrowRight, Calendar, MapPin } from "lucide-react";
import { cn } from "@/lib/utils";

export default function ExperiencesPage() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Form state
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [location, setLocation] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isCurrent, setIsCurrent] = useState(false);
  const [bullets, setBullets] = useState<string[]>([""]);

  const { data, isLoading } = useQuery({
    queryKey: ["experiences"],
    queryFn: () => api.experiences.list(accessToken!),
    enabled: !!accessToken,
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => api.experiences.create(accessToken!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["experiences"] });
      toast.success("Experience added successfully");
      setIsDialogOpen(false);
      resetForm();
    },
    onError: handleApiError,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.experiences.delete(accessToken!, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["experiences"] });
      toast.success("Experience deleted");
    },
    onError: handleApiError,
  });

  const resetForm = () => {
    setCompany("");
    setRole("");
    setLocation("");
    setStartDate("");
    setEndDate("");
    setIsCurrent(false);
    setBullets([""]);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const bulletPoints = bullets
      .filter((b) => b.trim().length >= 10)
      .map((content, index) => ({ content: content.trim(), order_index: index }));

    createMutation.mutate({
      company,
      role,
      location: location || null,
      start_date: startDate,
      end_date: isCurrent ? null : endDate || null,
      is_current: isCurrent,
      bullets: bulletPoints,
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

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "Present";
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", { month: "short", year: "numeric" });
  };

  const experiences = data?.items || [];

  return (
    <div className="space-y-12">
      {/* Add Experience Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        {/* FAB - only show when there are existing experiences */}
        {experiences.length > 0 && (
          <DialogTrigger asChild>
            <Button className="fixed bottom-8 right-8 shadow-elevated group z-50">
              <Plus className="h-4 w-4 mr-2" aria-hidden="true" />
              Add experience
              <ArrowRight className="ml-2 h-4 w-4 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" aria-hidden="true" />
            </Button>
          </DialogTrigger>
        )}
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Add Work Experience</DialogTitle>
            <DialogDescription>
              Add a job or position you&apos;ve held. Include key accomplishments as bullet points.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-6 mt-4">
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-3">
                <Label htmlFor="company">Company *</Label>
                <Input
                  id="company"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  placeholder="e.g., Google, Microsoft"
                  required
                />
              </div>

              <div className="space-y-3">
                <Label htmlFor="role">Role / Title *</Label>
                <Input
                  id="role"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  placeholder="e.g., Software Engineer"
                  required
                />
              </div>
            </div>

            <div className="space-y-3">
              <Label htmlFor="location">Location</Label>
              <Input
                id="location"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g., San Francisco, CA or Remote"
              />
            </div>

            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-3">
                <Label htmlFor="startDate">Start Date *</Label>
                <Input
                  id="startDate"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-3">
                <Label htmlFor="endDate">End Date</Label>
                <Input
                  id="endDate"
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  disabled={isCurrent}
                />
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <Checkbox
                id="isCurrent"
                checked={isCurrent}
                onCheckedChange={(checked) => {
                  setIsCurrent(checked === true);
                  if (checked) setEndDate("");
                }}
              />
              <Label htmlFor="isCurrent" className="text-sm font-normal cursor-pointer">
                I currently work here
              </Label>
            </div>

            <div className="space-y-4">
              <div>
                <Label>Key Accomplishments</Label>
                <p className="font-body text-xs text-muted-foreground italic mt-1">
                  Add bullet points highlighting what you achieved (min 10 characters each)
                </p>
              </div>
              <div className="space-y-3">
                {bullets.map((bullet, index) => (
                  <div key={index} className="flex gap-3">
                    <span className="font-mono text-xs text-muted-foreground pt-3 w-6">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <Input
                      value={bullet}
                      onChange={(e) => updateBullet(index, e.target.value)}
                      placeholder="e.g., Led a team of 5 engineers to deliver a new product feature"
                      className="flex-1"
                    />
                    {bullets.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeBullet(index)}
                        className="flex items-center justify-center w-10 h-10 border border-transparent hover:border-destructive hover:text-destructive transition-all"
                        aria-label="Remove bullet"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
              <Button type="button" variant="outline" size="sm" onClick={addBullet}>
                <Plus className="h-4 w-4 mr-2" aria-hidden="true" />
                Add bullet
              </Button>
            </div>

            <DialogFooter className="pt-6 border-t border-border">
              <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending} className="group">
                {createMutation.isPending ? (
                  "Adding..."
                ) : (
                  <>
                    Add experience
                    <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" aria-hidden="true" />
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Experience List - Editorial Card Style */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="font-display text-xl font-medium">Work History</h2>
            <div className="h-1 w-10 bg-foreground mt-3" aria-hidden="true" />
          </div>
          <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
            {experiences.length} position{experiences.length !== 1 ? "s" : ""}
          </span>
        </div>

        {isLoading ? (
          <div className="border border-border bg-card p-12 text-center">
            <p className="font-body text-sm text-muted-foreground italic">
              Loading experiences...
            </p>
          </div>
        ) : experiences.length === 0 ? (
          <div className="border border-border bg-card p-12 text-center">
            <Briefcase className="h-8 w-8 mx-auto mb-4 text-muted-foreground" aria-hidden="true" />
            <p className="font-display text-lg font-medium">No experience added yet</p>
            <p className="font-body text-sm text-muted-foreground mt-2 italic">
              Add your work history to include in tailored resumes.
            </p>
            <Button onClick={() => setIsDialogOpen(true)} className="mt-6 group">
              <Plus className="h-4 w-4 mr-2" aria-hidden="true" />
              Add your first experience
              <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" aria-hidden="true" />
            </Button>
          </div>
        ) : (
          <div className="space-y-6">
            {experiences.map((exp: any, index: number) => (
              <div
                key={exp.id}
                className="border border-border bg-card hover:border-foreground transition-colors group"
              >
                {/* Header */}
                <div className="p-6 pb-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      {/* Index and Role */}
                      <div className="flex items-start gap-4">
                        <span className="font-mono text-sm text-muted-foreground pt-1">
                          {String(index + 1).padStart(2, "0")}
                        </span>
                        <div className="flex-1 min-w-0">
                          <h3 className="font-display text-xl font-medium truncate group-hover:text-primary transition-colors">
                            {exp.role}
                          </h3>
                          <p className="font-body text-base text-charcoal mt-1">
                            {exp.company}
                          </p>

                          {/* Meta info */}
                          <div className="flex items-center gap-4 mt-3">
                            <span className="flex items-center gap-1.5 font-mono text-2xs uppercase tracking-widest text-muted-foreground">
                              <Calendar className="h-3 w-3" aria-hidden="true" />
                              {formatDate(exp.start_date)} – {formatDate(exp.end_date)}
                            </span>
                            {exp.location && (
                              <span className="flex items-center gap-1.5 font-mono text-2xs uppercase tracking-widest text-muted-foreground">
                                <MapPin className="h-3 w-3" aria-hidden="true" />
                                {exp.location}
                              </span>
                            )}
                            {exp.is_current && (
                              <span className="px-2 py-0.5 bg-success/10 text-success font-mono text-2xs uppercase tracking-widest">
                                Current
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Delete button */}
                    <button
                      onClick={() => deleteMutation.mutate(exp.id)}
                      className="flex items-center justify-center w-10 h-10 border border-transparent hover:border-destructive hover:text-destructive transition-all flex-shrink-0"
                      aria-label={`Delete ${exp.role} at ${exp.company}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {/* Bullets */}
                {exp.bullets?.length > 0 && (
                  <div className="px-6 pb-6 pt-2">
                    <div className="pl-10 border-l-2 border-border space-y-2">
                      {exp.bullets.map((bullet: any, idx: number) => (
                        <div key={bullet.id} className="flex items-start gap-3">
                          <span className="font-mono text-2xs text-muted-foreground pt-0.5 w-4 flex-shrink-0">
                            {String(idx + 1).padStart(2, "0")}
                          </span>
                          <p className="font-body text-sm text-charcoal">
                            {bullet.content}
                          </p>
                        </div>
                      ))}
                    </div>

                    {/* Skills tags */}
                    {exp.bullets?.[0]?.skills?.length > 0 && (
                      <div className="mt-4 pl-10 flex flex-wrap gap-2">
                        {exp.bullets
                          .flatMap((b: any) => b.skills || [])
                          .filter(
                            (skill: string, i: number, arr: string[]) =>
                              arr.indexOf(skill) === i
                          )
                          .slice(0, 8)
                          .map((skill: string) => (
                            <span
                              key={skill}
                              className="px-2 py-1 border border-border font-mono text-2xs uppercase tracking-widest text-muted-foreground hover:border-foreground hover:text-foreground transition-colors"
                            >
                              {skill}
                            </span>
                          ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
