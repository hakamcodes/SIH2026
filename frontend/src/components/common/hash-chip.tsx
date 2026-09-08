"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

import { abbreviateHash } from "@/lib/format";
import { cn } from "@/lib/utils";

/** A SHA-256 (or HMAC) hex string, abbreviated, monospaced, click-to-copy.
 *  Used for image_sha256, document_sha256, evidence sha256_hash and
 *  certificate hmac_signature everywhere they appear. */
export function HashChip({
  hash,
  label,
  className,
}: {
  hash: string;
  label?: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(hash);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard permission denied is not worth surfacing as an error.
    }
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      title={hash}
      aria-label={`Copy ${label ?? "hash"} ${hash}`}
      className={cn(
        "inline-flex min-h-8 items-center gap-1.5 rounded-sm border border-border bg-surface-subtle px-2 font-mono text-2xs text-fg-muted transition-colors duration-[var(--dur-fast)] hover:border-border-strong hover:text-foreground",
        className,
      )}
    >
      {label && <span className="text-fg-subtle">{label}</span>}
      <span>{abbreviateHash(hash)}</span>
      {copied ? (
        <Check className="size-3 shrink-0 text-[var(--conf-high)]" aria-hidden="true" />
      ) : (
        <Copy className="size-3 shrink-0" aria-hidden="true" />
      )}
    </button>
  );
}
