"use client";

import Link from "next/link";
import { ChevronRight, MessageSquare, Phone } from "lucide-react";

import { EmptyState } from "@/components/app/empty-state";
import { PageHeader } from "@/components/app/page-header";
import { StatusBadge } from "@/components/numbers/status-badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useNumbers } from "@/lib/hooks/use-numbers";

export default function ConversationsIndexPage() {
  const { data, isPending } = useNumbers();

  return (
    <div>
      <PageHeader
        title="Conversaciones"
        description="Elegí un número para ver sus conversaciones."
        accentClass="accent-conversations"
      />

      {isPending && (
        <div className="grid gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-[68px] w-full rounded-xl" />
          ))}
        </div>
      )}

      {data && data.length === 0 && (
        <EmptyState
          icon={<MessageSquare className="size-6" />}
          title="No hay números todavía"
          description="Sumá tu primer número desde la sección Números, escaneá el QR y empezarás a recibir conversaciones acá."
        />
      )}

      {data && data.length > 0 && (
        <div className="grid gap-3">
          {data.map((n) => {
            const initials = (n.name || "?")
              .split(/\s+/)
              .filter(Boolean)
              .slice(0, 2)
              .map((s) => s[0]?.toUpperCase())
              .join("");
            return (
              <Link
                key={n.id}
                href={`/numbers/${n.id}/conversations`}
                className="block"
              >
                <Card className="group flex items-center gap-4 p-4 transition-all hover:border-primary/40 hover:shadow-md">
                  <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-brand-gradient text-base font-semibold text-white">
                    {initials || <Phone className="size-5" />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="truncate font-medium">{n.name}</p>
                      <StatusBadge status={n.status} pulse />
                    </div>
                    <p className="mt-0.5 truncate text-sm text-muted-foreground">
                      {n.phone_number
                        ? `+${n.phone_number}`
                        : "Sin pairear"}
                    </p>
                  </div>
                  <ChevronRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
