"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { toast } from "sonner";
import { api, handleApiError } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function ProfilePage() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState({
    full_name: "",
    phone: "",
    location: "",
    linkedin_url: "",
    github_url: "",
    portfolio_url: "",
  });

  const { data: profile, isLoading } = useQuery({
    queryKey: ["profile"],
    queryFn: () => api.profile.get(accessToken!),
    enabled: !!accessToken,
  });

  useEffect(() => {
    if (profile) {
      setFormData({
        full_name: profile.full_name || "",
        phone: profile.phone || "",
        location: profile.location || "",
        linkedin_url: profile.linkedin_url || "",
        github_url: profile.github_url || "",
        portfolio_url: profile.portfolio_url || "",
      });
    }
  }, [profile]);

  const updateMutation = useMutation({
    mutationFn: (data: typeof formData) => api.profile.update(accessToken!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] });
      toast.success("Profile updated successfully");
    },
    onError: handleApiError,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate(formData);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  if (isLoading) {
    return <p className="text-muted-foreground">Loading...</p>;
  }

  return (
    <div className="space-y-12 max-w-2xl">
      {/* Header */}
      <div className="border-b pb-6">
        <h1>Profile</h1>
        <p className="text-muted-foreground mt-2">
          Manage your personal information and contact details.
        </p>
      </div>

      {/* Profile Form */}
      <section>
        <div className="simple-card">
          <h3 className="mb-1">Personal information</h3>
          <p className="text-sm text-muted-foreground mb-6">
            This information will be used in your generated resumes.
          </p>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="full_name" className="text-sm">Full Name</Label>
              <Input
                id="full_name"
                name="full_name"
                value={formData.full_name}
                onChange={handleChange}
                placeholder="John Doe"
                className="bg-secondary border-border"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-sm">Email</Label>
              <Input
                value={profile?.email || ""}
                disabled
                className="bg-muted border-border"
              />
              <p className="text-xs text-muted-foreground">
                Email cannot be changed
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone" className="text-sm">Phone</Label>
              <Input
                id="phone"
                name="phone"
                type="tel"
                value={formData.phone}
                onChange={handleChange}
                placeholder="+1 (555) 123-4567"
                className="bg-secondary border-border"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="location" className="text-sm">Location</Label>
              <Input
                id="location"
                name="location"
                value={formData.location}
                onChange={handleChange}
                placeholder="San Francisco, CA"
                className="bg-secondary border-border"
              />
            </div>

            <div className="border-t border-border pt-6">
              <h3 className="mb-4">Online Presence</h3>

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="linkedin_url" className="text-sm">LinkedIn URL</Label>
                  <Input
                    id="linkedin_url"
                    name="linkedin_url"
                    type="url"
                    value={formData.linkedin_url}
                    onChange={handleChange}
                    placeholder="https://linkedin.com/in/johndoe"
                    className="bg-secondary border-border"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="github_url" className="text-sm">GitHub URL</Label>
                  <Input
                    id="github_url"
                    name="github_url"
                    type="url"
                    value={formData.github_url}
                    onChange={handleChange}
                    placeholder="https://github.com/johndoe"
                    className="bg-secondary border-border"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="portfolio_url" className="text-sm">Portfolio URL</Label>
                  <Input
                    id="portfolio_url"
                    name="portfolio_url"
                    type="url"
                    value={formData.portfolio_url}
                    onChange={handleChange}
                    placeholder="https://johndoe.com"
                    className="bg-secondary border-border"
                  />
                </div>
              </div>
            </div>

            <Button type="submit" disabled={updateMutation.isPending} className="btn-primary">
              {updateMutation.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </form>
        </div>
      </section>
    </div>
  );
}
