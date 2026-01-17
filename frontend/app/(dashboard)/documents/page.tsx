"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import { toast } from "sonner";
import { api, handleApiError } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth";
import { useDocumentStream } from "@/hooks/useDocumentStream";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Upload,
  Trash2,
  CheckCircle,
  Clock,
  AlertCircle,
  Link as LinkIcon,
  Loader2,
  ChevronDown,
  FileText,
  ArrowRight,
  Brain,
  Sparkles,
  Wifi,
  WifiOff,
} from "lucide-react";
import { cn } from "@/lib/utils";

const statusConfig = {
  pending: { icon: Clock, label: "Queued", color: "text-warning" },
  processing: { icon: Loader2, label: "Processing", color: "text-info" },
  completed: { icon: CheckCircle, label: "Complete", color: "text-success" },
  failed: { icon: AlertCircle, label: "Failed", color: "text-destructive" },
};

// Component for displaying real-time processing stream
function ProcessingStream({
  documentId,
  accessToken,
  onComplete,
}: {
  documentId: string;
  accessToken: string | null;
  onComplete: () => void;
}) {
  const {
    logs,
    thinking,
    isThinking,
    progress,
    extractionCounts,
    connectionState,
    isConnected,
  } = useDocumentStream({
    documentId,
    accessToken,
    enabled: true,
    onComplete: () => {
      onComplete();
      toast.success("Document processing completed");
    },
    onError: (message) => {
      toast.error(`Processing failed: ${message}`);
    },
  });

  return (
    <div className="mt-4 space-y-4">
      {/* SSE Connection Status */}
      <div className="flex items-center gap-2">
        {isConnected ? (
          <>
            <Wifi className="h-3 w-3 text-success" aria-hidden="true" />
            <span className="font-mono text-2xs uppercase tracking-widest text-success">
              Live streaming
            </span>
          </>
        ) : connectionState === "connecting" ? (
          <>
            <Loader2 className="h-3 w-3 text-warning animate-spin" aria-hidden="true" />
            <span className="font-mono text-2xs uppercase tracking-widest text-warning">
              Connecting...
            </span>
          </>
        ) : (
          <>
            <WifiOff className="h-3 w-3 text-muted-foreground" aria-hidden="true" />
            <span className="font-mono text-2xs uppercase tracking-widest text-muted-foreground">
              Polling mode
            </span>
          </>
        )}
      </div>

      {/* Progress bar */}
      {progress && (
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <span className="font-mono text-2xs uppercase tracking-widest text-muted-foreground">
              Progress
            </span>
            <span className="font-mono text-2xs text-muted-foreground">
              {progress.current}/{progress.total} ({progress.percentage}%)
            </span>
          </div>
          <div className="h-1 w-full bg-border overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-300"
              style={{ width: `${progress.percentage}%` }}
            />
          </div>
        </div>
      )}

      {/* AI Thinking Display */}
      {(isThinking || thinking) && (
        <div className="border border-border bg-muted/30 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Brain className={cn("h-4 w-4 text-primary", isThinking && "animate-pulse")} aria-hidden="true" />
            <span className="font-mono text-xs uppercase tracking-widest text-primary">
              {isThinking ? "AI Reasoning..." : "AI Reasoning Complete"}
            </span>
            {isThinking && <Sparkles className="h-3 w-3 text-primary animate-pulse" aria-hidden="true" />}
          </div>
          <div className="pl-6 border-l-2 border-primary/30">
            <p className="font-body text-xs text-charcoal whitespace-pre-wrap max-h-40 overflow-y-auto">
              {thinking || "Processing..."}
            </p>
          </div>
        </div>
      )}

      {/* Real-time logs */}
      {logs.length > 0 && (
        <div className="pl-4 border-l-2 border-border space-y-2">
          {logs.map((log, idx) => (
            <div key={idx} className="flex items-start gap-3">
              <span className="font-mono text-2xs text-muted-foreground w-4 flex-shrink-0">
                {String(idx + 1).padStart(2, "0")}
              </span>
              <span
                className={cn(
                  "font-body text-xs",
                  log.status === "completed" && "text-success",
                  log.status === "failed" && "text-destructive",
                  log.status === "started" && "text-info",
                  log.status === "skipped" && "text-muted-foreground"
                )}
              >
                {log.message}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Extraction counts */}
      {Object.keys(extractionCounts).length > 0 && (
        <div className="flex flex-wrap gap-3">
          {extractionCounts.experiences !== undefined && (
            <span className="px-2 py-1 border border-border font-mono text-2xs uppercase tracking-widest">
              Experiences: {extractionCounts.experiences}
            </span>
          )}
          {extractionCounts.projects !== undefined && (
            <span className="px-2 py-1 border border-border font-mono text-2xs uppercase tracking-widest">
              Projects: {extractionCounts.projects}
            </span>
          )}
          {extractionCounts.skills !== undefined && (
            <span className="px-2 py-1 border border-border font-mono text-2xs uppercase tracking-widest">
              Skills: {extractionCounts.skills}
            </span>
          )}
          {extractionCounts.publications !== undefined && (
            <span className="px-2 py-1 border border-border font-mono text-2xs uppercase tracking-widest">
              Publications: {extractionCounts.publications}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export default function DocumentsPage() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [isUploading, setIsUploading] = useState(false);
  const [googleDocUrl, setGoogleDocUrl] = useState("");
  const [activeStreamDocId, setActiveStreamDocId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.documents.list(accessToken!),
    enabled: !!accessToken,
    refetchInterval: (query) => {
      const docs = query.state.data?.items || [];
      const hasProcessing = docs.some(
        (doc: any) => doc.processing_status === "pending" || doc.processing_status === "processing"
      );
      return hasProcessing ? 5000 : false;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.documents.upload(accessToken!, file),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast.success("Document uploaded");
      // Start streaming for the newly uploaded document
      if (response?.id) {
        setActiveStreamDocId(response.id);
      }
    },
    onError: handleApiError,
  });

  // Auto-detect processing documents and start streaming
  useEffect(() => {
    const docs = data?.items || [];
    const processingDoc = docs.find(
      (doc: any) => doc.processing_status === "processing" || doc.processing_status === "pending"
    );
    if (processingDoc && !activeStreamDocId) {
      setActiveStreamDocId(processingDoc.id);
    }
    // Clear stream if no documents are processing
    if (!processingDoc && activeStreamDocId) {
      const activeDoc = docs.find((doc: any) => doc.id === activeStreamDocId);
      if (activeDoc && (activeDoc.processing_status === "completed" || activeDoc.processing_status === "failed")) {
        // Keep streaming for a bit after completion for final updates
        setTimeout(() => setActiveStreamDocId(null), 2000);
      }
    }
  }, [data?.items, activeStreamDocId]);

  const importGoogleDocMutation = useMutation({
    mutationFn: (googleDocId: string) => api.documents.importGoogleDoc(accessToken!, googleDocId),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast.success("Google Doc imported");
      setGoogleDocUrl("");
      // Start streaming for the newly imported document
      if (response?.id) {
        setActiveStreamDocId(response.id);
      }
    },
    onError: handleApiError,
  });

  const handleStreamComplete = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["documents"] });
    // Also invalidate related queries
    queryClient.invalidateQueries({ queryKey: ["experiences"] });
    queryClient.invalidateQueries({ queryKey: ["projects"] });
    queryClient.invalidateQueries({ queryKey: ["skills"] });
    queryClient.invalidateQueries({ queryKey: ["publications"] });
  }, [queryClient]);

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.documents.delete(accessToken!, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast.success("Document deleted");
    },
    onError: handleApiError,
  });

  const handleGoogleDocImport = () => {
    const urlMatch = googleDocUrl.match(/\/document\/d\/([a-zA-Z0-9_-]+)/);
    const docId = urlMatch ? urlMatch[1] : googleDocUrl;
    if (docId) {
      importGoogleDocMutation.mutate(docId);
    } else {
      toast.error("Please enter a valid Google Docs URL");
    }
  };

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      setIsUploading(true);
      for (const file of acceptedFiles) {
        await uploadMutation.mutateAsync(file);
      }
      setIsUploading(false);
    },
    [uploadMutation]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    },
    maxSize: 10 * 1024 * 1024,
  });

  const getDocumentClassLabel = (docClass: string | null) => {
    if (!docClass) return null;
    const labels: Record<string, string> = {
      RESUME: "Resume/CV",
      resume: "Resume/CV",
      EXPERIENCE: "Experience",
      experience: "Experience",
      PROJECT: "Project",
      project: "Project",
      SUPPORTING: "Supporting",
      supporting: "Supporting",
    };
    return labels[docClass] || docClass;
  };

  const documents = data?.items || [];

  return (
    <div className="space-y-12">
      {/* Upload Section - Editorial style */}
      <section className="grid gap-8 lg:grid-cols-2">
        {/* File Upload Dropzone */}
        <div className="border border-border bg-card p-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
                Method 01
              </span>
              <h3 className="font-display text-lg font-medium mt-1">
                File Upload
              </h3>
            </div>
            <Upload className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
          </div>

          <div
            {...getRootProps()}
            className={cn(
              "relative border-2 border-dashed p-10 text-center cursor-pointer transition-all",
              isDragActive
                ? "border-primary bg-primary/5"
                : "border-border hover:border-foreground hover:bg-muted/30",
              isUploading && "opacity-50 pointer-events-none"
            )}
          >
            <input {...getInputProps()} />

            {/* Corner marks */}
            <div className="absolute -top-1 -left-1 w-3 h-3 border-l-2 border-t-2 border-primary opacity-0 transition-opacity group-hover:opacity-100" aria-hidden="true" />
            <div className="absolute -bottom-1 -right-1 w-3 h-3 border-r-2 border-b-2 border-primary opacity-0 transition-opacity group-hover:opacity-100" aria-hidden="true" />

            {isDragActive ? (
              <>
                <FileText className="h-8 w-8 mx-auto mb-4 text-primary" aria-hidden="true" />
                <p className="font-body text-sm text-primary font-medium">
                  Drop to upload
                </p>
              </>
            ) : isUploading ? (
              <>
                <Loader2 className="h-8 w-8 mx-auto mb-4 text-muted-foreground animate-spin" aria-hidden="true" />
                <p className="font-body text-sm text-muted-foreground">
                  Uploading...
                </p>
              </>
            ) : (
              <>
                <FileText className="h-8 w-8 mx-auto mb-4 text-muted-foreground" aria-hidden="true" />
                <p className="font-body text-sm">
                  Drag & drop or{" "}
                  <span className="text-primary font-medium">browse</span>
                </p>
                <p className="font-mono text-2xs text-muted-foreground mt-2 uppercase tracking-wider">
                  PDF or DOCX, max 10MB
                </p>
              </>
            )}
          </div>
        </div>

        {/* Google Docs Import */}
        <div className="border border-border bg-card p-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
                Method 02
              </span>
              <h3 className="font-display text-lg font-medium mt-1">
                Google Docs
              </h3>
            </div>
            <LinkIcon className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
          </div>

          <div className="space-y-6">
            <div className="space-y-3">
              <Label htmlFor="googleDocUrl">Document URL</Label>
              <Input
                id="googleDocUrl"
                type="url"
                placeholder="https://docs.google.com/document/d/..."
                value={googleDocUrl}
                onChange={(e) => setGoogleDocUrl(e.target.value)}
              />
            </div>

            <Button
              onClick={handleGoogleDocImport}
              disabled={!googleDocUrl || importGoogleDocMutation.isPending}
              className="w-full group"
            >
              {importGoogleDocMutation.isPending ? (
                "Importing..."
              ) : (
                <>
                  Import document
                  <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" aria-hidden="true" />
                </>
              )}
            </Button>

            <p className="font-body text-xs text-muted-foreground italic">
              Document must be shared with &quot;Anyone with the link&quot;
            </p>
          </div>
        </div>
      </section>

      {/* Documents List - Magazine Index Style */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="font-display text-xl font-medium">Your Documents</h2>
            <div className="h-1 w-10 bg-foreground mt-3" aria-hidden="true" />
          </div>
          <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
            {documents.length} item{documents.length !== 1 ? "s" : ""}
          </span>
        </div>

        {isLoading ? (
          <div className="border border-border bg-card p-12 text-center">
            <Loader2 className="h-6 w-6 mx-auto mb-4 text-muted-foreground animate-spin" aria-hidden="true" />
            <p className="font-body text-sm text-muted-foreground italic">
              Loading documents...
            </p>
          </div>
        ) : documents.length === 0 ? (
          <div className="border border-border bg-card p-12 text-center">
            <FileText className="h-8 w-8 mx-auto mb-4 text-muted-foreground" aria-hidden="true" />
            <p className="font-display text-lg font-medium">No documents yet</p>
            <p className="font-body text-sm text-muted-foreground mt-2 italic">
              Upload your first document above to get started.
            </p>
          </div>
        ) : (
          <div className="border border-border bg-card divide-y divide-border" role="list">
            {documents.map((doc: any, index: number) => {
              const status = statusConfig[doc.processing_status as keyof typeof statusConfig] || statusConfig.pending;
              const StatusIcon = status.icon;
              const isProcessing = doc.processing_status === "processing" || doc.processing_status === "pending";

              return (
                <div
                  key={doc.id}
                  className="flex items-start gap-6 p-6 hover:bg-muted/30 transition-colors group"
                  role="listitem"
                >
                  {/* Index number */}
                  <span className="font-mono text-sm text-muted-foreground w-8 pt-1 flex-shrink-0">
                    {String(index + 1).padStart(2, "0")}
                  </span>

                  {/* Document info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-body text-base font-medium truncate group-hover:text-primary transition-colors">
                          {doc.filename}
                        </h3>

                        {/* Classification */}
                        {doc.document_class && (
                          <div className="mt-2 flex items-center gap-3">
                            <span className="font-mono text-2xs uppercase tracking-widest text-muted-foreground">
                              Classification
                            </span>
                            <span className="font-body text-sm text-primary font-medium">
                              {getDocumentClassLabel(doc.document_class)}
                            </span>
                            {doc.classification_confidence && (
                              <span className="font-mono text-2xs text-muted-foreground">
                                ({Math.round(doc.classification_confidence * 100)}%)
                              </span>
                            )}
                          </div>
                        )}

                        {doc.classification_reasoning && (
                          <p className="mt-2 font-body text-xs text-muted-foreground italic line-clamp-2">
                            {doc.classification_reasoning}
                          </p>
                        )}

                        {/* Live Processing Stream (for actively processing documents) */}
                        {isProcessing && activeStreamDocId === doc.id && (
                          <ProcessingStream
                            documentId={doc.id}
                            accessToken={accessToken}
                            onComplete={handleStreamComplete}
                          />
                        )}

                        {/* Static Processing Logs (for completed/failed documents) */}
                        {!isProcessing && doc.processing_logs && doc.processing_logs.length > 0 && (
                          <Collapsible defaultOpen={false} className="mt-4">
                            <CollapsibleTrigger className="flex items-center gap-2 font-mono text-2xs uppercase tracking-widest text-muted-foreground hover:text-foreground transition-colors group/trigger">
                              <span>Processing log</span>
                              <span className="px-1.5 py-0.5 border border-border text-2xs">
                                {doc.processing_logs.length}
                              </span>
                              <ChevronDown className="h-3 w-3 group-hover/trigger:rotate-180 transition-transform" aria-hidden="true" />
                            </CollapsibleTrigger>
                            <CollapsibleContent className="mt-3">
                              <div className="pl-4 border-l-2 border-border space-y-2">
                                {doc.processing_logs.map((log: any, idx: number) => (
                                  <div key={idx} className="flex items-start gap-3">
                                    <span className="font-mono text-2xs text-muted-foreground w-4 flex-shrink-0">
                                      {String(idx + 1).padStart(2, "0")}
                                    </span>
                                    <span
                                      className={cn(
                                        "font-body text-xs",
                                        log.status === "completed" && "text-success",
                                        log.status === "failed" && "text-destructive",
                                        log.status === "processing" && "text-info",
                                        log.status === "pending" && "text-muted-foreground"
                                      )}
                                    >
                                      {log.message}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </CollapsibleContent>
                          </Collapsible>
                        )}

                        {doc.processing_status === "failed" && doc.processing_error && (
                          <div className="mt-3 p-3 border-2 border-destructive bg-destructive/5">
                            <p className="font-body text-xs text-destructive">
                              {doc.processing_error.slice(0, 150)}...
                            </p>
                          </div>
                        )}
                      </div>

                      {/* Status badge */}
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span
                          className={cn(
                            "flex items-center gap-2 px-3 py-1.5 border font-mono text-2xs uppercase tracking-widest",
                            status.color,
                            doc.processing_status === "completed" && "border-success/30 bg-success/5",
                            doc.processing_status === "processing" && "border-info/30 bg-info/5",
                            doc.processing_status === "pending" && "border-warning/30 bg-warning/5",
                            doc.processing_status === "failed" && "border-destructive/30 bg-destructive/5"
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
                  </div>

                  {/* Delete button */}
                  <button
                    onClick={() => deleteMutation.mutate(doc.id)}
                    className="flex items-center justify-center w-10 h-10 border border-transparent hover:border-destructive hover:text-destructive transition-all flex-shrink-0"
                    aria-label={`Delete ${doc.filename}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
