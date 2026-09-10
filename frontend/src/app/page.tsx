"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Scale } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useInspector } from "@/components/shell/inspector-provider";

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
    <div className="bg-gradient-hero flex flex-1 items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="animate-hero-icon glow-compliant flex size-14 items-center justify-center rounded-2xl bg-gradient-primary shadow-lg">
            <Scale className="size-6 text-primary-foreground" aria-hidden="true" />
          </div>
          <h1 className="text-page-title animate-fade-in-up mt-4 text-2xl font-bold text-foreground" style={{ animationDelay: "80ms" }}>
            Legal Metrology Compliance Scanner
          </h1>
          <p className="animate-fade-in-up mt-1 text-xs text-fg-subtle" style={{ animationDelay: "140ms" }}>
            SIH Problem Statement 26034
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="shadow-panel animate-fade-in-up flex flex-col gap-4 rounded-md border border-border bg-surface p-5"
          style={{ animationDelay: "200ms" }}
        >
          <div className="stagger-item flex flex-col gap-1.5" style={{ "--stagger": 1 } as React.CSSProperties}>
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

          <div className="stagger-item flex flex-col gap-1.5" style={{ "--stagger": 2 } as React.CSSProperties}>
            <Label htmlFor="designation">Designation</Label>
            <Input
              id="designation"
              value={designation}
              onChange={(e) => setDesignation(e.target.value)}
              placeholder="Legal Metrology Officer"
              autoComplete="off"
            />
          </div>

          <div className="stagger-item flex flex-col gap-1.5" style={{ "--stagger": 3 } as React.CSSProperties}>
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

          <div className="stagger-item" style={{ "--stagger": 4 } as React.CSSProperties}>
            <Button type="submit" disabled={!canContinue} className="mt-1 w-full gap-1.5">
              Continue
              <ArrowRight className="size-3.5" aria-hidden="true" />
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
