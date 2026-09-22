/**
 * Client-side resize before upload. The backend already caps every image at
 * 1280px on the longest side (backend/lmd/api/scan.py's _API_MAX_DIM), so a
 * phone photo (often 4000x3000, several MB) is shrunk on the same wire it
 * would be shrunk on the server -- doing it here cuts upload time and the
 * server's peak RSS by the same factor the resize itself represents.
 *
 * Files already at or under maxDim AND already JPEG are returned completely
 * unchanged (not just visually equivalent) -- pipeline B's vision cache
 * (backend/lmd/cv/pipeline_b.py) keys on the sha256 of the uploaded bytes,
 * so a byte-identical upload is what makes a pre-primed demo cache hit.
 */
export async function resizeForUpload(file: File, maxDim = 1280): Promise<File> {
  if (file.type !== "image/jpeg" && file.type !== "image/png") {
    return file;
  }

  try {
    const bitmap = await createImageBitmap(file);
    const { width, height } = bitmap;
    const longest = Math.max(width, height);

    if (longest <= maxDim && file.type === "image/jpeg") {
      bitmap.close();
      return file;
    }

    const scale = Math.min(1, maxDim / longest);
    const targetWidth = Math.max(1, Math.round(width * scale));
    const targetHeight = Math.max(1, Math.round(height * scale));

    const canvas = new OffscreenCanvas(targetWidth, targetHeight);
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      bitmap.close();
      return file;
    }
    ctx.drawImage(bitmap, 0, 0, targetWidth, targetHeight);
    bitmap.close();

    const blob = await canvas.convertToBlob({ type: "image/jpeg", quality: 0.85 });
    const name = file.name.replace(/\.[^./\\]+$/, "") + ".jpg";
    return new File([blob], name, { type: "image/jpeg" });
  } catch {
    // A resize failure must never block a scan -- fall back to the original
    // file and let the server-side resize handle it.
    return file;
  }
}

export interface ImageQualityReport {
  width: number;
  height: number;
  /** Laplacian variance over a downscaled grayscale copy -- lower means
   *  blurrier. Not a calibrated physical unit, just a relative sharpness
   *  score; do not surface this number to the user, only the derived
   *  warning. */
  blurVariance: number;
  warnings: string[];
}

const MIN_WIDTH_PX = 800;
const MIN_HEIGHT_PX = 600;
const MIN_FILE_BYTES = 50 * 1024;
// Measured against a handful of sharp vs visibly-blurred package photos
// during development, not a research-verified constant -- this is advisory
// client-side feedback, not a gate, so a rough threshold is acceptable.
const BLUR_VARIANCE_THRESHOLD = 45;

/**
 * Client-side-only heuristics (resolution, blur, suspiciously small file)
 * that warn the user *before* upload about an image likely to come back
 * mostly NEEDS_REVIEW from OCR, so they can retake the photo instead of
 * waiting through a wasted scan. Never blocks or alters the upload -- the
 * server pipeline runs on whatever file is sent regardless of this report.
 */
export async function assessImageQuality(file: File): Promise<ImageQualityReport> {
  const warnings: string[] = [];

  if (file.size < MIN_FILE_BYTES) {
    warnings.push(
      `File is only ${(file.size / 1024).toFixed(0)} KB — likely a screenshot of a screenshot or an over-compressed copy. Text may be unreadable to OCR.`,
    );
  }

  let width = 0;
  let height = 0;
  let blurVariance = Infinity;

  try {
    const bitmap = await createImageBitmap(file);
    width = bitmap.width;
    height = bitmap.height;

    if (width < MIN_WIDTH_PX || height < MIN_HEIGHT_PX) {
      warnings.push(
        `Image is ${width}×${height}px, below the recommended ${MIN_WIDTH_PX}×${MIN_HEIGHT_PX}px minimum. Small print may not be readable.`,
      );
    }

    blurVariance = laplacianVariance(bitmap);
    bitmap.close();

    if (blurVariance < BLUR_VARIANCE_THRESHOLD) {
      warnings.push(
        "Image looks blurry (low edge sharpness). Hold the camera steady and retake in better light for a cleaner read.",
      );
    }
  } catch {
    // A quality-check failure must never block a scan -- report what we
    // have (possibly just the file-size warning) and let the upload proceed.
  }

  return { width, height, blurVariance, warnings };
}

/** Laplacian variance on a downscaled grayscale copy: convolve with the
 *  standard 4-neighbour Laplacian kernel ([0,1,0;1,-4,1;0,1,0]) and take the
 *  variance of the response. Sharp edges produce large-magnitude responses
 *  with high variance; a blurred image's edges are smeared, so the response
 *  stays close to zero everywhere -- low variance. Downscaled to a fixed
 *  small dimension first because blur is a global sharpness property that
 *  doesn't need full resolution to measure, and it keeps this fast enough
 *  to run synchronously on file selection. */
function laplacianVariance(bitmap: ImageBitmap): number {
  const targetDim = 300;
  const scale = Math.min(1, targetDim / Math.max(bitmap.width, bitmap.height));
  const w = Math.max(3, Math.round(bitmap.width * scale));
  const h = Math.max(3, Math.round(bitmap.height * scale));

  const canvas = new OffscreenCanvas(w, h);
  const ctx = canvas.getContext("2d");
  if (!ctx) return Infinity;
  ctx.drawImage(bitmap, 0, 0, w, h);

  const { data } = ctx.getImageData(0, 0, w, h);
  const gray = new Float32Array(w * h);
  for (let i = 0; i < w * h; i++) {
    const r = data[i * 4];
    const g = data[i * 4 + 1];
    const b = data[i * 4 + 2];
    gray[i] = 0.299 * r + 0.587 * g + 0.114 * b;
  }

  let sum = 0;
  let sumSq = 0;
  let count = 0;
  for (let y = 1; y < h - 1; y++) {
    for (let x = 1; x < w - 1; x++) {
      const idx = y * w + x;
      const lap = gray[idx - w] + gray[idx + w] + gray[idx - 1] + gray[idx + 1] - 4 * gray[idx];
      sum += lap;
      sumSq += lap * lap;
      count++;
    }
  }
  if (count === 0) return Infinity;
  const mean = sum / count;
  return sumSq / count - mean * mean;
}
