import Link from "next/link";
import { ChevronRight } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/numbers/status-badge";
import type { WhatsAppNumber } from "@/lib/api/types";

export function NumberCard({ number }: { number: WhatsAppNumber }) {
  return (
    <Link href={`/numbers/${number.id}`} className="block">
      <Card className="transition-colors hover:bg-muted/40">
        <CardContent className="flex items-center justify-between gap-4 p-4">
          <div className="min-w-0">
            <p className="truncate font-medium">{number.name}</p>
            <p className="truncate text-sm text-muted-foreground">
              {number.phone_number ?? "Not paired yet"}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={number.status} />
            <ChevronRight className="size-4 text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
