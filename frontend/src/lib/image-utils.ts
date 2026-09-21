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
