"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { CalendarClock, ImageUp, ScanLine, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
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
import { createScanWithProgress } from "@/lib/api";
import { describeUnknownError } from "@/lib/errors";
import { cn } from "@/lib/utils";

import { ScanProcessingPanel, type ScanProcessingPhase } from "./scan-processing-panel";

const CAPTION_ROTATE_MS = 3400;

/**
 * The dropzone is hand-rolled rather than adapted from a 21st.dev catalogue
 * component -- every dropzone in that search bundled multi-file management,
 * upload-progress bars, or a details form this endpoint doesn't take
 * (POST /api/v1/scans accepts exactly one `image` file). A single-file
 * dropzone with a preview and a remove control is around 60 lines; adapting
 * a 150-line multi-file component down to that would mean deleting more than
 * it kept.
 */
const COMMODITY_CATEGORIES = [
  "biscuits",
  "bread",
  "milk_powder",
  "soaps",
  "detergent",
  "paints",
  "cement",
  "rice",
  "edible_oil",
  "bottled_water",
  "other",
] as const;

interface ScanFormState {
  scanDate: string;
  commodityCategory: string;
  commoditySubtype: string;
  isImported: boolean;
  isExempt: boolean;
}

const today = () => new Date().toISOString().slice(0, 10);

export function ScanUploadForm() {
  const router = useRouter();
  const inputId = useId();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [processingPhase, setProcessingPhase] = useState<ScanProcessingPhase | null>(null);
  const [uploadPercent, setUploadPercent] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [captionIndex, setCaptionIndex] = useState(0);
  const [form, setForm] = useState<ScanFormState>({
    scanDate: today(),
    commodityCategory: "",
    commoditySubtype: "",
    isImported: false,
    isExempt: false,
  });

  const acceptFile = useCallback((next: File | null) => {
    setFile(next);
    setSubmitError(null);
    setPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return next ? URL.createObjectURL(next) : null;
    });
  }, []);

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    const dropped = event.dataTransfer.files?.[0];
    if (dropped && dropped.type.startsWith("image/")) acceptFile(dropped);
  }

  // Elapsed-time ticker for the "server-side processing" step -- real wall
  // clock time, shown so the wait never reads as a frozen screen even though
  // no genuine percentage is available for that phase.
  useEffect(() => {
    if (processingPhase !== "processing") return;
    const interval = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, [processingPhase]);

  // Rotating captions describing the pipeline's known stages. Cosmetic only
  // -- they do not claim to reflect the server's actual current position,
  // which this build has no way to observe (see ScanProcessingPanel).
  useEffect(() => {
    if (processingPhase !== "processing") return;
    const interval = setInterval(
      () => setCaptionIndex((i) => i + 1),
      CAPTION_ROTATE_MS,
    );
    return () => clearInterval(interval);
  }, [processingPhase]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!file || submitting) return;

    setSubmitting(true);
    setSubmitError(null);
    setUploadPercent(0);
    setElapsedSeconds(0);
    setCaptionIndex(0);
    setProcessingPhase("uploading");

    try {
      const result = await createScanWithProgress(
        {
          image: file,
          scanDate: form.scanDate || undefined,
          commodityCategory: form.commodityCategory || undefined,
          commoditySubtype: form.commoditySubtype || undefined,
          commodityIsImported: form.isImported,
          commodityIsExempt: form.isExempt,
        },
        {
          onUploadProgress: (percent) => {
            setUploadPercent(percent);
            // The upload event fires up to 100% well before the server has
            // even decoded the image; once the browser reports it complete,
            // whatever happens next is server-side.
            if (percent >= 100) setProcessingPhase("processing");
          },
        },
      );
      setProcessingPhase("finalizing");
      toast.success(`Scan complete — ${result.overall_verdict.replace("_", " ").toLowerCase()}`);
      router.push(`/scan/${result.scan_id}`);
    } catch (error) {
      setSubmitError(describeUnknownError(error));
      setSubmitting(false);
      setProcessingPhase(null);
    }
  }

  if (processingPhase) {
    return (
      <ScanProcessingPanel
        phase={processingPhase}
        uploadPercent={uploadPercent}
        elapsedSeconds={elapsedSeconds}
        captionIndex={captionIndex}
      />
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-6 lg:flex-row">
      <div className="flex-1">
        <Label htmlFor={inputId} className="sr-only">
          Package image
        </Label>
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={cn(
            "relative flex aspect-4/3 flex-col items-center justify-center gap-3 rounded-md border-2 border-dashed border-border bg-surface-subtle p-6 text-center transition-colors duration-[var(--dur-fast)]",
            isDragging && "border-link bg-[color-mix(in_oklab,var(--surface-subtle),var(--link)_8%)]",
          )}
        >
          {previewUrl ? (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element -- a
                  local blob: object URL cannot be optimized by next/image. */}
              <img
                src={previewUrl}
                alt="Selected package"
                className="absolute inset-0 size-full rounded-[calc(var(--radius)-1px)] object-contain p-2"
              />
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={() => acceptFile(null)}
                aria-label="Remove selected image"
                className="absolute top-2 right-2 size-8 bg-surface"
              >
                <X className="size-3.5" aria-hidden="true" />
              </Button>
              {file && (
                <p className="absolute bottom-2 left-2 rounded-sm border border-border bg-surface px-1.5 py-0.5 font-mono text-2xs text-fg-muted">
                  {file.name} · {(file.size / 1024).toFixed(0)} KB
                </p>
              )}
            </>
          ) : (
            <>
              <ImageUp className="size-7 text-fg-subtle" aria-hidden="true" />
              <div>
                <p className="text-sm font-medium text-foreground">
                  Drop a package photo, or browse
                </p>
                <p className="mt-1 text-xs text-fg-muted">JPEG or PNG, one image per scan</p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
              >
                Browse files
              </Button>
            </>
          )}
          <input
            ref={fileInputRef}
            id={inputId}
            type="file"
            accept="image/jpeg,image/png"
            className="sr-only"
            onChange={(e) => acceptFile(e.target.files?.[0] ?? null)}
          />
        </div>
      </div>

      <div className="flex w-full flex-col gap-4 lg:w-80">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="scan-date" className="flex items-center gap-1.5">
            <CalendarClock className="size-3.5 text-fg-subtle" aria-hidden="true" />
            Scan date
          </Label>
          <Input
            id="scan-date"
            type="date"
            value={form.scanDate}
            onChange={(e) => setForm((f) => ({ ...f, scanDate: e.target.value }))}
            className="font-mono text-sm"
          />
          <p className="text-xs text-fg-subtle">
            Rules are evaluated against the law in force on this date, not
            today&apos;s date — this is what makes point-in-time evaluation
            demonstrable.
          </p>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="commodity-category">Commodity category</Label>
          <Select
            value={form.commodityCategory}
            onValueChange={(v) => setForm((f) => ({ ...f, commodityCategory: v }))}
          >
            <SelectTrigger id="commodity-category" className="w-full">
              <SelectValue placeholder="Select a category" />
            </SelectTrigger>
            <SelectContent>
              {COMMODITY_CATEGORIES.map((c) => (
                <SelectItem key={c} value={c}>
                  {c.replaceAll("_", " ")}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="commodity-subtype">Subtype (optional)</Label>
          <Input
            id="commodity-subtype"
            value={form.commoditySubtype}
            onChange={(e) => setForm((f) => ({ ...f, commoditySubtype: e.target.value }))}
            placeholder="e.g. cream biscuits"
          />
        </div>

        <div className="flex flex-col gap-2.5 rounded-md border border-border p-3">
          <label className="flex items-center gap-2 text-sm">
            <Checkbox
              checked={form.isImported}
              onCheckedChange={(v) => setForm((f) => ({ ...f, isImported: v === true }))}
            />
            Imported commodity
          </label>
          <label className="flex items-center gap-2 text-sm">
            <Checkbox
              checked={form.isExempt}
              onCheckedChange={(v) => setForm((f) => ({ ...f, isExempt: v === true }))}
            />
            Exempt from packaging rules
          </label>
        </div>

        <Button type="submit" disabled={!file || submitting} className="w-full gap-1.5">
          <ScanLine className="size-4" aria-hidden="true" />
          Run scan
        </Button>
        {submitError && <ErrorNotice>{submitError}</ErrorNotice>}
      </div>
    </form>
  );
}
