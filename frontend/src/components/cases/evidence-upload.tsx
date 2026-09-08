"use client";

import { useId, useState } from "react";
import { UploadCloud } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ErrorNotice } from "@/components/common/error-state";
import { useInspector } from "@/components/shell/inspector-provider";
import { uploadEvidence } from "@/lib/api";
import { describeUnknownError } from "@/lib/errors";
import { EVIDENCE_TYPES } from "@/lib/types";
import type { EvidenceType } from "@/lib/types";
import { EVIDENCE_TYPE_VOCAB } from "@/lib/vocab";

interface EvidenceUploadProps {
  caseId: string;
  onUploaded: () => void;
}

/**
 * `evidence_type` and `device_identification` are query params on
 * POST /api/v1/cases/{case_id}/evidence, not multipart form fields
 * (backend/lmd/api/cases.py:82-83 declare them as plain function params with
 * no Form(...) marker) -- lib/api.ts's uploadEvidence() puts them on the URL
 * and only the file itself in the request body.
 */
export function EvidenceUpload({ caseId, onUploaded }: EvidenceUploadProps) {
  const { inspector } = useInspector();
  const inputId = useId();
  const [file, setFile] = useState<File | null>(null);
  const [evidenceType, setEvidenceType] = useState<EvidenceType>("PACKAGE_PHOTO");
  const [deviceId, setDeviceId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // File inputs are uncontrolled; bumping this key remounts the <Input> to
  // clear its selected file after a successful upload rather than reaching
  // for a ref (the shared Input component doesn't forward one).
  const [fileInputKey, setFileInputKey] = useState(0);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!file || !inspector || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await uploadEvidence(
        caseId,
        { file, evidenceType, deviceIdentification: deviceId || "unspecified" },
        inspector.inspectorId,
      );
      toast.success("Evidence attached");
      setFile(null);
      setDeviceId("");
      setFileInputKey((k) => k + 1);
      onUploaded();
    } catch (err) {
      setError(describeUnknownError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor={inputId}>File</Label>
        <Input
          key={fileInputKey}
          id={inputId}
          type="file"
          accept="image/jpeg,image/png,application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="evidence-type">Evidence type</Label>
        <Select value={evidenceType} onValueChange={(v) => setEvidenceType(v as EvidenceType)}>
          <SelectTrigger id="evidence-type" className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {EVIDENCE_TYPES.map((type) => (
              <SelectItem key={type} value={type}>
                {EVIDENCE_TYPE_VOCAB[type].label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="device-id">Device identification</Label>
        <Input
          id="device-id"
          value={deviceId}
          onChange={(e) => setDeviceId(e.target.value)}
          placeholder="e.g. inspector-phone-camera-01"
        />
        <p className="text-2xs text-fg-subtle">
          Recorded on the Section 63 certificate as the capturing device.
        </p>
      </div>

      <Button type="submit" size="sm" disabled={!file || !inspector || submitting} className="gap-1.5">
        <UploadCloud className="size-3.5" aria-hidden="true" />
        {submitting ? "Uploading…" : "Attach evidence"}
      </Button>
      {!inspector && (
        <p className="text-2xs text-fg-subtle">Sign in with an inspector identity to attach evidence.</p>
      )}
      {error && <ErrorNotice>{error}</ErrorNotice>}
    </form>
  );
}
