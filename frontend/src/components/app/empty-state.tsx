import * as React from "react";

import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "relative flex flex-col items-center justify-center overflow-hidden rounded-2xl border bg-card p-10 text-center shadow-sm",
        className
      )}
    >
      {/* Soft gradient halo behind the icon — adds warmth without being noisy. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 mx-auto h-32 w-32 -translate-y-1/2 rounded-full opacity-30 blur-3xl bg-brand-gradient"
      />
      {icon && (
        <div className="relative mb-4 flex size-14 items-center justify-center rounded-full bg-brand-gradient text-white shadow-md ring-4 ring-white/40 dark:ring-white/10">
          {icon}
        </div>
      )}
      <h3 className="relative text-base font-semibold">{title}</h3>
      {description && (
        <p className="relative mt-2 max-w-sm text-sm text-muted-foreground">
          {description}
        </p>
      )}
      {action && <div className="relative mt-5">{action}</div>}
    </div>
  );
}
