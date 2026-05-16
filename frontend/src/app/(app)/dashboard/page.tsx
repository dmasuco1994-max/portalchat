"use client";

import { useAuth } from "@/components/providers/auth-provider";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function DashboardPage() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Welcome back{user ? `, ${user.full_name}` : ""}.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>WhatsApp numbers</CardTitle>
          <CardDescription>
            Number management is delivered in Phase 6.2 (next PR in the chain).
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Phase 6.1 wires up auth, the protected shell and the API client.
        </CardContent>
      </Card>
    </div>
  );
}
