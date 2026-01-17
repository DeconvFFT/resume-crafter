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
import { Plus, Trash2, ExternalLink, Star } from "lucide-react";
import type { PublicationCreate, PublicationType } from "@/lib/types/api";

const publicationTypeLabels: Record<PublicationType, string> = {
  journal: "Journal Article",
  conference: "Conference Paper",
  workshop: "Workshop Paper",
  preprint: "Preprint",
  thesis: "Thesis/Dissertation",
  book_chapter: "Book Chapter",
  patent: "Patent",
  other: "Other",
};

export default function PublicationsPage() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Form state
  const [title, setTitle] = useState("");
  const [authors, setAuthors] = useState("");
  const [publicationType, setPublicationType] = useState<PublicationType>("conference");
  const [venue, setVenue] = useState("");
  const [publicationDate, setPublicationDate] = useState("");
  const [doi, setDoi] = useState("");
  const [url, setUrl] = useState("");
  const [abstract, setAbstract] = useState("");
  const [isFirstAuthor, setIsFirstAuthor] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["publications"],
    queryFn: () => api.publications.list(accessToken!),
    enabled: !!accessToken,
  });

  const createMutation = useMutation({
    mutationFn: (data: PublicationCreate) => api.publications.create(accessToken!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["publications"] });
      toast.success("Publication added successfully");
      setIsDialogOpen(false);
      resetForm();
    },
    onError: handleApiError,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.publications.delete(accessToken!, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["publications"] });
      toast.success("Publication deleted");
    },
    onError: handleApiError,
  });

  const resetForm = () => {
    setTitle("");
    setAuthors("");
    setPublicationType("conference");
    setVenue("");
    setPublicationDate("");
    setDoi("");
    setUrl("");
    setAbstract("");
    setIsFirstAuthor(false);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    createMutation.mutate({
      title,
      authors,
      publication_type: publicationType,
      venue: venue || undefined,
      publication_date: publicationDate || undefined,
      doi: doi || undefined,
      url: url || undefined,
      abstract: abstract || undefined,
      is_first_author: isFirstAuthor,
    });
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "";
    try {
      return new Date(dateStr).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-12">
      {/* Header */}
      <div className="border-b pb-6 flex items-center justify-between">
        <div>
          <h1>Publications</h1>
          <p className="text-muted-foreground mt-2">
            Manage your research papers, articles, and other publications.
          </p>
        </div>

        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button size="sm" className="btn-primary">
              <Plus className="h-4 w-4 mr-1" />
              Add publication
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Add New Publication</DialogTitle>
              <DialogDescription>
                Add a research paper, article, or other publication to your profile.
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="title" className="text-sm">Title *</Label>
                <Input
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g., Deep Learning for Natural Language Processing"
                  required
                  className="bg-secondary border-border"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="authors" className="text-sm">Authors *</Label>
                <Input
                  id="authors"
                  value={authors}
                  onChange={(e) => setAuthors(e.target.value)}
                  placeholder="e.g., John Smith, Jane Doe, Bob Wilson"
                  required
                  className="bg-secondary border-border"
                />
                <p className="text-xs text-muted-foreground">
                  Comma-separated list of authors in order of contribution
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="publicationType" className="text-sm">Publication Type</Label>
                  <Select
                    value={publicationType}
                    onValueChange={(v) => setPublicationType(v as PublicationType)}
                  >
                    <SelectTrigger className="bg-secondary border-border">
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(publicationTypeLabels).map(([key, label]) => (
                        <SelectItem key={key} value={key}>
                          {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="publicationDate" className="text-sm">Publication Date</Label>
                  <Input
                    id="publicationDate"
                    type="date"
                    value={publicationDate}
                    onChange={(e) => setPublicationDate(e.target.value)}
                    className="bg-secondary border-border"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="venue" className="text-sm">Venue / Journal / Conference</Label>
                <Input
                  id="venue"
                  value={venue}
                  onChange={(e) => setVenue(e.target.value)}
                  placeholder="e.g., NeurIPS 2024, Nature Machine Intelligence"
                  className="bg-secondary border-border"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="doi" className="text-sm">DOI</Label>
                  <Input
                    id="doi"
                    value={doi}
                    onChange={(e) => setDoi(e.target.value)}
                    placeholder="e.g., 10.1234/example.2024"
                    className="bg-secondary border-border"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="url" className="text-sm">URL</Label>
                  <Input
                    id="url"
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://..."
                    className="bg-secondary border-border"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="abstract" className="text-sm">Abstract</Label>
                <Textarea
                  id="abstract"
                  value={abstract}
                  onChange={(e) => setAbstract(e.target.value)}
                  placeholder="Brief summary of the publication..."
                  rows={3}
                  className="bg-secondary border-border"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="isFirstAuthor"
                  checked={isFirstAuthor}
                  onChange={(e) => setIsFirstAuthor(e.target.checked)}
                  className="rounded"
                />
                <Label htmlFor="isFirstAuthor" className="text-sm font-normal">
                  I am the first author / primary contributor
                </Label>
              </div>

              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createMutation.isPending} className="btn-primary">
                  {createMutation.isPending ? "Adding..." : "Add Publication"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Publications List */}
      <section>
        {isLoading ? (
          <p className="text-muted-foreground">Loading...</p>
        ) : data?.items.length === 0 ? (
          <div className="simple-card text-center py-12">
            <p className="text-muted-foreground mb-4">No publications yet.</p>
            <Button onClick={() => setIsDialogOpen(true)} size="sm" className="btn-primary">
              <Plus className="h-4 w-4 mr-1" />
              Add your first publication
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {data?.items.map((pub) => (
              <div key={pub.id} className="simple-card">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs px-2 py-0.5 bg-primary/10 text-primary rounded">
                        {publicationTypeLabels[pub.publication_type as PublicationType] ||
                          pub.publication_type}
                      </span>
                      {pub.is_first_author && (
                        <span className="text-xs px-2 py-0.5 bg-secondary rounded flex items-center gap-1">
                          <Star className="h-3 w-3" />
                          First Author
                        </span>
                      )}
                    </div>
                    <h3 className="leading-tight">{pub.title}</h3>
                    <p className="text-sm text-muted-foreground mt-1">{pub.authors}</p>

                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground mt-2">
                      {pub.venue && <span>{pub.venue}</span>}
                      {pub.publication_date && <span>{formatDate(pub.publication_date)}</span>}
                      {pub.citation_count !== null && pub.citation_count > 0 && (
                        <span>{pub.citation_count} citations</span>
                      )}
                    </div>

                    {pub.abstract && (
                      <p className="mt-2 text-sm text-muted-foreground line-clamp-2">
                        {pub.abstract}
                      </p>
                    )}

                    <div className="flex gap-2 mt-3">
                      {pub.url && (
                        <a href={pub.url} target="_blank" rel="noopener noreferrer">
                          <Button variant="outline" size="sm">
                            <ExternalLink className="h-3 w-3 mr-1" />
                            View
                          </Button>
                        </a>
                      )}
                      {pub.doi && (
                        <a
                          href={`https://doi.org/${pub.doi}`}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Button variant="outline" size="sm">
                            DOI
                          </Button>
                        </a>
                      )}
                      {pub.arxiv_id && (
                        <a
                          href={`https://arxiv.org/abs/${pub.arxiv_id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Button variant="outline" size="sm">
                            arXiv
                          </Button>
                        </a>
                      )}
                    </div>
                  </div>

                  <button
                    onClick={() => deleteMutation.mutate(pub.id)}
                    className="text-muted-foreground hover:text-red-500 transition-colors ml-4"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
