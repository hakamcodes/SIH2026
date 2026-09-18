"use client";

import { useState } from "react";

import { polygonToPoints } from "@/lib/format";
import { CONFIDENCE_VOCAB, confidenceBand } from "@/lib/vocab";
import type { OcrBox } from "@/lib/types";

interface AnnotatedCanvasProps {
  scanId: string;
  boxes: OcrBox[];
  /** Hover preview, cleared on mouse leave. */
  hoverIndex: number | null;
  onHover: (index: number | null) => void;
  /** Click-pinned selection, persists until the same box is clicked again. */
  pinnedIndex: number | null;
  onPin: (index: number | null) => void;
}

/**
 * Renders the raw source image (GET /scans/{id}/image, Phase 0) with an
 * absolutely-positioned SVG polygon layer built from ocr_boxes[], rather than
 * the baked overlay PNG -- this scales without pixelation and each box is
 * hoverable/keyboard-focusable. Boxes are coloured by OCR confidence only,
 * never by rule outcome: cv/overlay.py deliberately refuses to claim a box
 * caused a rule failure, and this view must not imply that link either.
 *
 * GET /api/v1/scans/{id} does not persist image_width/image_height (only
 * POST's immediate response does), so the SVG viewBox is sized from the
 * image's own onLoad naturalWidth/naturalHeight instead of a prop -- avoids
 * a backend change for a value the browser already knows.
 */
export function AnnotatedCanvas({
  scanId,
  boxes,
  hoverIndex,
  onHover,
  pinnedIndex,
  onPin,
}: AnnotatedCanvasProps) {
  const activeIndex = pinnedIndex ?? hoverIndex;
  const [natural, setNatural] = useState<{ w: number; h: number } | null>(null);

  return (
    <div
      className="animate-fade-in-up relative w-full select-none bg-surface-subtle"
      onMouseLeave={() => onHover(null)}
    >
      {/* eslint-disable-next-line @next/next/no-img-element -- served through
          the /api/lmd proxy, not a static/optimizable asset. */}
      <img
        src={`/api/lmd/scans/${scanId}/image`}
        alt="Package, as submitted"
        className="block h-auto w-full max-h-[60vh] object-contain"
        draggable={false}
        onLoad={(e) =>
          setNatural({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })
        }
      />
      {natural && (
        <svg
          viewBox={`0 0 ${natural.w} ${natural.h}`}
          preserveAspectRatio="xMidYMid meet"
          className="absolute inset-0 size-full"
        >
          {boxes.map((box, index) => {
            const stroke = CONFIDENCE_VOCAB[confidenceBand(box.confidence)].stroke;
            const isActive = index === activeIndex;
            return (
              <polygon
                key={index}
                points={polygonToPoints(box.polygon)}
                fill={stroke}
                fillOpacity={isActive ? 0.22 : 0}
                stroke={stroke}
                strokeWidth={isActive ? 3 : 1.25}
                vectorEffect="non-scaling-stroke"
                tabIndex={0}
                role="button"
                aria-label={`OCR text "${box.text}", ${(box.confidence * 100).toFixed(0)} percent confidence`}
                style={{ "--stagger": Math.min(index, 24) } as React.CSSProperties}
                className="stagger-item cursor-pointer outline-none transition-[fill-opacity,stroke-width] duration-[var(--dur-fast)] ease-[var(--ease)]"
                onMouseEnter={() => onHover(index)}
                onFocus={() => onHover(index)}
                onClick={() => onPin(pinnedIndex === index ? null : index)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onPin(pinnedIndex === index ? null : index);
                  }
                }}
              />
            );
          })}
        </svg>
      )}
    </div>
  );
}
