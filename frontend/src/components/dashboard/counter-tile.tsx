import type { LucideIcon } from "lucide-react";

import { Panel } from "@/components/common/panel";
import { useCountUp } from "@/hooks/use-count-up";
import { cn } from "@/lib/utils";

export function CounterTile({
  label,
  value,
  icon: Icon,
  accentClassName,
  style,
}: {
  label: string;
  /** null renders as "—", never as 0 — a genuine zero count and "not loaded
   *  yet" must not look identical. */
  value: number | null;
  icon: LucideIcon;
  accentClassName?: string;
  style?: React.CSSProperties;
}) {
  const animated = useCountUp(value);
  return (
    <Panel
      className="stagger-item group/tile p-4 transition-[box-shadow,transform] duration-[var(--dur)] hover:-translate-y-0.5 hover:shadow-lg"
      style={style}
    >
      <div className="flex items-center justify-between">
        <p className="label-caps">{label}</p>
        <Icon
          className={cn(
            "size-4 text-fg-subtle transition-transform duration-[var(--dur)] group-hover/tile:scale-110",
            accentClassName,
          )}
          aria-hidden="true"
        />
      </div>
      <p className="mt-2 font-mono text-3xl font-semibold tracking-tight tabular-nums">
        {animated === null ? "—" : animated.toLocaleString()}
      </p>
    </Panel>
  );
}
