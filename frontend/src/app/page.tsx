"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Scale, ShieldCheck, ScanLine, ClipboardCheck } from "lucide-react";

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
    <div className="flex min-h-dvh flex-col lg:flex-row">
      {/* ── Left Hero Panel (desktop only) ─────────────────────────── */}
      <div className="hidden lg:flex lg:w-[52%] xl:w-[55%] flex-col justify-between bg-gradient-sidebar px-10 py-12 xl:px-16 xl:py-14">
        {/* Top: wordmark */}
        <div className="flex items-center gap-2.5">
          <div className="flex size-8 items-center justify-center rounded-lg bg-gradient-primary shadow-sm">
            <Scale className="size-4 text-white" aria-hidden="true" />
          </div>
          <span className="text-sm font-semibold tracking-tight text-sidebar-foreground">
            Legal Metrology Compliance Scanner
          </span>
        </div>

        {/* Centre: feature showcase */}
        <div className="space-y-10">
          <div className="space-y-4">
            <p className="label-caps text-sidebar-foreground/50">SIH Problem Statement 26034</p>
            <h1 className="text-3xl font-bold leading-tight tracking-tight text-white xl:text-4xl">
              AI-Powered Package
              <br />
              Label Compliance
            </h1>
            <p className="max-w-sm text-sm leading-relaxed text-sidebar-foreground/70">
              Automated pre-screening for Legal Metrology (Packaged Commodities) Rules, 2011.
              Inspector-ready with a full audit trail, point-in-time rule evaluation, and
              violation report generation.
            </p>
          </div>

          {/* Feature pills */}
          <ul className="space-y-3">
            {[
              {
                icon: ScanLine,
                label: "OCR + Vision pipeline",
                desc: "RapidOCR + optional vision model for field extraction",
              },
              {
                icon: ClipboardCheck,
                label: "29-rule JSON DSL engine",
                desc: "Hot-swappable ruleset, point-in-time evaluation",
              },
              {
                icon: ShieldCheck,
                label: "Hash-chained audit log",
                desc: "Evidence chain & Section 63 BSA 2023 report generation",
              },
            ].map(({ icon: Icon, label, desc }) => (
              <li key={label} className="flex items-start gap-3">
                <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md bg-sidebar-accent">
                  <Icon className="size-3.5 text-sidebar-foreground/80" aria-hidden="true" />
                </span>
                <div>
                  <p className="text-sm font-medium text-sidebar-foreground">{label}</p>
                  <p className="text-xs text-sidebar-foreground/50">{desc}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        {/* Bottom: legal notice */}
        <p className="text-2xs text-sidebar-foreground/35 max-w-sm leading-relaxed">
          Advisory pre-screening signal only. Not a legal determination or enforcement action.
          All decisions require a qualified Legal Metrology Officer.
        </p>
      </div>

      {/* ── Right: Identity Form ────────────────────────────────────── */}
      <div className="bg-gradient-hero flex flex-1 items-center justify-center px-4 py-10 lg:bg-none lg:bg-background">
        <div className="w-full max-w-sm">
          {/* Mobile header (hidden on desktop where the left panel shows) */}
          <div className="mb-8 flex flex-col items-center text-center lg:hidden">
            <div className="animate-hero-icon glow-compliant flex size-14 items-center justify-center rounded-2xl bg-gradient-primary shadow-lg">
              <Scale className="size-6 text-primary-foreground" aria-hidden="true" />
            </div>
            <h1
              className="text-page-title animate-fade-in-up mt-4 text-2xl font-bold text-foreground"
              style={{ animationDelay: "80ms" }}
            >
              Legal Metrology Compliance Scanner
            </h1>
            <p
              className="animate-fade-in-up mt-1 text-xs text-fg-subtle"
              style={{ animationDelay: "140ms" }}
            >
              SIH Problem Statement 26034
            </p>
          </div>

          {/* Desktop header */}
          <div className="mb-8 hidden flex-col lg:flex">
            <h2 className="text-page-title font-bold text-foreground">Inspector sign-in</h2>
            <p className="mt-1 text-sm text-fg-muted">
              Enter your identity to begin an inspection session.
            </p>
          </div>

          <form
            onSubmit={handleSubmit}
            className="shadow-panel animate-fade-in-up flex flex-col gap-4 rounded-md border border-border bg-surface p-5"
            style={{ animationDelay: "200ms" }}
          >
            <div
              className="stagger-item flex flex-col gap-1.5"
              style={{ "--stagger": 1 } as React.CSSProperties}
            >
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

            <div
              className="stagger-item flex flex-col gap-1.5"
              style={{ "--stagger": 2 } as React.CSSProperties}
            >
              <Label htmlFor="designation">Designation</Label>
              <Input
                id="designation"
                value={designation}
                onChange={(e) => setDesignation(e.target.value)}
                placeholder="Legal Metrology Officer"
                autoComplete="off"
              />
            </div>

            <div
              className="stagger-item flex flex-col gap-1.5"
              style={{ "--stagger": 3 } as React.CSSProperties}
            >
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
                Sent as <code className="font-mono">X-Inspector-Id</code> on every case action
                you take. Not verified against a user directory — there isn&apos;t one in this
                build.
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
    </div>
  );
}
