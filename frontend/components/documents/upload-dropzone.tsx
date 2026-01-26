"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, X, Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface UploadFile {
  file: File;
  id: string;
  status: "pending" | "uploading" | "completed" | "error";
  progress: number;
  error?: string;
}

interface UploadDropzoneProps {
  onUpload: (file: File) => Promise<void>;
  isDisabled?: boolean;
}

export function UploadDropzone({ onUpload, isDisabled }: UploadDropzoneProps) {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  const processFiles = async (pendingFiles: UploadFile[]) => {
    setIsProcessing(true);

    for (const uploadFile of pendingFiles) {
      // Mark as uploading
      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadFile.id ? { ...f, status: "uploading" as const, progress: 0 } : f
        )
      );

      try {
        // Simulate progress
        const progressInterval = setInterval(() => {
          setFiles((prev) =>
            prev.map((f) =>
              f.id === uploadFile.id && f.progress < 90
                ? { ...f, progress: f.progress + 10 }
                : f
            )
          );
        }, 100);

        await onUpload(uploadFile.file);

        clearInterval(progressInterval);

        // Mark as completed
        setFiles((prev) =>
          prev.map((f) =>
            f.id === uploadFile.id ? { ...f, status: "completed" as const, progress: 100 } : f
          )
        );

        // Remove after delay
        setTimeout(() => {
          setFiles((prev) => prev.filter((f) => f.id !== uploadFile.id));
        }, 2000);
      } catch (error) {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === uploadFile.id
              ? { ...f, status: "error" as const, error: "Upload failed" }
              : f
          )
        );
      }
    }

    setIsProcessing(false);
  };

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      const newFiles: UploadFile[] = acceptedFiles.map((file) => ({
        file,
        id: `${file.name}-${Date.now()}-${Math.random()}`,
        status: "pending" as const,
        progress: 0,
      }));

      setFiles((prev) => [...prev, ...newFiles]);
      processFiles(newFiles);
    },
    [onUpload]
  );

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const { getRootProps, getInputProps, isDragActive, isDragAccept, isDragReject } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    },
    maxSize: 10 * 1024 * 1024,
    disabled: isDisabled || isProcessing,
  });

  return (
    <div className="space-y-6">
      {/* Dropzone - Editorial Style */}
      <div
        {...getRootProps()}
        className={cn(
          "relative border-2 border-dashed p-10 text-center cursor-pointer transition-all",
          isDragActive && isDragAccept && "border-primary bg-primary/5",
          isDragActive && isDragReject && "border-destructive bg-destructive/5",
          !isDragActive && "border-border hover:border-foreground hover:bg-muted/30",
          (isDisabled || isProcessing) && "opacity-50 cursor-not-allowed"
        )}
      >
        <input {...getInputProps()} />

        {/* Corner marks on hover */}
        <div
          className={cn(
            "absolute -top-1 -left-1 w-3 h-3 border-l-2 border-t-2 transition-opacity",
            isDragActive && isDragAccept ? "border-primary opacity-100" : "border-foreground opacity-0"
          )}
          aria-hidden="true"
        />
        <div
          className={cn(
            "absolute -bottom-1 -right-1 w-3 h-3 border-r-2 border-b-2 transition-opacity",
            isDragActive && isDragAccept ? "border-primary opacity-100" : "border-foreground opacity-0"
          )}
          aria-hidden="true"
        />

        {/* Icon */}
        <div className="relative mx-auto w-16 h-16 mb-6">
          <div
            className={cn(
              "absolute inset-0 border-2 transition-all",
              isDragActive && isDragAccept && "border-primary bg-primary/10",
              isDragActive && isDragReject && "border-destructive bg-destructive/10",
              !isDragActive && "border-border bg-muted/30"
            )}
          />
          <div className="absolute inset-0 flex items-center justify-center">
            {isDragActive ? (
              isDragAccept ? (
                <Upload className="h-6 w-6 text-primary" />
              ) : (
                <X className="h-6 w-6 text-destructive" />
              )
            ) : (
              <FileText className="h-6 w-6 text-muted-foreground" />
            )}
          </div>
        </div>

        {/* Text */}
        {isDragActive ? (
          isDragAccept ? (
            <p className="text-sm text-primary font-medium">
              Drop to upload
            </p>
          ) : (
            <p className="text-sm text-destructive font-medium">
              File type not supported
            </p>
          )
        ) : (
          <>
            <p className="text-sm">
              Drag & drop files here, or{" "}
              <span className="text-primary font-medium">browse</span>
            </p>
            <p className="font-mono text-2xs text-muted-foreground mt-2 uppercase tracking-widest">
              PDF or DOCX, max 10MB
            </p>
          </>
        )}
      </div>

      {/* Upload Queue - Editorial Style */}
      {files.length > 0 && (
        <div className="border border-border bg-card divide-y divide-border">
          {files.map((file, index) => (
            <div
              key={file.id}
              className={cn(
                "flex items-center gap-4 p-4 transition-all",
                file.status === "completed" && "bg-success/5",
                file.status === "error" && "bg-destructive/5",
                file.status === "uploading" && "bg-primary/5",
                file.status === "pending" && "bg-muted/30"
              )}
            >
              {/* Index */}
              <span className="font-mono text-2xs text-muted-foreground w-6">
                {String(index + 1).padStart(2, "0")}
              </span>

              {/* Status Icon */}
              <div
                className={cn(
                  "flex items-center justify-center w-8 h-8 border flex-shrink-0",
                  file.status === "completed" && "border-success text-success",
                  file.status === "uploading" && "border-primary text-primary",
                  file.status === "error" && "border-destructive text-destructive",
                  file.status === "pending" && "border-border text-muted-foreground"
                )}
              >
                {file.status === "completed" ? (
                  <Check className="h-4 w-4" />
                ) : file.status === "uploading" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : file.status === "error" ? (
                  <X className="h-4 w-4" />
                ) : (
                  <FileText className="h-4 w-4" />
                )}
              </div>

              {/* File Info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">
                  {file.file.name}
                </p>
                <div className="flex items-center gap-3 mt-1">
                  <span className="font-mono text-2xs text-muted-foreground">
                    {(file.file.size / 1024).toFixed(1)} KB
                  </span>

                  {file.status === "uploading" && (
                    <>
                      <span className="font-mono text-2xs text-primary">
                        {file.progress}%
                      </span>
                      {/* Progress bar */}
                      <div className="flex-1 h-0.5 bg-border">
                        <div
                          className="h-full bg-primary transition-all duration-200"
                          style={{ width: `${file.progress}%` }}
                        />
                      </div>
                    </>
                  )}

                  {file.status === "completed" && (
                    <span className="font-mono text-2xs uppercase tracking-widest text-success">
                      Uploaded
                    </span>
                  )}

                  {file.status === "error" && (
                    <span className="font-mono text-2xs uppercase tracking-widest text-destructive">
                      {file.error}
                    </span>
                  )}
                </div>
              </div>

              {/* Remove button */}
              {(file.status === "pending" || file.status === "error") && (
                <button
                  onClick={() => removeFile(file.id)}
                  className="flex items-center justify-center w-8 h-8 border border-transparent hover:border-destructive hover:text-destructive transition-all flex-shrink-0"
                  aria-label={`Remove ${file.file.name}`}
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
