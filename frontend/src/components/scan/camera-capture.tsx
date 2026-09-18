"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, CameraOff, SwitchCamera, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface CameraCaptureProps {
  onCapture: (file: File) => void;
  onCancel?: () => void;
}

/**
 * Uses navigator.mediaDevices.getUserMedia to capture a photo from the
 * device camera. Falls back to a clear error when camera is unavailable
 * (desktop without camera, denied permission, etc.).
 *
 * The stream is torn down on unmount and on cancel to avoid leaving the
 * camera indicator light on.
 */
export function CameraCapture({ onCapture, onCancel }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [facingMode, setFacingMode] = useState<"environment" | "user">("environment");
  const [capturing, setCapturing] = useState(false);

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setReady(false);
  }, []);

  const startStream = useCallback(async (facing: "environment" | "user") => {
    stopStream();
    setError(null);
    setReady(false);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: facing, width: { ideal: 1280 }, height: { ideal: 960 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setReady(true);
      }
    } catch (err) {
      const msg =
        err instanceof DOMException && err.name === "NotAllowedError"
          ? "Camera permission denied. Allow camera access in browser settings."
          : err instanceof DOMException && err.name === "NotFoundError"
            ? "No camera found on this device."
            : "Could not start camera.";
      setError(msg);
    }
  }, [stopStream]);

  useEffect(() => {
    startStream(facingMode);
    return stopStream;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [facingMode]);

  function handleCapture() {
    if (!videoRef.current || !ready || capturing) return;
    setCapturing(true);
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    canvas.toBlob(
      (blob) => {
        setCapturing(false);
        if (blob) {
          const file = new File([blob], `capture_${Date.now()}.jpg`, { type: "image/jpeg" });
          stopStream();
          onCapture(file);
        }
      },
      "image/jpeg",
      0.92,
    );
  }

  function handleSwitchCamera() {
    setFacingMode((prev) => (prev === "environment" ? "user" : "environment"));
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Guidance banner */}
      <div className="rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-700">
        📷 Hold steady · Keep package fully visible · Good lighting helps OCR accuracy
      </div>

      {/* Video preview + scanner frame guide */}
      <div className="relative aspect-4/3 w-full overflow-hidden rounded-md bg-black">
        <video
          ref={videoRef}
          className={cn(
            "absolute inset-0 h-full w-full object-cover",
            !ready && "opacity-0",
          )}
          playsInline
          muted
          aria-label="Camera preview"
        />

        {/* Document scanning frame overlay — SVG corner brackets */}
        {ready && (
          <svg
            className="pointer-events-none absolute inset-0 h-full w-full"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            {/* Semi-transparent vignette around the frame */}
            <rect
              x="0" y="0" width="100" height="100"
              fill="rgba(0,0,0,0.25)"
              mask="url(#frame-cutout)"
            />
            <mask id="frame-cutout">
              <rect x="0" y="0" width="100" height="100" fill="white" />
              <rect x="8" y="8" width="84" height="84" rx="1" fill="black" />
            </mask>
            {/* Corner bracket — top-left */}
            <path d="M8 18 L8 8 L18 8" stroke="white" strokeWidth="1.5" fill="none" strokeLinecap="round" />
            {/* Corner bracket — top-right */}
            <path d="M82 8 L92 8 L92 18" stroke="white" strokeWidth="1.5" fill="none" strokeLinecap="round" />
            {/* Corner bracket — bottom-left */}
            <path d="M8 82 L8 92 L18 92" stroke="white" strokeWidth="1.5" fill="none" strokeLinecap="round" />
            {/* Corner bracket — bottom-right */}
            <path d="M82 92 L92 92 L92 82" stroke="white" strokeWidth="1.5" fill="none" strokeLinecap="round" />
          </svg>
        )}

        {!ready && !error && (
          <div className="absolute inset-0 flex items-center justify-center text-white text-sm">
            Starting camera…
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 p-4">
            <CameraOff className="size-8 text-white/60" aria-hidden="true" />
            <p className="text-center text-sm text-white/80">{error}</p>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="flex items-center gap-2">
        {onCancel && (
          <Button type="button" variant="outline" size="sm" onClick={() => { stopStream(); onCancel(); }} className="gap-1.5">
            <X className="size-3.5" aria-hidden="true" />
            Cancel
          </Button>
        )}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleSwitchCamera}
          disabled={!!error}
          className="gap-1.5"
          title="Switch between front and rear camera"
        >
          <SwitchCamera className="size-3.5" aria-hidden="true" />
          Flip
        </Button>
        <Button
          type="button"
          onClick={handleCapture}
          disabled={!ready || capturing}
          className="ml-auto min-h-[44px] gap-1.5 bg-gradient-cta text-accent-cta-foreground px-5"
        >
          <Camera className="size-4" aria-hidden="true" />
          {capturing ? "Capturing…" : "Capture"}
        </Button>
      </div>
    </div>
  );
}
