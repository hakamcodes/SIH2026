"use client";

import { useState } from "react";
import { RotateCw } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useInspector } from "@/components/shell/inspector-provider";
import { reloadRules } from "@/lib/api";
import { describeUnknownError } from "@/lib/errors";
import { cn } from "@/lib/utils";

/**
 * Proves the ruleset is hot-swappable at runtime (CLAUDE.md's "hot-swappable
 * at runtime" claim): POST /api/v1/rules/reload re-reads
 * packages/rules/lmd_rules.v1.json (or LMD_RULES_PATH) from disk with no
 * process restart. Bumps `onReloaded`'s counter so RulesTable below
 * refetches and the rule_count / rows visibly change.
 */
export function RulesetReloadButton({ onReloaded }: { onReloaded: () => void }) {
  const { inspector } = useInspector();
  const [pending, setPending] = useState(false);

  async function handleReload() {
    if (!inspector) {
      toast.error("Sign in with an inspector identity to reload the ruleset.");
      return;
    }
    setPending(true);
    try {
      const result = await reloadRules(inspector.inspectorId);
      toast.success(`Ruleset reloaded — ${result.rule_count} rules loaded`);
      onReloaded();
    } catch (err) {
      toast.error(describeUnknownError(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <Button size="sm" variant="outline" onClick={handleReload} disabled={pending} className="gap-1.5">
      <RotateCw className={cn("size-3.5", pending && "animate-spin")} aria-hidden="true" />
      {pending ? "Reloading…" : "Reload ruleset"}
    </Button>
  );
}
