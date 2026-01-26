"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { api, handleApiError } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Trash2, Star, StarOff } from "lucide-react";
import type { SkillCreate, SkillCategory, ProficiencyLevel } from "@/lib/types/api";

const categoryLabels: Record<SkillCategory, string> = {
  programming_language: "Programming Languages",
  framework: "Frameworks & Libraries",
  database: "Databases",
  cloud: "Cloud Platforms",
  devops: "DevOps & CI/CD",
  tool: "Tools",
  soft_skill: "Soft Skills",
  methodology: "Methodologies",
  other: "Other",
};

const proficiencyLabels: Record<ProficiencyLevel, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
  expert: "Expert",
};

export default function SkillsPage() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [category, setCategory] = useState<SkillCategory>("other");
  const [proficiency, setProficiency] = useState<ProficiencyLevel | "">("");
  const [yearsOfExperience, setYearsOfExperience] = useState("");
  const [isHighlighted, setIsHighlighted] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["skills-grouped"],
    queryFn: () => api.skills.listGrouped(accessToken!),
    enabled: !!accessToken,
  });

  const createMutation = useMutation({
    mutationFn: (data: SkillCreate) => api.skills.create(accessToken!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["skills-grouped"] });
      toast.success("Skill added successfully");
      setIsDialogOpen(false);
      resetForm();
    },
    onError: handleApiError,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.skills.delete(accessToken!, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["skills-grouped"] });
      toast.success("Skill deleted");
    },
    onError: handleApiError,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { is_highlighted: boolean } }) =>
      api.skills.update(accessToken!, id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["skills-grouped"] });
    },
    onError: handleApiError,
  });

  const resetForm = () => {
    setName("");
    setCategory("other");
    setProficiency("");
    setYearsOfExperience("");
    setIsHighlighted(false);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    createMutation.mutate({
      name,
      category,
      proficiency: proficiency || undefined,
      years_of_experience: yearsOfExperience ? parseInt(yearsOfExperience) : undefined,
      is_highlighted: isHighlighted,
    });
  };

  const toggleHighlight = (skillId: string, currentValue: boolean) => {
    updateMutation.mutate({ id: skillId, data: { is_highlighted: !currentValue } });
  };

  return (
    <div className="space-y-12">
      {/* Actions */}
      <div className="flex justify-end">
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button size="sm" className="btn-primary">
              <Plus className="h-4 w-4 mr-1" />
              Add skill
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Add New Skill</DialogTitle>
              <DialogDescription>
                Add a skill to your profile. You can categorize and rate your proficiency.
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name" className="text-sm">Skill Name *</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Python, AWS, Project Management"
                  required
                  className="bg-card border-border text-foreground"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="category" className="text-sm">Category</Label>
                <Select value={category} onValueChange={(v) => setCategory(v as SkillCategory)}>
                  <SelectTrigger className="bg-card border-border text-foreground">
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(categoryLabels).map(([key, label]) => (
                      <SelectItem key={key} value={key}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="proficiency" className="text-sm">Proficiency Level</Label>
                <Select
                  value={proficiency}
                  onValueChange={(v) => setProficiency(v as ProficiencyLevel)}
                >
                  <SelectTrigger className="bg-card border-border text-foreground">
                    <SelectValue placeholder="Select proficiency" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(proficiencyLabels).map(([key, label]) => (
                      <SelectItem key={key} value={key}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="yearsOfExperience" className="text-sm">Years of Experience</Label>
                <Input
                  id="yearsOfExperience"
                  type="number"
                  min="0"
                  max="50"
                  value={yearsOfExperience}
                  onChange={(e) => setYearsOfExperience(e.target.value)}
                  placeholder="e.g., 5"
                  className="bg-card border-border text-foreground"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="isHighlighted"
                  checked={isHighlighted}
                  onChange={(e) => setIsHighlighted(e.target.checked)}
                  className="rounded"
                />
                <Label htmlFor="isHighlighted" className="text-sm font-normal">
                  Highlight this skill (featured on resume)
                </Label>
              </div>

              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createMutation.isPending} className="btn-primary">
                  {createMutation.isPending ? "Adding..." : "Add Skill"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Skills by Category */}
      <section>
        {isLoading ? (
          <p className="text-muted-foreground">Loading...</p>
        ) : !data || data.length === 0 ? (
          <div className="simple-card text-center py-12">
            <p className="text-muted-foreground mb-4">No skills yet.</p>
            <Button onClick={() => setIsDialogOpen(true)} size="sm" className="btn-primary">
              <Plus className="h-4 w-4 mr-1" />
              Add your first skill
            </Button>
          </div>
        ) : (
          <div className="space-y-6">
            {data.map((group) => (
              <div key={group.category} className="simple-card">
                <h3 className="mb-1">
                  {categoryLabels[group.category as SkillCategory] || group.category}
                </h3>
                <p className="text-xs text-muted-foreground mb-4">{group.skills.length} skill(s)</p>

                <div className="flex flex-wrap gap-2">
                  {group.skills.map((skill) => (
                    <div
                      key={skill.id}
                      className="flex items-center gap-1 px-3 py-1.5 bg-muted text-foreground border border-border rounded-full group hover:border-foreground transition-colors"
                    >
                      {skill.is_highlighted && (
                        <Star className="h-3 w-3 text-warning fill-warning" />
                      )}
                      <span className="text-sm">{skill.name}</span>
                      {skill.proficiency && (
                        <span className="text-xs text-muted-foreground ml-1">
                          ({proficiencyLabels[skill.proficiency as ProficiencyLevel] ||
                            skill.proficiency})
                        </span>
                      )}
                      {skill.years_of_experience && (
                        <span className="text-xs text-muted-foreground">
                          · {skill.years_of_experience}y
                        </span>
                      )}
                      <div className="flex items-center gap-0.5 ml-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => toggleHighlight(skill.id, skill.is_highlighted)}
                          className="p-0.5 hover:bg-muted rounded"
                          title={skill.is_highlighted ? "Remove highlight" : "Highlight skill"}
                        >
                          {skill.is_highlighted ? (
                            <StarOff className="h-3 w-3 text-muted-foreground" />
                          ) : (
                            <Star className="h-3 w-3 text-muted-foreground" />
                          )}
                        </button>
                        <button
                          onClick={() => deleteMutation.mutate(skill.id)}
                          className="p-0.5 hover:bg-destructive/10 rounded"
                          title="Delete skill"
                        >
                          <Trash2 className="h-3 w-3 text-destructive" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
