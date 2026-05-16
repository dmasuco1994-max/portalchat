import Link from "next/link";
import { ChevronRight, Phone } from "lucide-react";

import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/numbers/status-badge";
import type { WhatsAppNumber } from "@/lib/api/types";

export function NumberCard({ number }: { number: WhatsAppNumber }) {
  const initials = (number.name || "?")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase())
    .join("");

  return (
    <Link href={`/numbers/${number.id}`} className="block">
      <Card className="group relative overflow-hidden transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-lg">
        <div
          className="pointer-events-none absolute inset-x-0 top-0 h-px bg-brand-gradient opacity-0 transition-opacity group-hover:opacity-100"
        />
        <div className="flex items-center gap-4 p-4">
          <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-brand-gradient text-base font-semibold text-white shadow-sm">
            {initials || <Phone className="size-5" />}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="truncate font-medium">{number.name}</p>
              <StatusBadge status={number.status} pulse />
            </div>
            <p className="mt-0.5 truncate text-sm text-muted-foreground">
              {number.phone_number ? `+${number.phone_number}` : "Sin pairear"}
              <span className="mx-1.5 text-muted-foreground/40">·</span>
              <span className="font-mono text-xs">{number.instance_name}</span>
            </p>
          </div>
          <ChevronRight className="size-4 text-muted-foreground transition-all group-hover:translate-x-0.5 group-hover:text-primary" />
        </div>
      </Card>
    </Link>
  );
}
