"use client";

import { useState } from "react";
import { ShieldAlert } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { CaseStatusBadge } from "@/components/common/status-badge";
import { useInspector } from "@/components/shell/inspector-provider";
import { updateCase } from "@/lib/api";
import { describeUnknownError, isApiError } from "@/lib/errors";
import { REASON_TO_BELIEVE_EXPLANATION } from "@/lib/disclaimers";
import type { CaseStatus } from "@/lib/types";

interface ReasonToBelieveDialogProps {
  caseId: string;
  targetStatus: CaseStatus;
  onClose: () => void;
  onSuccess: () => void;
}

/**
 * Deliberately does NOT disable the confirm action when the note is empty.
 * Submitting an empty note is the point: it proves the 422 hard gate is real
 * server-side enforcement (sqlite CHECK constraint + API), not a client-side
 * courtesy the UI could be tricked into skipping. The server's own
 * `legal_basis` string is rendered verbatim rather than a paraphrase.
 */
export function ReasonToBelieveDialog({
  caseId,
  targetStatus,
  onClose,
  onSuccess,
}: ReasonToBelieveDialogProps) {
  const { inspector } = useInspector();
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [gateMessage, setGateMessage] = useState<{ detail: string; legalBasis?: string } | null>(
    null,
  );
  const [otherError, setOtherError] = useState<string | null>(null);

  async function handleConfirm() {
    if (!inspector) return;
    setSubmitting(true);
    setGateMessage(null);
    setOtherError(null);
    try {
      await updateCase(caseId, { status: targetStatus, reasonToBelieveNote: note }, inspector.inspectorId);
      toast.success(`Case moved to ${targetStatus.replace("_", " ").toLowerCase()}`);
      onSuccess();
    } catch (err) {
      if (isApiError(err) && err.kind === "reason_to_believe_required") {
        setGateMessage({ detail: err.message, legalBasis: err.legalBasis });
      } else {
        setOtherError(describeUnknownError(err));
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShieldAlert className="size-4 text-[var(--sev-blocker)]" aria-hidden="true" />
            Reason to believe
          </DialogTitle>
          <DialogDescription>
            Moving this case to <CaseStatusBadge status={targetStatus} size="sm" /> requires a
            recorded reason-to-believe note. {REASON_TO_BELIEVE_EXPLANATION}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="rtb-note">Reason to believe note</Label>
          <Textarea
            id="rtb-note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="e.g. Physical inspection confirms MRP declaration missing from the front panel."
            rows={4}
          />
          <p className="text-xs text-fg-subtle">
            Leaving this blank and confirming anyway demonstrates the server-side gate — it will
            refuse the request rather than silently accepting an empty note.
          </p>
        </div>

        {gateMessage && (
          <div className="rounded-md border border-[var(--verdict-non-compliant-border)] bg-[var(--verdict-non-compliant-bg)] p-3">
            <p className="text-sm font-medium text-[var(--verdict-non-compliant-fg)]">
              422 — request refused by the server
            </p>
            <p className="mt-1 text-sm text-foreground">{gateMessage.detail}</p>
            {gateMessage.legalBasis && (
              <p className="mt-1.5 font-mono text-xs text-fg-muted">{gateMessage.legalBasis}</p>
            )}
          </div>
        )}
        {otherError && (
          <p className="text-xs text-[var(--verdict-non-compliant-fg)]">{otherError}</p>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={submitting}>
            {submitting ? "Submitting…" : "Confirm"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
