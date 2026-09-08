import Link from "next/link";
import { Info } from "lucide-react";

import { SITEWIDE_DISCLAIMER } from "@/lib/disclaimers";

/**
 * Rendered in the root layout, so it is present on every page. CLAUDE.md
 * invariant 13 requires this to be visible sitewide rather than buried, and
 * LEGAL_DISCLAIMERS.md is the source of the wording.
 *
 * Deliberately not dismissible: a disclaimer an inspector can close is a
 * disclaimer that is absent on the screenshot that ends up in a case file.
 */
export function AdvisoryBanner() {
  return (
    <div className="border-b border-border bg-surface-subtle">
      <div className="mx-auto flex max-w-[var(--content-max)] items-start gap-2 px-4 py-2 sm:items-center">
        <Info
          className="mt-0.5 size-3.5 shrink-0 text-fg-subtle sm:mt-0"
          aria-hidden="true"
        />
        <p className="text-xs text-fg-muted">
          {SITEWIDE_DISCLAIMER}{" "}
          <Link
            href="/limitations"
            className="text-link underline underline-offset-2 hover:text-link-hover"
          >
            Known limitations
          </Link>
        </p>
      </div>
    </div>
  );
}
