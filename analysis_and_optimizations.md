# MetriX (SIH 26034) — Deep Optimization & Competitive Analysis

> **Goal:** Make the prototype run reliably on Render's 512 MB free tier, load fast enough to impress judges reviewing 500 prototypes, and surface improvements that increase your chances of winning.

---

## Part 1: The RAM Problem — Why It Crashes

### Memory Budget Breakdown (512 MB total)

| Component | Estimated RSS | Notes |
|---|---|---|
| Python 3.13 interpreter + stdlib | ~30 MB | Unavoidable |
| FastAPI + Uvicorn + Pydantic + all deps | ~40 MB | Unavoidable |
| RapidOCR ONNX models loaded into memory | ~200–350 MB | PP-OCRv6 det + rec + cls sessions |
| OpenCV (cv2) import overhead | ~20 MB | Unavoidable once imported |
| Firebase Admin SDK + gRPC | ~30 MB | gRPC channels are heavy |
| **Idle baseline before any scan** | **~320–470 MB** | Already near the ceiling |
| **Single scan (1280px image pipeline)** | +50–100 MB spike | NumPy arrays, base64, overlay render |
| **Multi-panel scan (4 images)** | +100–200 MB spike | Sequential, but bytes buffered |

> [!CAUTION]
> Your idle baseline is already **320–470 MB**. A single scan pushes you to **420–570 MB**. The 512 MB hard kill is an OOM kill — no graceful error, the process just dies and Render restarts it (another 30–60s cold start).

### Where Exactly the RAM Goes

1. **RapidOCR's ONNX Runtime sessions** — The three ONNX models (det, cls, rec) are loaded into memory at startup via `_warm_ocr_engine()`. This is the **single largest consumer** (~200–350 MB). You've already set `intra_op_num_threads=1` and `inter_op_num_threads=1`, and `OMP_NUM_THREADS=1` + `MALLOC_ARENA_MAX=2` in render.yaml. Good — but the models themselves are that big.

2. **Image arrays during scan** — A 1280×960 BGR image is ~3.7 MB as a NumPy array. You create multiple copies: working frame, glare-masked frame, overlay frame, JPEG-encoded bytes, base64 string. You're doing explicit `= None` releases (good), but Python's GC doesn't always reclaim immediately.

3. **Firebase Admin SDK** — Imports `google-cloud-firestore` which pulls in `grpcio`, `google-auth`, `proto-plus`. The gRPC channel alone is ~20–30 MB.

4. **Base64 encoding** — `compress_for_storage` + `encode_base64` creates a base64 string (33% larger than bytes). For the original + overlay, you're holding both in memory simultaneously.

---

## Part 2: Optimization Strategies (Without Sacrificing Quality)

### 🔴 Priority 1 — Things That Will Make or Break the Demo

#### 1.1 Client-Side Image Resizing Before Upload

**Problem:** Phone cameras produce 4000×3000 (12 MP) images at 3–8 MB each. You're sending these raw to the backend, where `_resize_to_max_dim` shrinks them to 1280px anyway. The raw bytes consume bandwidth, upload time, and server RAM during the read.

**Solution:** Resize on the frontend using `<canvas>` before uploading. The backend already caps at 1280px — doing it client-side means:
- **Upload is 5–10x faster** (200 KB vs 5 MB)
- **Server RAM spike is 5–10x smaller** (200 KB buffer vs 5 MB buffer)
- **User perceives faster response** (upload phase shrinks from seconds to milliseconds)

**How:**
```typescript
// In lib/api.ts or a new lib/image-utils.ts
async function resizeImage(file: File, maxDim: number = 1280): Promise<Blob> {
  const bitmap = await createImageBitmap(file);
  const { width, height } = bitmap;
  const scale = Math.min(1, maxDim / Math.max(width, height));
  const canvas = new OffscreenCanvas(
    Math.round(width * scale),
    Math.round(height * scale)
  );
  const ctx = canvas.getContext("2d")!;
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  return canvas.convertToBlob({ type: "image/jpeg", quality: 0.85 });
}
```
Then in `buildScanFormData`, replace `formData.set("image", params.image)` with the resized blob.

> [!IMPORTANT]
> This is the **single highest-impact change**. It reduces upload time by 5–10x and cuts server-side memory spike by the same factor. Does not affect OCR quality since the backend was already capping at 1280px.

#### 1.2 Reduce ONNX Runtime Memory with Model Optimization

**Problem:** RapidOCR bundles full PP-OCRv6 models. The ONNX session memory is the biggest contributor to idle RSS.

**Options (pick one):**

| Option | Impact | Effort |
|---|---|---|
| **A. Use INT8 quantized models** | ~40–50% RAM reduction on model sessions | Medium — need to download INT8 variants of PP-OCRv6 and configure RapidOCR to use them |
| **B. Lazy-load the OCR engine** | Shifts ~200 MB from startup to first scan | Low — remove `_warm_ocr_engine()` from lifespan, accept slower first scan |
| **C. Use a smaller model (PP-OCRv4_mobile)** | ~30–40% RAM reduction, slightly lower accuracy | Medium — need to swap model files |

**Recommended:** Option **B** (lazy-load) is the safest for the demo. Remove `_warm_ocr_engine()` from the lifespan. Yes, the first scan will be ~10s slower, but:
- The **health check endpoint** will respond instantly (Render won't mark the service as unhealthy during startup)
- Idle RSS drops to ~150–200 MB, giving **300+ MB headroom** for the actual scan
- If the demo judge opens the page and browses the UI for even 10 seconds before scanning, the cold-start penalty is invisible

#### 1.3 Force Garbage Collection After Scan

**Problem:** Python's GC is generational and doesn't reclaim large arrays immediately. After a scan, the ~50–100 MB spike lingers.

**Solution:** Add explicit `gc.collect()` at the end of the scan endpoint:
```python
import gc

# At the end of create_scan(), after building the response dict:
gc.collect()
return { ... }
```
This costs ~5–20ms and can reclaim tens of MB immediately. On a 512 MB instance, that's worth it.

#### 1.4 Drop the Warm-Up Inference Call

In [main.py](file:///c:/Users/hakam/OneDrive/Desktop/CSS/SIH2634/SIH/backend/lmd/api/main.py#L20-L31), `_warm_ocr_engine()` runs a throwaway 64×64 inference. This forces ONNX Runtime to allocate its internal buffers at startup. Combined with the model load, this pushes startup RSS to peak before any real work happens.

**Trade-off:** The first real scan will be ~10s slower (one-time session init). But:
- Startup completes in ~3–5s instead of ~15s
- Peak startup RSS drops by ~50–100 MB
- Render's health check passes faster → the service appears "ready" sooner

### 🟡 Priority 2 — Things That Make the Demo Smoother

#### 2.1 Add a Loading/Wake-Up Screen on Frontend

**Problem:** Render free tier spins down after 15 minutes of inactivity. First request takes 30–60s to wake. A judge clicking your prototype link sees a blank/error screen for 30–60s.

**Solution:** On the frontend, the scan page should:
1. On mount, ping `/health` via the API proxy
2. While waiting, show a professional "waking up the server" animation with estimated time
3. Only enable the scan button when the backend is responsive

```tsx
// pseudo-code for scan/page.tsx
const [backendReady, setBackendReady] = useState(false);
useEffect(() => {
  const check = async () => {
    try {
      await fetch("/api/lmd/health", { signal: AbortSignal.timeout(5000) });
      setBackendReady(true);
    } catch {
      setTimeout(check, 3000); // retry every 3s
    }
  };
  check();
}, []);
```

This turns a broken first-impression into a polished "our servers are warming up" experience.

> [!TIP]
> Add a **keep-alive cron ping** on the frontend side. A simple `setInterval(() => fetch("/api/lmd/health"), 10 * 60 * 1000)` on the landing page keeps Render from spinning down while a judge is browsing your site. Even better: use Vercel's cron feature or an external pinger like UptimeRobot (free tier) to ping the Render health endpoint every 10 minutes.


#### 2.3 Vision Cache for Demo Images

[Pipeline B](file:///c:/Users/hakam/OneDrive/Desktop/CSS/SIH2634/SIH/backend/lmd/cv/pipeline_b.py) already caches Claude Vision responses by image SHA-256 in `data/cache/vision/`. But:
- `data/cache/vision/` is **empty** right now
- Render has no persistent disk, so the cache is lost on every deploy

**Solution:**
1. Run the demo images through Pipeline B locally
2. Commit the cache files to `data/cache/vision/`
3. For the demo, use the **same images** → Pipeline B is a cache hit → zero API latency → zero Anthropic cost → works even if ANTHROPIC_API_KEY expires

#### 2.4 Pre-Warm Render Before the Demo

Before the judges review your prototype:
1. Hit the health endpoint to wake Render
2. Run one scan to load the ONNX models and warm up ONNX Runtime
3. The next scans will be significantly faster

You can automate this with a simple script or even a browser bookmark that hits your `/health` endpoint.

### 🟢 Priority 3 — Nice to Have

#### 3.1 Compress the Overlay PNG More Aggressively

In [image_codec.py](file:///c:/Users/hakam/OneDrive/Desktop/CSS/SIH2634/SIH/backend/lmd/evidence/image_codec.py), the overlay PNG can be large. The iterative PNG compression loop is good, but you could:
- Render the overlay at a smaller resolution (900px instead of matching the input)
- Use palette-mode PNG (fewer colors = much smaller) since the overlay is basically boxes and text

#### 3.2 Stream Firestore Writes

The `create_scan` function builds the entire document dict (including two base64 image strings) in memory before writing. On a tight RAM budget, this is a ~2 MB allocation. Consider:
- Writing images_base64 in a separate update after the initial scan doc
- Or skipping overlay storage for multi-panel scans (you already do `ocr_boxes: []`)

#### 3.3 Use `uvicorn --limit-concurrency 1`

On a 512 MB instance, you cannot handle two concurrent scans. Set `--limit-concurrency 1` in the Render start command to queue the second request instead of crashing:

```yaml
startCommand: uvicorn lmd.main:app --host 0.0.0.0 --port $PORT --workers 1 --no-access-log --limit-concurrency 1
```

This is already implicitly the case (single worker), but `--limit-concurrency` makes it explicit and prevents a second connection from consuming memory before the first is done.

---

## Part 3: Limitations & Improvements to Increase Winning Chances

> [!NOTE]
> This section thinks differently about what judges actually look for. They're not just evaluating if the code runs — they're evaluating **completeness of thought, legal defensibility, innovation depth, and real-world viability**. Many of these ideas don't require code changes — they require **thinking** that most competitors won't do.

### 🏆 Things That Will Set You Apart (Most Competitors Won't Think Of)

#### 3.1 Your Limitations Page Is a Superpower — Weaponize It

Most SIH teams hide their limitations. You have a **dedicated `/limitations` endpoint and page** that programmatically surfaces what the system can't do. This is incredibly rare and shows intellectual honesty — which is what **real government deployments need**.

**How to leverage this:**
- In the PPT, dedicate one slide to "What We Deliberately Don't Claim" — show the limitations API response
- Frame it as: "A compliance tool that over-reports is as dangerous as one that under-reports. Our system knows its boundaries."
- Mention the `_FIXED_SCOPE_LIMITATIONS` list by name — judges will be impressed that you documented that net weight can't be verified from a photograph

#### 3.2 The Legal Red-Teaming Story

You have `legal-claim-audit.md` which **red-teams your own research and catches real legal errors** (wrong rule numbers, fabricated citations, incorrect Jan Vishwas dates). No other SIH team will have this.

**PPT talking point:** "We found that two legal citations in our own source material were AI-hallucinated. We built a blocklist (`citations.json → do_not_cite`) to prevent them from ever appearing in a report. This is the kind of reliability a government system needs."

#### 3.3 The "Three-State Verdict" Is Your Key Differentiator

Most competitors will build binary PASS/FAIL. Your three-state `COMPLIANT / NON_COMPLIANT / NEEDS_REVIEW` with the principle that **structural absence beats confidence** and **NEEDS_REVIEW is never collapsed** is genuinely novel.

**PPT talking point:** "Other systems force a yes/no answer. Ours says 'I'm not sure' when it genuinely isn't — and routes that to human review. An inspector needs to trust the system's 'yes' and its 'no'. That only works if it also has a 'maybe'."

#### 3.4 Point-in-Time Legal Evaluation

Your rule engine evaluates rules against `effective_from` / `effective_to` dates. This means you can demonstrate:
- "Show me the compliance result for this package if it was scanned on 31 March 2022" (before USP rule 6(11))
- "Now show me the same package on 1 April 2022" (after USP rule kicked in)

**This is a killer demo moment.** Show the same product flip from COMPLIANT to NON_COMPLIANT by changing only the scan date. No other SIH team will have this.

#### 3.5 Hot-Swappable Rules at Runtime

You have `lmd_rules.v2.draft.json` and a `/api/v1/rules/reload` endpoint. You can **live-swap the entire ruleset** without restarting the server.

**Demo moment:** "If the Ministry of Consumer Affairs issues a new amendment tomorrow, a legal officer can update one JSON file and reload — no code deployment needed. Let me show you..."

### 🔧 Technical Improvements Worth Making

#### 3.6 Missing: Client-Side Image Quality Feedback

**Problem:** If a user uploads a blurry, dark, or too-small image, the OCR will fail silently and the scan will return NEEDS_REVIEW for most fields. The user doesn't know why.

**Solution:** Before uploading, run client-side checks:
- **Resolution check:** Warn if image is below 800×600
- **Blur detection:** Use a simple Laplacian variance on canvas pixel data
- **File size check:** Warn if image is suspiciously small (< 50 KB, likely a screenshot of a screenshot)

This costs zero server resources and prevents wasted scans.

#### 3.7 Missing: Scan History / Progress on Frontend

The frontend has no scan history. A user who scans 5 products has no way to find their results again (except bookmarking the scan URL). Add a simple scan list page that queries `/api/v1/scans` (you'd need to add a list-scans endpoint — `repository.py` doesn't have one).

#### 3.8 Missing: Error Recovery for Long Scans

If the backend takes 30+ seconds (which it will on Render free tier), the frontend's XHR has no timeout. The user sees the processing animation indefinitely if the backend OOM-crashes.

**Solution:**
- Set a 120s timeout on the XHR
- If timeout fires, show "The analysis is taking longer than expected. The server may be under load. Please try again."
- Add a retry button

#### 3.9 The "Calibration Card" Demo Is Not Demonstrable

You have calibration card detection (ISO ID-1 card, 85.60×53.98mm) for absolute font-size measurement. But CLAUDE.md §12 says: "None of the seven existing photos contains a calibration object."

**Quick fix:** Take one photo of a product label with a standard ID card (like an Aadhaar card, which is ID-1 format) placed next to it. When you scan this image, the system will detect the card, compute px-per-mm, and report font heights in absolute millimetres. This is a **wow moment** that demonstrates a unique capability.

#### 3.10 Fill in the Second Schedule Data

`second_schedule_sizes.json` only has biscuits. The file says `_status: PARTIAL_SOURCE`. If you transcribe even 2–3 more categories from the docx file in `research/`, the limitations page shows fewer gaps and the rule engine can enforce standard pack sizes for more product types.

#### 3.11 The Multi-Panel Scan Is Under-Demonstrated

You have a working multi-panel scan (`/api/v1/scans/multi`) that merges extractions from front/back/side panels with a confidence-based field merge. This is architecturally sophisticated. But:
- The scan detail page probably doesn't show "which panel provided which field"
- The `panel_sources` data is returned but may not be visualized

**If it's not visualized:** Add a small badge next to each extracted field showing which panel it came from. This shows judges that multi-panel scanning isn't just "multiple images" — it's intelligent field-level merging.

### 📊 Things to Highlight in the PPT

#### 3.12 The DSL Rule Engine Is Genuinely Innovative

Most teams will hardcode `if/elif` rules. You have:
- 29 rules defined in JSON with DSL conditions
- A safe interpreter with AST whitelisting (16 allowed functions, no eval/exec)
- A security test (`test_dsl_security.py`) that proves the DSL rejects dangerous inputs
- `effective_from` / `effective_to` on every rule

**This is publishable-quality work.** Emphasize it.

#### 3.13 SHA-256 Evidence Chain + BSA §63 Certificate

Your evidence chain is cryptographically verifiable. Every evidence item is hashed, the chain is append-only, and the PDF report carries a BSA Section 63 certificate with HMAC-SHA256 integrity signature. This is beyond what any SIH team will implement.

#### 3.14 The Dual-Pipeline Cross-Check

Pipeline A (RapidOCR, deterministic, offline) and Pipeline B (Claude Vision, probabilistic, API-based) running in parallel with a reconciliation layer that requires agreement for numeric legal fields — this is enterprise-grade architecture. Emphasize:
- "We don't trust any single AI model's reading of a legal number like MRP or net quantity"
- "Both pipelines must agree within tolerance, or the field routes to NEEDS_REVIEW"

#### 3.15 The "Reason to Believe" Gate

This is a legal requirement (Section 15(4), LM Act 2009) that you've implemented as a **hard gate** — both in the API (422 error) and the database. No inspector can advance a case without recording their reasoning. This is exactly what DPIIT would want.

### ❌ Known Gaps That Judges Might Ask About (Be Ready)

| Gap | Your Answer |
|---|---|
| "Can it detect counterfeit products?" | "This is a **compliance scanner**, not a counterfeit detector. It checks if a package label meets Legal Metrology Rules — missing MRP, wrong net quantity format, absent manufacturer address. Counterfeit detection is a different problem (brand-specific visual matching) and is a roadmap item." |
| "What about Hindi/regional language labels?" | "Our OCR is measured-accurate on English printed text. Hindi/Devanagari is a known limitation — we've documented it on the limitations page rather than hiding it. We have a synthetic test, and real bilingual photo testing is a data task, not a code task." |
| "Can it work offline?" | "Pipeline A (RapidOCR) runs fully offline — the ONNX models are bundled in the wheel. Pipeline B (Claude Vision) has a SHA-256 content cache, so once an image is scanned, the result is cached and future scans of the same image work offline. The rule engine itself is entirely offline." |
| "How does it scale?" | "The current prototype is on Render's free tier (512 MB). The architecture is stateless — any number of backend instances behind a load balancer, with Firestore as the shared state store. The rule engine is ~5ms per evaluation. The bottleneck is OCR (5–15s per image), which is CPU-bound and scales horizontally." |
| "What if the law changes?" | "Hot-swappable rules. Every rule has `effective_from`/`effective_to` dates. A legal officer updates the JSON file and hits the reload endpoint. No code deployment. Let me demonstrate..." |

---

## Part 4: Quick-Win Action Checklist

Ordered by impact-to-effort ratio:

| # | Action | Impact | Effort | Category |
|---|---|---|---|---|
| 1 | **Client-side image resize to 1280px before upload** | 🔴 Critical | ~1 hour | RAM + Speed |
| 2 | **Remove `_warm_ocr_engine()` from lifespan** (lazy-load) | 🔴 Critical | ~5 min | RAM |
| 3 | **Add `gc.collect()` at end of scan endpoints** | 🟡 High | ~5 min | RAM |
| 4 | **Add `--limit-concurrency 1` to Render start command** | 🟡 High | ~2 min | Stability |
| 5 | **Add backend health-check polling + wake-up screen** | 🟡 High | ~1 hour | UX |
| 6 | **Set up UptimeRobot or cron to ping /health every 10 min** | 🟡 High | ~10 min | UX |
| 7 | **Commit pre-populated vision cache for demo images** | 🟡 Medium | ~30 min | Speed |
| 8 | **Seed demo data into Firestore** | 🟡 Medium | ~1 hour | Demo |
| 9 | **Take one photo with calibration card** | 🟢 Medium | ~10 min | Demo wow-factor |
| 10 | **Fill 2–3 more Second Schedule categories** | 🟢 Medium | ~1 hour | Completeness |
| 11 | **Add XHR timeout (120s) with retry UI** | 🟢 Low | ~30 min | UX |
| 12 | **Client-side image quality warnings** | 🟢 Low | ~1–2 hours | UX |

---

## Part 5: What NOT to Change

> [!WARNING]
> Do not compromise these for speed or convenience:

1. **Don't skip Pipeline A for "faster" scans.** The dual-pipeline architecture is a key differentiator.
2. **Don't collapse NEEDS_REVIEW into PASS or FAIL.** The three-state verdict is legally defensible and a talking point.
3. **Don't remove the limitations page.** It's your credibility shield.
4. **Don't hardcode rules.** The DSL engine is the project's crown jewel.
5. **Don't remove the reason-to-believe gate.** It's the legal enforcement demo moment.
6. **Don't fabricate test results or accuracy numbers.** Your honest claims register (CLAUDE.md §11) is what makes the whole thing trustworthy. Judges can tell when numbers are invented.

---

## Part 6: Developer Context for Claude Code (Implementation Guide)

> **Note to Claude Code:** Read this section before implementing the checklist above. This contains verified architectural truths and file mappings established during deep analysis, saving you from re-reading the entire codebase or making incorrect assumptions.

### 1. Architectural Truths & Constraints
*   **Environment:** Python 3.13 on Windows 11. No GPU. Render deployment has a strict **512 MB RAM limit**.
*   **Dependencies:** We are using `rapidocr==3.9.2` because `rapidocr-onnxruntime` does not support Python 3.13. Do NOT attempt to swap to PaddleOCR (too large) or Tesseract (not installed).
*   **Encoding:** Windows console crashes on the `₹` symbol. `PYTHONUTF8=1` is required.
*   **Source of Truth:** The `research/` directory is READ-ONLY. Do not modify it. The rules JSON (`packages/rules/lmd_rules.v1.json`) is the canonical source for the DSL engine.

### 2. Implementation Coordinates for Quick Wins

**For Action 1 (Client-side Resize):**
*   **Files:** `frontend/src/lib/api.ts` (API client) and `frontend/src/components/scan/scan-upload-form.tsx` (Upload form).
*   **Context:** The API currently sends raw `File` objects directly. The backend expects a multipart form data payload with an `image` field. Add a resizing utility using `OffscreenCanvas` (cap at 1280px on the longest side) and encode to a JPEG `Blob` before appending to `FormData`. **Only do this for `image/jpeg` or `image/png`.**

**For Action 2 (Lazy-load OCR Engine):**
*   **File:** `backend/lmd/api/main.py`.
*   **Context:** Look for `_warm_ocr_engine()` inside the `_lifespan` context manager. Remove the call to `await asyncio.to_thread(_warm_ocr_engine)` and its import. This prevents ONNX sessions from allocating memory at boot.

**For Action 3 (Forced GC):**
*   **Files:** `backend/lmd/api/scan.py` and `backend/lmd/api/scan_multi.py`.
*   **Context:** `create_scan` and `create_multi_scan` endpoints create multiple large NumPy array copies. Add `import gc` and run `gc.collect()` at the very end of these endpoints right before returning the JSON dictionary to forcefully reclaim memory.

**For Action 4 (Render Concurrency Limit):**
*   **File:** `render.yaml`.
*   **Context:** The `startCommand` uses `uvicorn`. Append `--limit-concurrency 1` to ensure the server queues requests rather than processing two concurrent scans and OOMing.

**For Action 5 (Backend Wake-up UI):**
*   **Files:** `frontend/src/app/scan/page.tsx` or `frontend/src/components/scan/scan-upload-form.tsx`.
*   **Context:** The backend health endpoint is available via the Next.js proxy at `/api/lmd/health`. Use a polling loop to ping this (with a timeout) until it returns a 200 OK. Show a UI overlay ("Waking up server...") while polling.

### 3. Invariants to Respect
*   **Do not modify `ExtractionEnvelope`:** The shape is deeply tied to the DSL JSON rules.
*   **Do not change the three-state verdict logic:** `COMPLIANT / NON_COMPLIANT / NEEDS_REVIEW` must remain intact.
*   **No global image preprocessing:** Except for the specific glare masking stage.
