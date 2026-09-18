import { cn } from "@/lib/utils";

/**
 * The one surface container in the product. Used instead of shadcn's Card
 * because Card ships its own padding, gap and radius scale; this design
 * direction wants a flat 1px-bordered surface with a distinct header band and
 * no nesting.
 */
export function Panel({
  className,
  ...props
}: React.ComponentProps<"section">) {
  return (
    <section
      className={cn(
        "shadow-panel min-w-0 overflow-hidden rounded-md border border-border bg-surface transition-shadow duration-[var(--dur)]",
        className,
      )}
      {...props}
    />
  );
}

export function PanelHeader({
  title,
  description,
  actions,
  className,
}: {
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center justify-between gap-2 border-b border-border bg-surface-subtle/50 px-4 py-2.5",
        className,
      )}
    >
      <div className="min-w-0">
        <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
        {description && (
          <p className="mt-0.5 text-xs text-fg-muted">{description}</p>
        )}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

export function PanelBody({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("p-4", className)} {...props} />;
}

export function PanelFooter({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-2 border-t border-border bg-surface-subtle px-4 py-2.5",
        className,
      )}
      {...props}
    />
  );
}

/** Label/value row. `mono` for anything an inspector reads digit by digit. */
export function DataRow({
  label,
  value,
  mono = false,
  hint,
  className,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
  hint?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5 border-b border-border py-1.5 last:border-b-0",
        className,
      )}
    >
      <dt className="label-caps">{label}</dt>
      <dd
        className={cn(
          "min-w-0 text-right text-sm",
          mono && "font-mono text-xs",
        )}
        data-numeric={mono ? "" : undefined}
        title={hint}
      >
        {value}
      </dd>
    </div>
  );
}
