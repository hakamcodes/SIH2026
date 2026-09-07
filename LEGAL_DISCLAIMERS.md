# Legal Disclaimers

This document is the sitewide disclaimer text CLAUDE.md section 7 (invariant 13)
requires to be visible, not buried in a README. It should be surfaced in the
frontend on every page (not built in this pass) and is embedded in every
generated PDF report (`lmd.evidence.report_pdf`) and API response context.

## What this system is

An automated pre-screening signal for Legal Metrology (Packaged Commodities)
Rules, 2011 compliance, built for a Smart India Hackathon prototype (PS 26034).
It runs OCR and a deterministic rule engine over a photograph and produces an
advisory verdict for a human inspector to review.

## What this system is not, and never claims to be

- **Not a legal adjudication.** Only a Legal Metrology Officer may determine
  a violation and issue a notice. Every verdict is advisory.
- **Not a weighment device.** Actual net weight cannot be verified from a
  photograph. The system checks *declaration consistency* only (does the
  label say what it should, and is it internally consistent), never physical
  correctness against the First Schedule maximum permissible error.
- **Not proof of court-admissibility.** A generated PDF report carries a
  SHA-256 hash and a certificate under Section 63 of the Bharatiya Sakshya
  Adhiniyam 2023, making the record *certifiable*. Certifiable is not the
  same as automatically court-proven; admissibility is still a judicial
  determination.
- **Not a live eMaap integration.** Registration lookups and cross-state
  repeat-offender tracking are proposed roadmap architecture only. Nothing in
  this build queries eMaap or any government registry live.
- **Not a marketplace crawler.** This build scans one inspector-captured
  image at a time. Web/marketplace scraping, automated notice dispatch, and
  multi-state case federation are out of scope, roadmap-only, and not coded.
- **Not a font-compliance verifier without a calibration reference.**
  Absolute millimetre measurements (Rule 7) are only produced when an ID-1
  calibration card is visible in frame; otherwise `height_mm` is `null` and
  the system says so explicitly, rather than guessing a scale.
- **Not proven on dot-matrix or curved/cylindrical surfaces.** Measured
  accuracy on this repository's own sample photographs is zero text recovery
  on a rotated dot-matrix stamp and a curved jar. The system routes these to
  `NEEDS_REVIEW`, never `COMPLIANT`.
- **No accuracy percentage stated anywhere in this product is claimed
  without a labelled-set run in this repository backing it.**

## The reason-to-believe gate

Advancing a case to a confirmed-violation, escalated, or closed status
without a recorded reason-to-believe note is refused by both the database
(a CHECK constraint) and the API (HTTP 422), citing Section 15(4) of the
Legal Metrology Act 2009, read with the BNSS 2023: searches and seizures
require reasons to believe recorded in writing beforehand.
