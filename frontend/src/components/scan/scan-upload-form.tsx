"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { CalendarClock, Camera, ImageUp, Layers, ScanLine, X } from "lucide-react";
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
import {
  createScanWithProgress,
  createMultiScanWithProgress,
  type CreateMultiScanParams,
} from "@/lib/api";
import { describeUnknownError } from "@/lib/errors";
import type { ScanStageEvent, ScanStreamEvent } from "@/lib/types";
import { useBackendReady } from "@/lib/use-backend-ready";
import { cn } from "@/lib/utils";

import { CameraCapture } from "./camera-capture";
import { ScanProcessingPanel, type ScanProcessingPhase } from "./scan-processing-panel";

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

type InputMode = "upload" | "camera";
type PanelSlot = "back" | "side" | "other";
const PANEL_LABELS: Record<PanelSlot, string> = {
  back: "Back panel",
  side: "Side panel",
  other: "Other panel",
};

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
  const { ready: backendReady, attempts: backendAttempts } = useBackendReady();
  const inputId = useId();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [inputMode, setInputMode] = useState<InputMode>("upload");

  // Front / primary image
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Extra panel images (back, side, other)
  const [panelFiles, setPanelFiles] = useState<Partial<Record<PanelSlot, File>>>({});
  // Which extra panel slot (if any) currently has its camera open
  const [panelCameraSlot, setPanelCameraSlot] = useState<PanelSlot | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [processingPhase, setProcessingPhase] = useState<ScanProcessingPhase | null>(null);
  const [uploadPercent, setUploadPercent] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [stages, setStages] = useState<ScanStageEvent[]>([]);
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

  function setPanelFile(slot: PanelSlot, f: File | null) {
    setPanelFiles((prev) => {
      const next = { ...prev };
      if (f) next[slot] = f;
      else delete next[slot];
      return next;
    });
  }

  useEffect(() => {
    if (processingPhase !== "processing") return;
    const interval = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, [processingPhase]);

  const hasExtraPanels = Object.keys(panelFiles).length > 0;

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!file || submitting || !backendReady) return;

    setSubmitting(true);
    setSubmitError(null);
    setUploadPercent(0);
    setElapsedSeconds(0);
    setStages([]);
    setProcessingPhase("uploading");

    const onUploadProgress = (percent: number) => {
      setUploadPercent(percent);
      if (percent >= 100) setProcessingPhase("processing");
    };
    const onStage = (event: ScanStreamEvent) => {
      if (event.event === "stage") setStages((prev) => [...prev, event]);
    };

    try {
      let result;
      if (hasExtraPanels) {
        const params: CreateMultiScanParams = {
          front: file,
          back: panelFiles.back,
          side: panelFiles.side,
          other: panelFiles.other,
          scanDate: form.scanDate || undefined,
          commodityCategory: form.commodityCategory || undefined,
          commoditySubtype: form.commoditySubtype || undefined,
          commodityIsImported: form.isImported,
          commodityIsExempt: form.isExempt,
        };
        result = await createMultiScanWithProgress(params, { onUploadProgress, onStage });
      } else {
        result = await createScanWithProgress(
          {
            image: file,
            scanDate: form.scanDate || undefined,
            commodityCategory: form.commodityCategory || undefined,
            commoditySubtype: form.commoditySubtype || undefined,
            commodityIsImported: form.isImported,
            commodityIsExempt: form.isExempt,
          },
          { onUploadProgress, onStage },
        );
      }

      setProcessingPhase("finalizing");
      const panels = result.panels_processed?.length
        ? ` (${result.panels_processed.length} panels)`
        : "";
      toast.success(`Scan complete${panels} — ${result.overall_verdict.replace("_", " ").toLowerCase()}`);

      // Show barcode info if detected
      if (result.barcodes?.length) {
        toast.info(`Barcode detected: ${result.barcodes[0].text}`);
      }

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
        stages={stages}
      />
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-6 lg:flex-row">
      {/* Left: image capture area */}
      <div className="flex-1 flex flex-col gap-3">
        {/* Mode tabs */}
        <div className="flex rounded-md border border-border overflow-hidden text-sm">
          {(["upload", "camera"] as InputMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => setInputMode(mode)}
              className={cn(
                "flex-1 flex items-center justify-center gap-1.5 py-2.5 font-medium transition-colors",
                inputMode === mode
                  ? "bg-primary text-primary-foreground"
                  : "bg-surface text-fg-muted hover:bg-surface-subtle",
              )}
            >
              {mode === "upload" ? (
                <><ImageUp className="size-3.5" aria-hidden="true" /> Upload</>
              ) : (
                <><Camera className="size-3.5" aria-hidden="true" /> Camera</>
              )}
            </button>
          ))}
        </div>

        {/* Upload dropzone */}
        {inputMode === "upload" && (
          <div>
            <Label htmlFor={inputId} className="sr-only">Package image</Label>
            <div
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              className={cn(
                "relative flex aspect-4/3 flex-col items-center justify-center gap-3 rounded-md border-2 border-dashed border-border bg-surface-subtle p-6 text-center transition-[background-color,border-color,box-shadow] duration-[var(--dur-fast)]",
                isDragging && "animate-dash-pulse border-primary bg-[color-mix(in_oklab,var(--surface-subtle),var(--primary)_8%)] shadow-md",
              )}
            >
              {previewUrl ? (
                <>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={previewUrl}
                    alt="Selected package"
                    className="animate-scale-in absolute inset-0 size-full rounded-[calc(var(--radius)-1px)] object-contain p-2"
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
                    <p className="text-sm font-medium text-foreground">Drop a package photo, or browse</p>
                    <p className="mt-1 text-xs text-fg-muted">JPEG or PNG · front panel (required)</p>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => fileInputRef.current?.click()}
                    className="min-h-[44px]"
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
        )}

        {/* Camera capture */}
        {inputMode === "camera" && (
          <CameraCapture
            onCapture={(captured) => {
              acceptFile(captured);
              setInputMode("upload");
            }}
          />
        )}

        {/* Extra panel slots (back / side / other) */}
        {file && (
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-1.5 text-xs text-fg-muted">
              <Layers className="size-3.5" aria-hidden="true" />
              <span>Optional: add more panels for a complete multi-panel scan</span>
            </div>
            {(["back", "side", "other"] as PanelSlot[]).map((slot) => {
              const slotFile = panelFiles[slot];
              const cameraOpen = panelCameraSlot === slot;
              return (
                <div key={slot} className="flex flex-col gap-2 rounded-md border border-border bg-surface-subtle px-3 py-2">
                  {/* Slot header row */}
                  <div className="flex items-center gap-2">
                    <span className="w-20 text-xs font-medium text-fg-muted shrink-0">{PANEL_LABELS[slot]}</span>
                    {slotFile ? (
                      <>
                        <span className="flex-1 truncate font-mono text-2xs text-fg-muted">{slotFile.name}</span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="size-6 shrink-0"
                          onClick={() => setPanelFile(slot, null)}
                          aria-label={`Remove ${PANEL_LABELS[slot]}`}
                        >
                          <X className="size-3" />
                        </Button>
                      </>
                    ) : cameraOpen ? (
                      <span className="flex-1 text-xs text-fg-muted">Camera active…</span>
                    ) : (
                      <div className="flex flex-1 items-center gap-2">
                        {/* File picker */}
                        <label className="cursor-pointer text-xs text-link hover:text-link-hover">
                          + File
                          <input
                            type="file"
                            accept="image/jpeg,image/png"
                            className="sr-only"
                            onChange={(e) => {
                              const f = e.target.files?.[0];
                              if (f) setPanelFile(slot, f);
                            }}
                          />
                        </label>
                        <span className="text-xs text-fg-subtle">or</span>
                        {/* Camera button */}
                        <button
                          type="button"
                          onClick={() => setPanelCameraSlot(slot)}
                          className="inline-flex items-center gap-1 text-xs text-link hover:text-link-hover"
                        >
                          <Camera className="size-3" aria-hidden="true" />
                          Camera
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Inline camera for this slot */}
                  {cameraOpen && (
                    <CameraCapture
                      onCapture={(captured) => {
                        setPanelFile(slot, captured);
                        setPanelCameraSlot(null);
                      }}
                      onCancel={() => setPanelCameraSlot(null)}
                    />
                  )}
                </div>
              );
            })}
            {hasExtraPanels && (
              <p className="text-2xs text-fg-subtle">
                Multi-panel scan: panels processed sequentially on server to keep memory usage stable.
              </p>
            )}
          </div>
        )}
      </div>

      {/* Right: form fields */}
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
          <label className="flex items-center gap-2 text-sm min-h-[44px]">
            <Checkbox
              checked={form.isImported}
              onCheckedChange={(v) => setForm((f) => ({ ...f, isImported: v === true }))}
            />
            Imported commodity
          </label>
          <label className="flex items-center gap-2 text-sm min-h-[44px]">
            <Checkbox
              checked={form.isExempt}
              onCheckedChange={(v) => setForm((f) => ({ ...f, isExempt: v === true }))}
            />
            Exempt from packaging rules
          </label>
        </div>

        {!backendReady && (
          <p className="rounded-md border border-border bg-surface-subtle px-3 py-2 text-xs text-fg-muted">
            Waking the analysis server — Render&apos;s free tier sleeps after 15 minutes of
            inactivity (typically 30–60s){backendAttempts > 1 ? ` · attempt ${backendAttempts}` : ""}
          </p>
        )}
        <Button
          type="submit"
          disabled={!file || submitting || !backendReady}
          className="w-full min-h-[52px] gap-1.5 bg-gradient-cta text-accent-cta-foreground shadow-sm transition-[box-shadow,transform] hover:shadow-md hover:-translate-y-px text-base"
        >
          <ScanLine className="size-4" aria-hidden="true" />
          {hasExtraPanels ? `Run multi-panel scan (${Object.keys(panelFiles).length + 1} panels)` : "Run scan"}
        </Button>
        {submitError && <ErrorNotice>{submitError}</ErrorNotice>}
      </div>
    </form>
  );
}
