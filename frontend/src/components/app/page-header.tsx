import * as React from "react";

import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  /** Optional section accent class (accent-numbers / accent-team / …) to
   *  tint the underline. Defaults to brand teal. */
  accentClass?: string;
  className?: string;
}

export function PageHeader({
  title,
  description,
  actions,
  accentClass,
  className,
}: PageHeaderProps) {
  return (
    <div className={cn("mb-8 space-y-4", accentClass, className)}>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight md:text-3xl">
            {title}
          </h1>
          {description && (
            <p className="mt-1.5 text-sm text-muted-foreground">{description}</p>
          )}
        </div>
        {actions && (
          <div className="flex flex-wrap items-center gap-2">{actions}</div>
        )}
      </div>
      <div className="relative h-px overflow-hidden">
        <div className="absolute inset-0 bg-border" />
        <div
          className="absolute inset-y-0 left-0 w-32 bg-section-strong"
          style={{ height: "2px", top: "-0.5px" }}
        />
      </div>
    </div>
  );
}
