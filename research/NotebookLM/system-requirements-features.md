# Government of India
## Department of Consumer Affairs
### Legal Metrology Enforcement Division

# SYSTEM REQUIREMENTS & TECHNICAL FEATURES SPECIFICATION
**Document Identifier:** LMD-SR-2026-V1.0  
**Effective Date:** September 6, 2026  
**Status:** Implementation-Ready Specification  

---

## 1. System Architecture Overview
This document specifies the technical requirements for the automated visual analysis pipeline and compliance processing engine for **SIH Problem Statement 2634** [49]. The system must operate as a hybrid, deterministic-semantic pipeline to ensure both legal reproducibility and robust error handling [54].

---

## 2. Recommended Image-Processing Pipeline (8-Stage Architecture)
A global, single-threshold preprocessing approach fails on real product packaging due to busy backgrounds, holographic security seals, and complex geometries [52, 58]. The system must implement the following 8-stage image-processing pipeline [51]:

```
+--------------------------------------------------------------------------------------------------------------------+
| STAGE 1: Capture-Time Constraints                                                                                  |
| • Require multi-shot capture: front Principal Display Panel (PDP) + all side panels [51].                         |
| • Require reference calibration card/ArUco marker in frame [51].                                                   |
| • Reject frame if Estimated Sharpness (Laplacian variance) < threshold or if Resolution < 1080p [51].               |
+--------------------------------------------------------------------------------------------------------------------+
                                                         │
                                                         ▼
+--------------------------------------------------------------------------------------------------------------------+
| STAGE 2: Package/Panel Localization                                                                                |
| • Segment package boundaries using YOLOv8-Pose/Segmentation to isolate package from hand or background [51].      |
| • Classify panel in view: front (PDP), side ingredient panel, or side declaration panel [51].                      |
+--------------------------------------------------------------------------------------------------------------------+
                                                         │
                                                         ▼
+--------------------------------------------------------------------------------------------------------------------+
| STAGE 3: Geometric Correction                                                                                      |
| • Homography matrix calculation for flat panels captured at an angle [51].                                         |
| • Cylindrical/conic unwarp mapping for curved bottles, jars, and metal cans [51].                                  |
| • Skew correction based on text-line angle estimation [51].                                                        |
+--------------------------------------------------------------------------------------------------------------------+
                                                         │
                                                         ▼
+--------------------------------------------------------------------------------------------------------------------+
| STAGE 4: Local (Not Global) Image Enhancement                                                                      |
| • Specular-highlight detection (glare) -> mask out or flag glare regions to prevent false characters [51, 62].    |
| • Region-local adaptive binarization (Sauvola/Niblack) applied only *after* cropping to text blocks [51, 52].      |
| • Selective super-resolution (ESRGAN-Light) on low-res text-bearing patches [51].                                 |
+--------------------------------------------------------------------------------------------------------------------+
                                                         │
                                                         ▼
+--------------------------------------------------------------------------------------------------------------------+
| STAGE 5: Text Detection                                                                                            |
| • Polygon-based text detection (CRAFT/DBNet) to handle rotated, curved, or flexible-pouch text [51].               |
| • Separate detection pass for dot-matrix/inkjet batch-code regions (different visual signature) [51].             |
+--------------------------------------------------------------------------------------------------------------------+
                                                         │
                                                         ▼
+--------------------------------------------------------------------------------------------------------------------+
| STAGE 6: Text Recognition                                                                                          |
| • Primary Engine: PaddleOCR (PP-OCRv4) with Devanagari (Hindi) and Latin (English) models [53].                   |
| • Fallback Engine: Tesseract 5.3.4 (English + Hindi trained models) [53].                                          |
| • Specialized dot-matrix classifier (CNN) for batch, date, and price stamps [51, 60].                              |
| • Script router: Send Devanagari-script regions to Hindi model, English-script regions to English model [51].      |
+--------------------------------------------------------------------------------------------------------------------+
                                                         │
                                                         ▼
+--------------------------------------------------------------------------------------------------------------------+
| STAGE 7: Structuring & Measurement                                                                                 |
| • Convert bounding boxes -> font height in mm based on pixels-per-millimeter calibration card [51, 66].            |
| • Spacing/placement and fold-crossing layout analysis [51, 70].                                                    |
+--------------------------------------------------------------------------------------------------------------------+
                                                         │
                                                         ▼
+--------------------------------------------------------------------------------------------------------------------+
| STAGE 8: Handoff to Rule Engine                                                                                    |
| • Standardized JSON serialization with confidence scores, coordinates, and raw texts handoff [51].                |
+--------------------------------------------------------------------------------------------------------------------+
```

---

## 3. Recommended OCR / Model Recommendation
To balance high accuracy, repeatability, and legal defensibility, the system must employ a **Two-Pipeline Hybrid Architecture** [54]:

| Model Class | Recommended Technology | Specific Role in System | Performance Trade-off & Justification |
| :--- | :--- | :--- | :--- |
| **Deterministic OCR** [53] | **PaddleOCR (PP-OCRv4/v5)** [53] | Primary engine for character bounding box detection, layout analysis, font-size extraction, and language script-routing [54]. | Highly deterministic, reproducible, runs locally on offline servers, provides precise pixel bounding boxes [53, 54]. |
| **Fallback Engine** [53] | **Tesseract 5.3.4** [53] | Runs in parallel or as fallback when PaddleOCR confidence drops [53, 54]. | Solid baseline for clean, flat text; weak on curves/rotations unless pre-corrected [53]. |
| **Semantic Cross-Checker** [53] | **Vision-Capable LLM** (e.g., Gemini Flash / GPT-4V class) [53] | Jointly reads and semantic-structures fields (e.g., identifying MRP value and generic name) to check against OCR outputs [53, 54]. | **Non-deterministic.** May hallucinate numbers, but excellent at resolving messy layouts [53, 54]. Must *never* be the sole source of truth [53]. |

### The Uncertainty Handshake Rule (LM-U02)
The system must never auto-average or auto-resolve numerical discrepancies between the Deterministic OCR pipeline and the Semantic LLM pipeline [54, 84]. If the extracted values disagree beyond a tight tolerance (e.g., OCR reads MRP as ₹299, LLM reads ₹290), the system must raise an **LM-U02** exception and route the SKU to the **NEEDS_REVIEW** queue for manual inspection [54, 84, 89].

---

## 4. Font-Size Measurement Methodology (Pixels to Millimeters)
The system must convert bounding box heights from pixels into millimeters to verify compliance with **Rule 7** [66]:

### 4.1 Establishing Pixels-per-Millimeter (px/mm)
The system must calculate `px_per_mm` using one of three hierarchical methods [66]:
1. **Reference Card contour (Primary):** The mobile capture app forces the user to place a standard ISO/ID-1 credit/ID card (85.60 mm wide) in frame [66]. The contour detector extracts its pixel width:
   $$\text{px\_per\_mm} = \frac{\text{detected\_card\_width\_px}}{85.60}$$
2. **Fixed-Distance Pinhole Model (Secondary):** If depth sensors (ARKit/ARCore) are available, calculate scale from focal length:
   $$\text{px\_per\_mm} = \frac{\text{focal\_length\_px} \times \text{real\_world\_size\_mm}}{\text{distance\_mm}}$$
3. **No Reference Available (Fallback):** The system cannot calculate physical millimeters. It **must** output `font_height_mm = null` and flag `needs_review = true` [66]. It must *never* guess the scale [66].

### 4.2 Ink-Only Character Height vs. Bounding Box Height
Standard OCR bounding boxes include font leading and ascender-descender padding, leading to false-positive passes [67]. The system must measure the **character height** by analyzing the local binarized character block:
1. Extract the cropped text bounding box.
2. Generate a row-wise horizontal projection profile: calculate the count of black (ink) pixels per row.
3. Establish the first row $R_{\text{start}}$ and last row $R_{\text{end}}$ where the pixel density exceeds a threshold (e.g., $2\%$ of row width) [67].
4. Compute ink-only height:
   $$\text{ink\_height\_px} = R_{\text{end}} - R_{\text{start}}$$
5. Convert to physical units:
   $$\text{font\_height\_mm} = \frac{\text{ink\_height\_px}}{\text{px\_per\_mm}}$$

---

## 5. Placement & Spacing Layout Detection Heuristics
Compliance with placement regulations is handled as a **layout analysis problem** on the extracted bounding boxes [69]:

1. **Line Clustering:** Group bounding boxes whose vertical coordinate ranges overlap by $> 50\%$ into a single horizontal text line [70].
2. **Block paragraph Clustering:** Group consecutive lines into a block when the vertical gap between lines is $< 1.5\times$ the median line height [70].
3. **Declaration-Block Identification:** While marketing text is large and sparse ($40\text{--}60\text{ px}$), regulatory declarations are dense and small ($23\text{--}39\text{ px}$) [70]. The system ranks blocks by:
   $$\text{Block Score} = \text{Box Density} \times \left(\frac{1}{\text{Average Box Height}}\right)$$
   The highest-scoring block is classified as the **LMPC Declaration Block** [70].
4. **Fold and Crease Bisection Checking:** Run a Hough Transform on high-gradient lines across flexible packaging [70]. If any detected text bounding box is bisected by a crease line, flag the field as a **MAJOR** violation for obscured legibility [70].

---

## 6. Resolving Specific Technical Edge-Cases
Developers must integrate dedicated modules to handle the following high-risk failure points:

### 6.1 Dot-Matrix Inkjet Batch Codes
* **The Problem:** Batch numbers, manufacturing dates, and MRP stamps on flexible pouches are printed using inkjet dot-matrix printers [56, 59]. Because these characters consist of a constellation of discrete dots rather than continuous strokes, general OCR models (Tesseract/PaddleOCR) fail completely (returning empty strings or garbled noise) [59, 60].
* **The Solution:**
  1. Train a dedicated YOLOv8-Object-Detector to localize the "Batch Stamp Region" [51].
  2. Apply a morphological **Closing** operation (dilation followed by erosion) using a horizontal-line structuring element to merge discrete dots into continuous strokes [59].
  3. Pass the merged glyphs through a lightweight, custom CNN character classifier trained specifically on dot-matrix digits, slashes, and month abbreviations [60].

### 6.2 Specular Glare and Holographic Seals
* **The Problem:** Specular glare from plastic wrapping or holographic security stickers generates high-luminance, high-contrast regions [56, 62]. Binarization engines interpret these shapes as characters, producing false-positive text boxes with high "confidence" [62].
* **The Solution:** Stage 4 must run a luminance-masking pass:
  $$\text{Glare Mask} = \text{Gray Image} > 250\text{ (for 8-bit channels)}$$
  Any text detections falling within a glare region are suppressed or flagged as `NEEDS_REVIEW`, preventing false-positive violations [62].

### 6.3 Hindi (Devanagari) Numeral Loss
* **The Problem:** Testing shows Hindi script engines (Tesseract `hin`) recognize Devanagari characters and conjuncts very well, but frequently scramble or drop the accompanying embedded numerals (e.g., misreading currency ₹100 as ₹00, or scrambling phone digits) [63, 64].
* **The Solution:** Enforce separate confidence gating [64]. If a Devanagari text line contains numerical fields (price, dates, or contact numbers), apply a **digit-only parser** (trained on Devanagari digits $\circ, \text{१}, \text{२}, \text{३}, \text{४}, \text{५}, \text{६}, \text{७}, \text{८}, \text{९}$ and Latin digits) to process the numerical bounding boxes independently, rather than trusting the global line-level script engine [64].
