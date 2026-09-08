/**
 * Text transcribed verbatim from LEGAL_DISCLAIMERS.md at the repository root,
 * which requires this to be "surfaced in the frontend on every page" rather
 * than buried in a README (CLAUDE.md invariant 13).
 *
 * Do not soften, shorten or paraphrase these strings to fit a layout.
 */

export const SITEWIDE_DISCLAIMER =
  "Advisory pre-screening signal only. Only a Legal Metrology Officer may determine a violation and issue a notice.";

export const WHAT_THIS_SYSTEM_IS =
  "An automated pre-screening signal for Legal Metrology (Packaged Commodities) Rules, 2011 compliance. It runs OCR and a deterministic rule engine over a photograph and produces an advisory verdict for a human inspector to review.";

export interface DisclaimerItem {
  title: string;
  detail: string;
}

/** The eight "what this system is not" bullets, LEGAL_DISCLAIMERS.md §"What
 *  this system is not, and never claims to be". */
export const NOT_CLAIMS: DisclaimerItem[] = [
  {
    title: "Not a legal adjudication",
    detail:
      "Only a Legal Metrology Officer may determine a violation and issue a notice. Every verdict is advisory.",
  },
  {
    title: "Not a weighment device",
    detail:
      "Actual net weight cannot be verified from a photograph. The system checks declaration consistency only — does the label say what it should, and is it internally consistent — never physical correctness against the First Schedule maximum permissible error.",
  },
  {
    title: "Not proof of court-admissibility",
    detail:
      "A generated PDF report carries a SHA-256 hash and a certificate under Section 63 of the Bharatiya Sakshya Adhiniyam 2023, making the record certifiable. Certifiable is not the same as automatically court-proven; admissibility is still a judicial determination.",
  },
  {
    title: "Not a live eMaap integration",
    detail:
      "Registration lookups and cross-state repeat-offender tracking are proposed roadmap architecture only. Nothing in this build queries eMaap or any government registry live.",
  },
  {
    title: "Not a marketplace crawler",
    detail:
      "This build scans one inspector-captured image at a time. Web/marketplace scraping, automated notice dispatch, and multi-state case federation are out of scope, roadmap-only, and not coded.",
  },
  {
    title: "Not a font-compliance verifier without a calibration reference",
    detail:
      "Absolute millimetre measurements (Rule 7) are only produced when an ID-1 calibration card is visible in frame; otherwise height_mm is null and the system says so explicitly, rather than guessing a scale.",
  },
  {
    title: "Not proven on dot-matrix or curved/cylindrical surfaces",
    detail:
      "Measured accuracy on this repository's own sample photographs is zero text recovery on a rotated dot-matrix stamp and a curved jar. The system routes these to NEEDS_REVIEW, never COMPLIANT.",
  },
  {
    title: "No unbacked accuracy percentage",
    detail:
      "No accuracy percentage stated anywhere in this product is claimed without a labelled-set run in this repository backing it.",
  },
];

export const REASON_TO_BELIEVE_BASIS = "Section 15(4), Legal Metrology Act 2009";

export const REASON_TO_BELIEVE_EXPLANATION =
  "Advancing a case to a confirmed-violation, escalated, or closed status without a recorded reason-to-believe note is refused by both the database (a CHECK constraint) and the API (HTTP 422), citing Section 15(4) of the Legal Metrology Act 2009, read with the BNSS 2023: searches and seizures require reasons to believe recorded in writing beforehand.";

export const NO_CALIBRATION_REASON = "no_calibration_reference_in_frame";

export const NO_CALIBRATION_MESSAGE =
  "No ID-1 calibration card was detected in frame, so absolute millimetre character heights cannot be measured. Relative height ratios remain valid; Rule 7 compliance is not asserted.";
