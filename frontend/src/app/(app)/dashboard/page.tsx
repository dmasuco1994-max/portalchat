"use client";

import { Phone } from "lucide-react";

import { useAuth } from "@/components/providers/auth-provider";
import { EmptyState } from "@/components/app/empty-state";
import { PageHeader } from "@/components/app/page-header";
import { NewNumberDialog } from "@/components/numbers/new-number-dialog";
import { NumberCard } from "@/components/numbers/number-card";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useNumbers } from "@/lib/hooks/use-numbers";

export default function DashboardPage() {
  const { user } = useAuth();
  const { data, isPending, error } = useNumbers();
  const canCreate = user?.role === "owner" || user?.role === "admin";

  return (
    <div>
      <PageHeader
        title="Números"
        description="Las líneas de WhatsApp conectadas a tu workspace."
        actions={canCreate && <NewNumberDialog />}
      />

      {isPending && (
        <div className="grid gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-[68px] w-full rounded-xl" />
          ))}
        </div>
      )}

      {error && (
        <Card>
          <CardHeader>
            <CardTitle>No pudimos cargar los números</CardTitle>
            <CardDescription>{error.message}</CardDescription>
          </CardHeader>
        </Card>
      )}

      {data && data.length === 0 && (
        <EmptyState
          icon={<Phone className="size-6" />}
          title="Todavía no hay números"
          description={
            canCreate
              ? "Creá tu primer número, escaneá el QR con WhatsApp y empezá a recibir conversaciones acá mismo."
              : "Pedile al owner o a un admin del workspace que sume el primer número."
          }
          action={canCreate && <NewNumberDialog />}
        />
      )}

      {data && data.length > 0 && (
        <div className="grid gap-3">
          {data.map((n) => (
            <NumberCard key={n.id} number={n} />
          ))}
        </div>
      )}
    </div>
  );
}
