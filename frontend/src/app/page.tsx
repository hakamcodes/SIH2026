"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Scale, ShieldAlert } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useInspector } from "@/components/shell/inspector-provider";
import { SITEWIDE_DISCLAIMER, WHAT_THIS_SYSTEM_IS } from "@/lib/disclaimers";

/**
 * Not a login screen. The backend has no authentication endpoint at all
 * (backend/lmd/api/deps.py): every write request carries a single shared
 * bearer token held server-side, plus an `X-Inspector-Id` header that is
 * caller-asserted and used only as the audit-log actor. This form collects
 * that identity string and nothing else -- it must never imply a verified
 * sign-in.
 */
export default function IdentityPage() {
  const router = useRouter();
  const { inspector, signIn } = useInspector();

  const [name, setName] = useState(inspector?.name ?? "");
  const [designation, setDesignation] = useState(inspector?.designation ?? "");
  const [inspectorId, setInspectorId] = useState(inspector?.inspectorId ?? "");

  const canContinue = name.trim() !== "" && inspectorId.trim() !== "";

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!canContinue) return;
    signIn({
      name: name.trim(),
      designation: designation.trim() || "Legal Metrology Officer",
      inspectorId: inspectorId.trim(),
    });
    router.push("/scan");
  }

  return (
    <div className="flex flex-1 items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="flex size-10 items-center justify-center rounded-md border border-border bg-surface-subtle">
            <Scale className="size-5 text-foreground" aria-hidden="true" />
          </div>
          <h1 className="mt-4 text-lg font-semibold tracking-tight">
            Legal Metrology Compliance Scanner
          </h1>
          <p className="mt-1 text-xs text-fg-subtle">SIH Problem Statement 26034</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-4 rounded-md border border-border bg-surface p-5"
        >
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Anita Verma"
              autoComplete="off"
              required
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="designation">Designation</Label>
            <Input
              id="designation"
              value={designation}
              onChange={(e) => setDesignation(e.target.value)}
              placeholder="Legal Metrology Officer"
              autoComplete="off"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="inspector-id">Inspector ID</Label>
            <Input
              id="inspector-id"
              value={inspectorId}
              onChange={(e) => setInspectorId(e.target.value)}
              placeholder="e.g. lmo-anita-verma"
              autoComplete="off"
              className="font-mono text-sm"
              required
            />
            <p className="text-xs text-fg-subtle">
              Sent as <code className="font-mono">X-Inspector-Id</code> on every
              case action you take. Not verified against a user directory —
              there isn&apos;t one in this build.
            </p>
          </div>

          <Button type="submit" disabled={!canContinue} className="mt-1 gap-1.5">
            Continue
            <ArrowRight className="size-3.5" aria-hidden="true" />
          </Button>
        </form>

        <div className="mt-4 flex items-start gap-2 rounded-md border border-border bg-surface-subtle p-3">
          <ShieldAlert
            className="mt-0.5 size-3.5 shrink-0 text-fg-subtle"
            aria-hidden="true"
          />
          <p className="text-xs text-fg-muted">
            {SITEWIDE_DISCLAIMER} {WHAT_THIS_SYSTEM_IS}
          </p>
        </div>
      </div>
    </div>
  );
}
