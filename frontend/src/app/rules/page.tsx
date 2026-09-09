"use client";

import { useState } from "react";

import { Panel, PanelBody, PanelHeader } from "@/components/common/panel";
import { RulesTable } from "@/components/rules/rules-table";
import { RulesetReloadButton } from "@/components/rules/ruleset-reload-button";
import { PageHeader } from "@/components/shell/page-header";
import { Button } from "@/components/ui/button";
import { CATEGORY_VOCAB, SEVERITY_VOCAB } from "@/lib/vocab";
import type { RuleCategory, Severity } from "@/lib/types";
import { cn } from "@/lib/utils";

function FilterChip({
  active,
  onClick,
  icon: Icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "inline-flex min-h-8 items-center gap-1 rounded-sm border px-2 py-1 text-xs transition-[background-color,border-color,box-shadow,transform,color] duration-[var(--dur)]",
        active
          ? "scale-105 border-transparent bg-gradient-primary text-primary-foreground shadow-sm"
          : "border-border bg-surface text-fg-muted hover:border-border-strong hover:text-foreground hover:shadow-sm",
      )}
    >
      <Icon className="size-3" />
      {label}
    </button>
  );
}

export default function RulesPage() {
  const [category, setCategory] = useState<RuleCategory | null>(null);
  const [severity, setSeverity] = useState<Severity | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div>
      <PageHeader
        eyebrow="Reference"
        title="Ruleset"
        description="Every rule is evaluated through the JSON DSL interpreter — no hardcoded per-rule branch exists. Rules, severities, citations and effective dates are data, and the ruleset is hot-swappable at runtime."
        actions={<RulesetReloadButton onReloaded={() => setRefreshKey((k) => k + 1)} />}
      />

      <div className="mb-4 flex flex-wrap gap-4">
        <div>
          <p className="label-caps mb-1.5">Category</p>
          <div className="flex flex-wrap gap-1.5">
            {(Object.keys(CATEGORY_VOCAB) as RuleCategory[]).map((key) => (
              <FilterChip
                key={key}
                active={category === key}
                onClick={() => setCategory((c) => (c === key ? null : key))}
                icon={CATEGORY_VOCAB[key].icon}
                label={CATEGORY_VOCAB[key].label}
              />
            ))}
          </div>
        </div>
        <div>
          <p className="label-caps mb-1.5">Severity</p>
          <div className="flex flex-wrap gap-1.5">
            {(Object.keys(SEVERITY_VOCAB) as Severity[]).map((key) => (
              <FilterChip
                key={key}
                active={severity === key}
                onClick={() => setSeverity((s) => (s === key ? null : key))}
                icon={SEVERITY_VOCAB[key].icon}
                label={SEVERITY_VOCAB[key].label}
              />
            ))}
          </div>
        </div>
        {(category || severity) && (
          <div className="flex items-end">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setCategory(null);
                setSeverity(null);
              }}
            >
              Clear filters
            </Button>
          </div>
        )}
      </div>

      <Panel>
        <PanelHeader
          title="Rules"
          description="Loaded from packages/rules/lmd_rules.v1.json via GET /api/v1/rules."
        />
        <PanelBody className="p-0">
          <RulesTable categoryFilter={category} severityFilter={severity} refreshKey={refreshKey} />
        </PanelBody>
      </Panel>
    </div>
  );
}
