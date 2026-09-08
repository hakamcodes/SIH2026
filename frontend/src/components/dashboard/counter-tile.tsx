import type { LucideIcon } from "lucide-react";

import { Panel } from "@/components/common/panel";
import { cn } from "@/lib/utils";

export function CounterTile({
  label,
  value,
  icon: Icon,
  accentClassName,
}: {
  label: string;
  /** null renders as "—", never as 0 — a genuine zero count and "not loaded
   *  yet" must not look identical. */
  value: number | null;
  icon: LucideIcon;
  accentClassName?: string;
}) {
  return (
    <Panel className="p-4 transition-shadow duration-[var(--dur)] hover:shadow-[0_2px_6px_-1px_rgb(15_23_42_/_0.08)]">
      <div className="flex items-center justify-between">
        <p className="label-caps">{label}</p>
        <Icon className={cn("size-3.5 text-fg-subtle", accentClassName)} aria-hidden="true" />
      </div>
      <p className="mt-2 font-mono text-2xl tracking-tight tabular-nums">
        {value === null ? "—" : value.toLocaleString()}
      </p>
    </Panel>
  );
}
