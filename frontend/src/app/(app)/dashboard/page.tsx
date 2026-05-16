"use client";

import { useAuth } from "@/components/providers/auth-provider";
import { NewNumberDialog } from "@/components/numbers/new-number-dialog";
import { NumberCard } from "@/components/numbers/number-card";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useNumbers } from "@/lib/hooks/use-numbers";

export default function DashboardPage() {
  const { user } = useAuth();
  const { data, isPending, error } = useNumbers();
  const canCreate = user?.role === "owner" || user?.role === "admin";

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Numbers</h1>
          <p className="text-sm text-muted-foreground">
            WhatsApp lines connected to your workspace.
          </p>
        </div>
        {canCreate && <NewNumberDialog />}
      </div>

      {isPending && (
        <p className="text-sm text-muted-foreground">Loading numbers…</p>
      )}

      {error && (
        <Card>
          <CardHeader>
            <CardTitle>Couldn&apos;t load numbers</CardTitle>
            <CardDescription>{error.message}</CardDescription>
          </CardHeader>
        </Card>
      )}

      {data && data.length === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>No numbers yet</CardTitle>
            <CardDescription>
              {canCreate
                ? "Click “New number” to create your first Evolution instance and pair a WhatsApp account."
                : "An owner or admin needs to add the first number for this workspace."}
            </CardDescription>
          </CardHeader>
          <CardContent />
        </Card>
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
