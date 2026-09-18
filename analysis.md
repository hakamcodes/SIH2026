# SIH2634 Prototype — Deep Analysis

---

## 1. 🧠 How the Current Prototype Works (Simple Language)

Think of it like a **smart inspector assistant**. When a package photo is uploaded, it goes through this exact chain:

```
Photo → OCR reads text → AI cross-checks → Rules checked → Verdict → PDF Report
```

### Step-by-step:

**Step 1 — Upload**
Inspector uploads a photo of a packaged product (biscuit packet, juice box, etc.) via the web app.

**Step 2 — Pipeline A (Local OCR — always runs)**
- First checks if there is an ID-1 calibration card in frame (for measuring font size in mm).
- Removes glare from the image (the ONLY global edit it makes).
- Runs **RapidOCR** — a fully offline AI OCR engine — to detect and read all text boxes.
- Any text box read with low confidence is re-read after local enhancement; the better result wins.
- A regex parser then turns raw OCR lines into structured fields: MRP, net quantity, manufacturer name, manufacturing date, best-before date, country of origin, consumer care number, etc.

**Step 3 — Pipeline B (Cloud AI Cross-check — optional)**
- Sends the same photo to Claude (Anthropic's vision AI).
- Asks it to extract the same fields independently.
- Result is cached locally by image hash — so demos work offline after the first run.

**Step 4 — Reconciliation (Merge)**
- The two pipelines' results are merged with a trust ladder:
  - OCR's own parsed value wins first.
  - If OCR didn't parse it but the AI found it AND an OCR line confirms it → accepted at medium confidence.
  - If only the AI found it, it's recorded but flagged as low-confidence (can never produce a COMPLIANT verdict alone).
- For numbers (MRP, net qty): both pipelines must *agree within tolerance* to be trusted. If they disagree → routed to **NEEDS_REVIEW**.

**Step 5 — Rule Engine (29 rules from a JSON file)**
- Runs all 29 legal rules (from `lmd_rules.v1.json`) against the extracted data.
- Rules cover: are all mandatory declarations present? Is MRP printed correctly? Is net quantity consistent? Is the pack size from the Second Schedule? etc.
- Every rule has an effective-date range — old rules (pre-2012, pre-2022) are automatically skipped.
- Output: per-rule PASS / FAIL / REVIEW / NOT_APPLICABLE.

**Step 6 — Verdict**
- Three possible outcomes: **COMPLIANT**, **NON_COMPLIANT**, or **NEEDS_REVIEW**.
- NON_COMPLIANT always beats NEEDS_REVIEW, which always beats COMPLIANT. No hiding failures.

**Step 7 — Annotated Overlay + Case**
- An annotated image is generated with colored boxes (green = high confidence, red = low).
- A Case is created in the local SQLite DB.

**Step 8 — Inspector Review + Reason-to-Believe Gate**
- Inspector MUST type a written reason before advancing the case (Section 15(4) Legal Metrology Act 2009). This is enforced at the database AND API level — you literally cannot skip it.

**Step 9 — Signed PDF Report**
- A PDF is generated with all evidence, rule verdicts, legal citations, and a SHA-256 hash chain.
- A Section 63 BSA 2023 certificate is attached, making the record "certifiable" (not automatically court-admissible, but legitimately certifiable).

---

## 2. 🔥 Why It Uses >512 MB RAM (Render Free Tier Crash)

There are **4 compounding reasons**, all happening at the same time:

### Reason 1 — ONNX Runtime + RapidOCR model weight loading (~200-350 MB)
`rapidocr==3.9.2` bundles three ONNX neural network model files **inside the wheel**:
- `PP-OCRv6_det_small.onnx` — text detection model
- `PP-OCRv6_rec_small.onnx` — text recognition model
- A classifier model

Each ONNX model loads into RAM as a full floating-point array. Even the "small" variants use 150-300 MB together. `onnxruntime` itself adds another ~50 MB of DLL/library footprint.

### Reason 2 — OpenCV image decoding (can be 10-50 MB per image)
```python
cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
```
A 2MB JPEG uploaded expands to a raw numpy BGR array in RAM. A 4MP photo (typical phone) = 4,000,000 × 3 bytes = ~12 MB. A 12MP photo = ~36 MB. Multiple copies are created during glare masking, ROI crops, overlay rendering, and PNG encoding — easily 100-200 MB peak for a single image.

### Reason 3 — No image resizing before processing
There is **zero image downscaling** before feeding into OCR. If the user uploads a 12MP phone photo, RapidOCR processes the full-resolution image. OCR on a 12MP image is orders of magnitude more expensive than on a 1MP image — and legal text on a package is still readable at 1MP.

### Reason 4 — Anthropic SDK + model payload in same process
```python
import anthropic  # local import inside pipeline_b
```
The Anthropic SDK loads into the same Python process. When an image is base64-encoded and sent to the API:
```python
image_b64 = base64.b64encode(image_bytes).decode("ascii")
```
A 3MB image becomes ~4MB base64 string, plus the full JPEG bytes are still in RAM. Total: original bytes + numpy array + base64 string + SDK overhead.

### Net Effect
| Component | RAM |
|---|---|
| ONNX runtime + RapidOCR models | ~200-350 MB |
| OpenCV image arrays (original + copies) | ~50-200 MB |
| Anthropic SDK + base64 payload | ~30-80 MB |
| Python + FastAPI + Pydantic + ReportLab | ~50-80 MB |
| **Total worst case** | **~500-700 MB** |

Render's free tier is 512 MB hard limit → OOM kill. This is a real architectural issue, not a configuration problem.

---

## 3. 🏆 What to Add / Improve for SIH Winning Prototype

### A. Multiple Images for One Scan (Front + Back + Side)
Currently one image per scan. Real packages need multiple sides.

**What to build:**
- Accept multiple images per scan (front panel, back panel, nutritional panel, side)
- Run Pipeline A on all images and merge the extracted fields (union across panels, higher confidence wins per field)
- Show which field came from which image in the overlay
- This alone dramatically improves extraction accuracy because the manufacturer address is usually on the back, MRP is on the front, best-before is on the bottom

### B. Single Product / Single Field Focus Mode
An inspector who already knows the product can tell the system "just check the MRP on this image."

**What to build:**
- A field-focus mode: inspector selects which declaration(s) to verify
- System runs only the relevant rules, gives a fast targeted verdict
- Useful for spot-checks at a market/shop vs. full compliance audit

### C. Direct Camera Capture (Live Capture Mode)
Currently only supports file upload. For field use (inspector at a shop), live camera is essential.

**What to build:**
- Use browser `MediaDevices.getUserMedia()` — works on any modern phone/tablet browser, no app install needed
- Add a "Capture" button on the scan page
- Add autofocus guidance: "Hold steady — detecting text..." (use canvas + OCR feedback loop)
- Optional: add a "Place ID-1 card in frame" guide overlay to enable font-size measurement

### D. Barcode / QR Code Scan for Product Identity
Link the scan to a known product in a database.

**What to build:**
- Use `jsQR` or ZXing in the browser to decode any barcode in the camera feed
- Look up the product by barcode in a local product DB
- Pre-fill commodity category and subtype (which the inspector currently has to type manually)
- Can also detect if the barcode on the package matches the declared product

### E. Hindi / Bilingual Package Support (Real, Not Synthetic)
Currently only tested on English text. Real Indian packages are bilingual.

**What to build:**
- Photograph one real Hindi-English package (per the CLAUDE.md §12 outstanding task)
- Measure actual RapidOCR accuracy on Devanagari — it may already work on real photos vs. the synthetic render currently tested
- If Devanagari OCR fails on numbers (documented issue: `₹100` → `₹]00`), explicitly gate numeric fields from Devanagari lines and fall back to Pipeline B for those

### F. Offline / PWA Mode for Field Inspectors
Inspectors in markets often have poor connectivity.

**What to build:**
- Service Worker to cache the web app shell
- Run Pipeline A (RapidOCR, ONNX) entirely in Python backend — keep it local when on intranet
- Cache the rule JSON + second schedule JSON client-side
- Queue scans for upload when connectivity returns

### G. Complete the Second Schedule (all 7 commodity categories)
Currently only biscuits are encoded in `second_schedule_sizes.json`. This means LM-M04a (pack size BLOCKER) only works for biscuits.

**What to add:** bread, milk powder, soaps, detergent, paints, cement, rice, edible oil, bottled water sizes from the gazette. This turns a partial rule into a fully enforced one — **big impact for SIH judges**.

### H. Comparison / Trend Dashboard
Judges love data. Add a meaningful dashboard beyond just counters.

**What to build:**
- Top failing rules by frequency (which rule fails most?)
- Compliance rate by product category
- Timeline of scans (when were most non-compliant products found?)
- Most common missing declarations

### I. Inspector Mobile UI
The frontend is Next.js (browser-based). Make it genuinely usable on a phone.

**What to build:**
- Responsive design optimized for mobile viewport
- Large tap targets for case review actions
- The camera capture feature above is the gateway to this

---

## 4. ⚡ How to Make It Actually Optimized (Usable)

### Fix 1 — Resize images before OCR (biggest single win)
```python
# Add this in scan.py BEFORE run_pipeline_a()
MAX_DIM = 1280  # px — legal text is fully readable at this resolution
h, w = cv_image.shape[:2]
if max(h, w) > MAX_DIM:
    scale = MAX_DIM / max(h, w)
    cv_image = cv2.resize(cv_image, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)
```
This alone cuts RAM from ~200 MB to ~20 MB for the image arrays, and makes OCR 4-10x faster. Text on labels is still fully readable. Do this everywhere — before Pipeline A, before overlay generation, before PNG encoding.

### Fix 2 — Load ONNX models once at startup, not per-request
Currently uses `@lru_cache(maxsize=1)` which is good, but the first request is always slow. Fix: **pre-load on startup** using FastAPI's `lifespan`:
```python
@asynccontextmanager
async def lifespan(app):
    _get_engine()  # pre-warm RapidOCR ONNX models
    yield
```
This amortizes the 2-3 second startup cost and prevents a cold-start timeout on Render.

### Fix 3 — Run Pipeline A and Pipeline B in parallel (async)
Currently Pipeline B runs after Pipeline A finishes:
```python
pipeline_a_result = run_pipeline_a(cv_image)  # blocking
vision_fields = _maybe_run_pipeline_b(image_bytes)  # blocking, after A finishes
```
Pipeline B is a network call to Anthropic — it's I/O bound. Run it concurrently with Pipeline A using `asyncio.gather()` or `concurrent.futures.ThreadPoolExecutor`. This cuts end-to-end latency by 40-60%.

### Fix 4 — Stream the overlay image, don't keep it in RAM
Currently the overlay is a full decoded numpy array in RAM during rendering. Write it to disk immediately after encoding:
```python
overlay_image = render_overlay(cv_image, ...)  # ~same size as original in RAM
encode_png(overlay_image)  # another copy
```
After encoding to bytes, explicitly `del overlay_image` to free the numpy array.

### Fix 5 — Use a proper production server (gunicorn + uvicorn workers)
On Render (or any cloud), do not run with `--reload`. Use:
```
gunicorn lmd.main:app -k uvicorn.workers.UvicornWorker -w 1 --max-requests 100 --max-requests-jitter 20
```
`--max-requests 100` restarts the worker every 100 requests, which flushes any memory fragmentation. `--max-requests-jitter` prevents all workers restarting at once.

### Fix 6 — Move to PostgreSQL from SQLite for concurrent access
The current store uses SQLite (`data/lmd.db`). SQLite has write serialization — only one scan can be written at a time. PostgreSQL handles concurrent scans properly and Render offers a free tier PostgreSQL. DDL is already written: `backend/lmd/store/ddl_postgres.sql` exists.

### Fix 7 — Add response caching for the rules endpoint
The `/api/v1/rules` endpoint loads the full `lmd_rules.v1.json` on every request. Add an HTTP `Cache-Control: max-age=3600` header or cache the parsed rules in memory (they already are — just expose that). Saves ~10 MB per rules endpoint call.

### Fix 8 — Compress uploaded images before storing
```python
# Instead of writing raw uploaded bytes:
image_path.write_bytes(image_bytes)
# Re-encode at reduced quality (still fully readable for legal purposes):
success, compressed = cv2.imencode('.jpg', cv_image, [cv2.IMWRITE_JPEG_QUALITY, 75])
if success:
    image_path.write_bytes(compressed.tobytes())
```
Reduces storage from ~3MB per upload to ~400-600KB. On a free-tier server with limited disk, this matters.

---

## Summary Table

| Issue | Impact | Effort |
|---|---|---|
| Image resize before OCR | 🔥 Fixes OOM crash | Low |
| Pre-warm ONNX at startup | ⚡ Faster first request | Low |
| Parallel Pipeline A + B | ⚡ 40-60% faster | Medium |
| Multi-image scan | 🏆 SIH differentiator | High |
| Camera capture in browser | 🏆 SIH differentiator | Medium |
| Complete Second Schedule | 🏆 Legal completeness | Low |
| Hindi real photo testing | 🏆 Credibility | Low |
| Barcode lookup | 🏆 WOW factor | Medium |
| Mobile-first UI | 🏆 Practical usability | Medium |
| PostgreSQL migration | 🔒 Production-ready | Medium |
