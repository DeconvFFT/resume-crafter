"use client";

import * as React from "react";
import { useState, useEffect, useCallback } from "react";
import {
  X,
  Trash2,
  ChevronDown,
  Info,
  AlertCircle,
  LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { type NodeCategory, type NodeType } from "./node-panel";

// Executive Noir color configuration
const categoryColors: Record<NodeCategory, {
  bg: string;
  text: string;
  glow: string;
  border: string;
}> = {
  trigger: {
    bg: "rgba(245, 158, 11, 0.12)",
    text: "#F59E0B",
    glow: "rgba(245, 158, 11, 0.3)",
    border: "rgba(245, 158, 11, 0.3)",
  },
  action: {
    bg: "rgba(20, 184, 166, 0.12)",
    text: "#14B8A6",
    glow: "rgba(20, 184, 166, 0.3)",
    border: "rgba(20, 184, 166, 0.3)",
  },
  logic: {
    bg: "rgba(20, 184, 166, 0.12)",
    text: "#14B8A6",
    glow: "rgba(20, 184, 166, 0.3)",
    border: "rgba(20, 184, 166, 0.3)",
  },
  output: {
    bg: "rgba(34, 197, 94, 0.12)",
    text: "#22C55E",
    glow: "rgba(34, 197, 94, 0.3)",
    border: "rgba(34, 197, 94, 0.3)",
  },
};

// Node configuration data structure
export interface NodeConfig {
  id: string;
  nodeTypeId: string;
  title: string;
  description: string;
  category: NodeCategory;
  icon: LucideIcon;
  // Type-specific configuration
  triggerConfig?: TriggerConfig;
  actionConfig?: ActionConfig;
  conditionConfig?: ConditionConfig;
  outputConfig?: OutputConfig;
}

// Trigger-specific configuration
export interface TriggerConfig {
  eventType: "job_posting" | "schedule" | "manual" | "webhook";
  schedule?: {
    cron: string;
    timezone: string;
  };
  webhookUrl?: string;
  filters?: {
    keywords?: string[];
    location?: string;
    salaryMin?: number;
  };
}

// Action-specific configuration
export interface ActionConfig {
  actionType: string;
  parameters: Record<string, unknown>;
  credentials?: {
    credentialId: string;
    credentialType: string;
  };
  timeout?: number;
  retryOnFailure?: boolean;
  maxRetries?: number;
}

// Condition-specific configuration
export interface ConditionConfig {
  field: string;
  operator: "equals" | "not_equals" | "contains" | "greater_than" | "less_than" | "is_empty" | "is_not_empty";
  value: string;
  caseSensitive?: boolean;
}

// Output-specific configuration
export interface OutputConfig {
  destination: "apply" | "draft" | "email" | "webhook" | "file";
  format: "pdf" | "docx" | "json" | "html";
  filename?: string;
  emailRecipient?: string;
  webhookUrl?: string;
}

// Form validation errors
interface ValidationErrors {
  title?: string;
  description?: string;
  cron?: string;
  field?: string;
  value?: string;
  emailRecipient?: string;
  webhookUrl?: string;
}

// NodeConfigPanel props
export interface NodeConfigPanelProps {
  node: NodeConfig | null;
  isOpen: boolean;
  onClose: () => void;
  onUpdate: (node: NodeConfig) => void;
  onDelete: (nodeId: string) => void;
  className?: string;
}

// Field wrapper component with Executive Noir styling
interface FormFieldProps {
  label: string;
  htmlFor: string;
  error?: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
}

function FormField({ label, htmlFor, error, hint, required, children }: FormFieldProps) {
  return (
    <div className="space-y-2">
      <Label htmlFor={htmlFor} className="flex items-center gap-1 text-white/70 text-xs font-medium">
        {label}
        {required && <span className="text-amber-400">*</span>}
      </Label>
      {children}
      {hint && !error && (
        <p className="text-[10px] text-white/40 flex items-center gap-1">
          <Info className="h-3 w-3" />
          {hint}
        </p>
      )}
      {error && (
        <p className="text-[10px] text-red-400 flex items-center gap-1">
          <AlertCircle className="h-3 w-3" />
          {error}
        </p>
      )}
    </div>
  );
}

// Trigger configuration form
interface TriggerFormProps {
  config: TriggerConfig;
  onChange: (config: TriggerConfig) => void;
  errors: ValidationErrors;
}

function TriggerForm({ config, onChange, errors }: TriggerFormProps) {
  return (
    <div className="space-y-4">
      <FormField label="Event Type" htmlFor="eventType" required>
        <Select
          value={config.eventType}
          onValueChange={(value) =>
            onChange({ ...config, eventType: value as TriggerConfig["eventType"] })
          }
        >
          <SelectTrigger id="eventType" className="bg-white/5 border-white/10 text-white">
            <SelectValue placeholder="Select event type" />
          </SelectTrigger>
          <SelectContent className="bg-[#14141f] border-white/10">
            <SelectItem value="job_posting">New Job Posting</SelectItem>
            <SelectItem value="schedule">Scheduled Time</SelectItem>
            <SelectItem value="manual">Manual Trigger</SelectItem>
            <SelectItem value="webhook">Webhook</SelectItem>
          </SelectContent>
        </Select>
      </FormField>

      {config.eventType === "schedule" && (
        <>
          <FormField
            label="Cron Expression"
            htmlFor="cron"
            hint="e.g., '0 9 * * *' for daily at 9 AM"
            error={errors.cron}
            required
          >
            <Input
              id="cron"
              value={config.schedule?.cron || ""}
              onChange={(e) =>
                onChange({
                  ...config,
                  schedule: { ...config.schedule, cron: e.target.value, timezone: config.schedule?.timezone || "UTC" },
                })
              }
              placeholder="0 9 * * *"
              className="bg-white/5 border-white/10 text-white placeholder:text-white/30"
            />
          </FormField>
          <FormField label="Timezone" htmlFor="timezone">
            <Select
              value={config.schedule?.timezone || "UTC"}
              onValueChange={(value) =>
                onChange({
                  ...config,
                  schedule: { ...config.schedule, cron: config.schedule?.cron || "", timezone: value },
                })
              }
            >
              <SelectTrigger id="timezone" className="bg-white/5 border-white/10 text-white">
                <SelectValue placeholder="Select timezone" />
              </SelectTrigger>
              <SelectContent className="bg-[#14141f] border-white/10">
                <SelectItem value="UTC">UTC</SelectItem>
                <SelectItem value="America/New_York">Eastern Time</SelectItem>
                <SelectItem value="America/Chicago">Central Time</SelectItem>
                <SelectItem value="America/Denver">Mountain Time</SelectItem>
                <SelectItem value="America/Los_Angeles">Pacific Time</SelectItem>
                <SelectItem value="Europe/London">London</SelectItem>
                <SelectItem value="Asia/Tokyo">Tokyo</SelectItem>
              </SelectContent>
            </Select>
          </FormField>
        </>
      )}

      {config.eventType === "webhook" && (
        <FormField
          label="Webhook URL"
          htmlFor="webhookUrl"
          error={errors.webhookUrl}
          hint="Your unique webhook endpoint URL"
        >
          <Input
            id="webhookUrl"
            value={config.webhookUrl || ""}
            onChange={(e) => onChange({ ...config, webhookUrl: e.target.value })}
            placeholder="https://..."
            readOnly
            className="bg-white/5 border-white/10 text-white placeholder:text-white/30"
          />
        </FormField>
      )}

      {config.eventType === "job_posting" && (
        <FormField label="Keywords Filter" htmlFor="keywords" hint="Comma-separated keywords">
          <Input
            id="keywords"
            value={config.filters?.keywords?.join(", ") || ""}
            onChange={(e) =>
              onChange({
                ...config,
                filters: {
                  ...config.filters,
                  keywords: e.target.value.split(",").map((k) => k.trim()).filter(Boolean),
                },
              })
            }
            placeholder="react, typescript, senior"
            className="bg-white/5 border-white/10 text-white placeholder:text-white/30"
          />
        </FormField>
      )}
    </div>
  );
}

// Action configuration form
interface ActionFormProps {
  config: ActionConfig;
  onChange: (config: ActionConfig) => void;
  nodeTypeId: string;
}

function ActionForm({ config, onChange, nodeTypeId }: ActionFormProps) {
  return (
    <div className="space-y-4">
      {nodeTypeId === "generate-resume" && (
        <>
          <FormField label="Resume Template" htmlFor="template">
            <Select
              value={(config.parameters?.template as string) || "default"}
              onValueChange={(value) =>
                onChange({ ...config, parameters: { ...config.parameters, template: value } })
              }
            >
              <SelectTrigger id="template" className="bg-white/5 border-white/10 text-white">
                <SelectValue placeholder="Select template" />
              </SelectTrigger>
              <SelectContent className="bg-[#14141f] border-white/10">
                <SelectItem value="default">Default Template</SelectItem>
                <SelectItem value="modern">Modern</SelectItem>
                <SelectItem value="classic">Classic</SelectItem>
                <SelectItem value="minimal">Minimal</SelectItem>
                <SelectItem value="creative">Creative</SelectItem>
              </SelectContent>
            </Select>
          </FormField>
          <FormField label="Customization Level" htmlFor="customization">
            <Select
              value={(config.parameters?.customization as string) || "balanced"}
              onValueChange={(value) =>
                onChange({ ...config, parameters: { ...config.parameters, customization: value } })
              }
            >
              <SelectTrigger id="customization" className="bg-white/5 border-white/10 text-white">
                <SelectValue placeholder="Select level" />
              </SelectTrigger>
              <SelectContent className="bg-[#14141f] border-white/10">
                <SelectItem value="minimal">Minimal - Keep original content</SelectItem>
                <SelectItem value="balanced">Balanced - Moderate adjustments</SelectItem>
                <SelectItem value="aggressive">Aggressive - Fully tailored</SelectItem>
              </SelectContent>
            </Select>
          </FormField>
        </>
      )}

      {nodeTypeId === "fill-application" && (
        <>
          <FormField label="Application Platform" htmlFor="platform">
            <Select
              value={(config.parameters?.platform as string) || "auto"}
              onValueChange={(value) =>
                onChange({ ...config, parameters: { ...config.parameters, platform: value } })
              }
            >
              <SelectTrigger id="platform" className="bg-white/5 border-white/10 text-white">
                <SelectValue placeholder="Select platform" />
              </SelectTrigger>
              <SelectContent className="bg-[#14141f] border-white/10">
                <SelectItem value="auto">Auto-detect</SelectItem>
                <SelectItem value="linkedin">LinkedIn</SelectItem>
                <SelectItem value="indeed">Indeed</SelectItem>
                <SelectItem value="workday">Workday</SelectItem>
                <SelectItem value="greenhouse">Greenhouse</SelectItem>
                <SelectItem value="lever">Lever</SelectItem>
              </SelectContent>
            </Select>
          </FormField>
          <FormField label="Credentials" htmlFor="credentials">
            <Select
              value={config.credentials?.credentialId || ""}
              onValueChange={(value) =>
                onChange({
                  ...config,
                  credentials: { credentialId: value, credentialType: "oauth" },
                })
              }
            >
              <SelectTrigger id="credentials" className="bg-white/5 border-white/10 text-white">
                <SelectValue placeholder="Select credentials" />
              </SelectTrigger>
              <SelectContent className="bg-[#14141f] border-white/10">
                <SelectItem value="linkedin-1">LinkedIn (john@example.com)</SelectItem>
                <SelectItem value="indeed-1">Indeed (john@example.com)</SelectItem>
              </SelectContent>
            </Select>
          </FormField>
        </>
      )}

      {nodeTypeId === "send-email-draft" && (
        <FormField label="Email Template" htmlFor="emailTemplate">
          <Select
            value={(config.parameters?.emailTemplate as string) || "follow-up"}
            onValueChange={(value) =>
              onChange({ ...config, parameters: { ...config.parameters, emailTemplate: value } })
            }
          >
            <SelectTrigger id="emailTemplate" className="bg-white/5 border-white/10 text-white">
              <SelectValue placeholder="Select template" />
            </SelectTrigger>
            <SelectContent className="bg-[#14141f] border-white/10">
              <SelectItem value="follow-up">Follow-up</SelectItem>
              <SelectItem value="thank-you">Thank You</SelectItem>
              <SelectItem value="inquiry">Inquiry</SelectItem>
              <SelectItem value="custom">Custom</SelectItem>
            </SelectContent>
          </Select>
        </FormField>
      )}

      <FormField label="Timeout (seconds)" htmlFor="timeout" hint="Maximum execution time">
        <Input
          id="timeout"
          type="number"
          min={1}
          max={300}
          value={config.timeout || 30}
          onChange={(e) => onChange({ ...config, timeout: parseInt(e.target.value) || 30 })}
          className="bg-white/5 border-white/10 text-white placeholder:text-white/30"
        />
      </FormField>
    </div>
  );
}

// Condition configuration form
interface ConditionFormProps {
  config: ConditionConfig;
  onChange: (config: ConditionConfig) => void;
  errors: ValidationErrors;
}

function ConditionForm({ config, onChange, errors }: ConditionFormProps) {
  return (
    <div className="space-y-4">
      <FormField label="Field" htmlFor="field" error={errors.field} required>
        <Input
          id="field"
          value={config.field}
          onChange={(e) => onChange({ ...config, field: e.target.value })}
          placeholder="e.g., job.salary, job.title"
          className="bg-white/5 border-white/10 text-white placeholder:text-white/30"
        />
      </FormField>

      <FormField label="Operator" htmlFor="operator" required>
        <Select
          value={config.operator}
          onValueChange={(value) =>
            onChange({ ...config, operator: value as ConditionConfig["operator"] })
          }
        >
          <SelectTrigger id="operator" className="bg-white/5 border-white/10 text-white">
            <SelectValue placeholder="Select operator" />
          </SelectTrigger>
          <SelectContent className="bg-[#14141f] border-white/10">
            <SelectItem value="equals">Equals</SelectItem>
            <SelectItem value="not_equals">Not Equals</SelectItem>
            <SelectItem value="contains">Contains</SelectItem>
            <SelectItem value="greater_than">Greater Than</SelectItem>
            <SelectItem value="less_than">Less Than</SelectItem>
            <SelectItem value="is_empty">Is Empty</SelectItem>
            <SelectItem value="is_not_empty">Is Not Empty</SelectItem>
          </SelectContent>
        </Select>
      </FormField>

      {!["is_empty", "is_not_empty"].includes(config.operator) && (
        <FormField label="Value" htmlFor="value" error={errors.value} required>
          <Input
            id="value"
            value={config.value}
            onChange={(e) => onChange({ ...config, value: e.target.value })}
            placeholder="Enter comparison value"
            className="bg-white/5 border-white/10 text-white placeholder:text-white/30"
          />
        </FormField>
      )}
    </div>
  );
}

// Output configuration form
interface OutputFormProps {
  config: OutputConfig;
  onChange: (config: OutputConfig) => void;
  errors: ValidationErrors;
  nodeTypeId: string;
}

function OutputForm({ config, onChange, errors, nodeTypeId }: OutputFormProps) {
  return (
    <div className="space-y-4">
      <FormField label="Destination" htmlFor="destination" required>
        <Select
          value={config.destination}
          onValueChange={(value) =>
            onChange({ ...config, destination: value as OutputConfig["destination"] })
          }
        >
          <SelectTrigger id="destination" className="bg-white/5 border-white/10 text-white">
            <SelectValue placeholder="Select destination" />
          </SelectTrigger>
          <SelectContent className="bg-[#14141f] border-white/10">
            {nodeTypeId === "apply-to-job" && (
              <SelectItem value="apply">Submit Application</SelectItem>
            )}
            <SelectItem value="draft">Save as Draft</SelectItem>
            <SelectItem value="email">Send via Email</SelectItem>
            <SelectItem value="webhook">Send to Webhook</SelectItem>
            <SelectItem value="file">Save to File</SelectItem>
          </SelectContent>
        </Select>
      </FormField>

      <FormField label="Format" htmlFor="format" required>
        <Select
          value={config.format}
          onValueChange={(value) =>
            onChange({ ...config, format: value as OutputConfig["format"] })
          }
        >
          <SelectTrigger id="format" className="bg-white/5 border-white/10 text-white">
            <SelectValue placeholder="Select format" />
          </SelectTrigger>
          <SelectContent className="bg-[#14141f] border-white/10">
            <SelectItem value="pdf">PDF</SelectItem>
            <SelectItem value="docx">Word Document (DOCX)</SelectItem>
            <SelectItem value="json">JSON</SelectItem>
            <SelectItem value="html">HTML</SelectItem>
          </SelectContent>
        </Select>
      </FormField>

      {config.destination === "file" && (
        <FormField label="Filename" htmlFor="filename" hint="Without extension">
          <Input
            id="filename"
            value={config.filename || ""}
            onChange={(e) => onChange({ ...config, filename: e.target.value })}
            placeholder="resume-{{date}}"
            className="bg-white/5 border-white/10 text-white placeholder:text-white/30"
          />
        </FormField>
      )}

      {config.destination === "email" && (
        <FormField
          label="Recipient Email"
          htmlFor="emailRecipient"
          error={errors.emailRecipient}
          required
        >
          <Input
            id="emailRecipient"
            type="email"
            value={config.emailRecipient || ""}
            onChange={(e) => onChange({ ...config, emailRecipient: e.target.value })}
            placeholder="recipient@example.com"
            className="bg-white/5 border-white/10 text-white placeholder:text-white/30"
          />
        </FormField>
      )}

      {config.destination === "webhook" && (
        <FormField
          label="Webhook URL"
          htmlFor="outputWebhookUrl"
          error={errors.webhookUrl}
          required
        >
          <Input
            id="outputWebhookUrl"
            value={config.webhookUrl || ""}
            onChange={(e) => onChange({ ...config, webhookUrl: e.target.value })}
            placeholder="https://..."
            className="bg-white/5 border-white/10 text-white placeholder:text-white/30"
          />
        </FormField>
      )}
    </div>
  );
}

export function NodeConfigPanel({
  node,
  isOpen,
  onClose,
  onUpdate,
  onDelete,
  className,
}: NodeConfigPanelProps) {
  const [localNode, setLocalNode] = useState<NodeConfig | null>(null);
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [isDirty, setIsDirty] = useState(false);

  // Sync local state with prop
  useEffect(() => {
    if (node) {
      setLocalNode(node);
      setIsDirty(false);
      setErrors({});
    }
  }, [node]);

  // Validate form
  const validate = useCallback((): boolean => {
    if (!localNode) return false;

    const newErrors: ValidationErrors = {};

    if (!localNode.title.trim()) {
      newErrors.title = "Title is required";
    }

    // Validate trigger config
    if (localNode.category === "trigger" && localNode.triggerConfig) {
      if (localNode.triggerConfig.eventType === "schedule") {
        if (!localNode.triggerConfig.schedule?.cron) {
          newErrors.cron = "Cron expression is required";
        }
      }
    }

    // Validate condition config
    if (localNode.category === "logic" && localNode.conditionConfig) {
      if (!localNode.conditionConfig.field) {
        newErrors.field = "Field is required";
      }
      if (
        !["is_empty", "is_not_empty"].includes(localNode.conditionConfig.operator) &&
        !localNode.conditionConfig.value
      ) {
        newErrors.value = "Value is required";
      }
    }

    // Validate output config
    if (localNode.category === "output" && localNode.outputConfig) {
      if (localNode.outputConfig.destination === "email" && !localNode.outputConfig.emailRecipient) {
        newErrors.emailRecipient = "Email recipient is required";
      }
      if (localNode.outputConfig.destination === "webhook" && !localNode.outputConfig.webhookUrl) {
        newErrors.webhookUrl = "Webhook URL is required";
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [localNode]);

  // Update handlers
  const handleTitleChange = (title: string) => {
    if (localNode) {
      setLocalNode({ ...localNode, title });
      setIsDirty(true);
    }
  };

  const handleDescriptionChange = (description: string) => {
    if (localNode) {
      setLocalNode({ ...localNode, description });
      setIsDirty(true);
    }
  };

  const handleTriggerConfigChange = (triggerConfig: TriggerConfig) => {
    if (localNode) {
      setLocalNode({ ...localNode, triggerConfig });
      setIsDirty(true);
    }
  };

  const handleActionConfigChange = (actionConfig: ActionConfig) => {
    if (localNode) {
      setLocalNode({ ...localNode, actionConfig });
      setIsDirty(true);
    }
  };

  const handleConditionConfigChange = (conditionConfig: ConditionConfig) => {
    if (localNode) {
      setLocalNode({ ...localNode, conditionConfig });
      setIsDirty(true);
    }
  };

  const handleOutputConfigChange = (outputConfig: OutputConfig) => {
    if (localNode) {
      setLocalNode({ ...localNode, outputConfig });
      setIsDirty(true);
    }
  };

  const handleSave = () => {
    if (localNode && validate()) {
      onUpdate(localNode);
      setIsDirty(false);
    }
  };

  const handleDelete = () => {
    if (localNode) {
      onDelete(localNode.id);
    }
  };

  if (!isOpen || !localNode) {
    return null;
  }

  const Icon = localNode.icon;
  const colors = categoryColors[localNode.category];

  return (
    <div
      className={cn(
        "flex flex-col h-full w-80",
        "animate-slide-in-right",
        className
      )}
      style={{
        background: "linear-gradient(180deg, rgba(15, 15, 20, 0.98) 0%, rgba(10, 10, 15, 0.98) 100%)",
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between p-4"
        style={{
          borderBottom: "1px solid rgba(255, 255, 255, 0.06)",
        }}
      >
        <div className="flex items-center gap-3">
          <div
            className="flex items-center justify-center w-10 h-10 rounded-lg transition-transform duration-200"
            style={{
              background: colors.bg,
              boxShadow: `0 0 20px ${colors.glow}`,
            }}
          >
            <Icon
              className="h-5 w-5"
              style={{ color: colors.text }}
            />
          </div>
          <div>
            <Badge
              variant="outline"
              className="text-[10px] uppercase tracking-wider"
              style={{
                background: colors.bg,
                borderColor: colors.border,
                color: colors.text,
              }}
            >
              {localNode.category}
            </Badge>
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          aria-label="Close panel"
          className="text-white/50 hover:text-white hover:bg-white/10"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-thin">
        {/* Basic Info */}
        <div className="space-y-4">
          <FormField label="Title" htmlFor="nodeTitle" error={errors.title} required>
            <Input
              id="nodeTitle"
              value={localNode.title}
              onChange={(e) => handleTitleChange(e.target.value)}
              placeholder="Enter node title"
              className="bg-white/5 border-white/10 text-white placeholder:text-white/30"
            />
          </FormField>

          <FormField label="Description" htmlFor="nodeDescription">
            <Textarea
              id="nodeDescription"
              value={localNode.description}
              onChange={(e) => handleDescriptionChange(e.target.value)}
              placeholder="Describe what this node does..."
              rows={3}
              className="bg-white/5 border-white/10 text-white placeholder:text-white/30 resize-none"
            />
          </FormField>
        </div>

        {/* Type-specific configuration */}
        <div
          className="pt-4"
          style={{
            borderTop: "1px solid rgba(255, 255, 255, 0.06)",
          }}
        >
          <h3
            className="font-mono text-[10px] uppercase tracking-widest mb-4"
            style={{ color: colors.text }}
          >
            Configuration
          </h3>

          {localNode.category === "trigger" && localNode.triggerConfig && (
            <TriggerForm
              config={localNode.triggerConfig}
              onChange={handleTriggerConfigChange}
              errors={errors}
            />
          )}

          {localNode.category === "action" && localNode.actionConfig && (
            <ActionForm
              config={localNode.actionConfig}
              onChange={handleActionConfigChange}
              nodeTypeId={localNode.nodeTypeId}
            />
          )}

          {localNode.category === "logic" && localNode.conditionConfig && (
            <ConditionForm
              config={localNode.conditionConfig}
              onChange={handleConditionConfigChange}
              errors={errors}
            />
          )}

          {localNode.category === "output" && localNode.outputConfig && (
            <OutputForm
              config={localNode.outputConfig}
              onChange={handleOutputConfigChange}
              errors={errors}
              nodeTypeId={localNode.nodeTypeId}
            />
          )}
        </div>
      </div>

      {/* Footer */}
      <div
        className="p-4 space-y-3"
        style={{
          borderTop: "1px solid rgba(255, 255, 255, 0.06)",
          background: "rgba(255, 255, 255, 0.02)",
        }}
      >
        {isDirty && (
          <div
            className="flex items-center gap-2 text-[10px] px-3 py-2 rounded-lg"
            style={{
              background: "rgba(245, 158, 11, 0.1)",
              color: "#F59E0B",
            }}
          >
            <AlertCircle className="h-3 w-3" />
            <span>You have unsaved changes</span>
          </div>
        )}
        <div className="flex items-center gap-2">
          <Button
            variant="destructive"
            size="sm"
            onClick={handleDelete}
            className="gap-1.5 bg-red-500/10 text-red-400 border-red-500/30 hover:bg-red-500/20"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Delete
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!isDirty}
            className="flex-1 bg-gradient-to-r from-primary to-cyan-600 hover:from-primary/90 hover:to-cyan-600/90 text-white border-0"
            style={{
              boxShadow: isDirty ? "0 0 20px rgba(20, 184, 166, 0.3)" : "none",
            }}
          >
            Save Changes
          </Button>
        </div>
      </div>
    </div>
  );
}

export default NodeConfigPanel;
