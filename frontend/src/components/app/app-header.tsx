"use client";

import * as React from "react";
import Link from "next/link";
import { LogOut } from "lucide-react";

import { useAuth } from "@/components/providers/auth-provider";
import { ThemeToggle } from "@/components/app/theme-toggle";
import { Button } from "@/components/ui/button";

export function AppHeader() {
  const { user, logout } = useAuth();
  const [signingOut, setSigningOut] = React.useState(false);

  const handleLogout = async () => {
    setSigningOut(true);
    try {
      await logout();
    } finally {
      setSigningOut(false);
    }
  };

  return (
    <header className="border-b bg-background">
      <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between px-4">
        <Link href="/dashboard" className="font-semibold">
          WhatsApp Portal
        </Link>
        <div className="flex items-center gap-2 text-sm">
          {user && (
            <span className="hidden text-muted-foreground sm:inline">
              {user.email} · {user.role}
            </span>
          )}
          <ThemeToggle />
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            disabled={signingOut}
          >
            <LogOut className="size-4" />
            <span className="sr-only md:not-sr-only">Logout</span>
          </Button>
        </div>
      </div>
    </header>
  );
}
