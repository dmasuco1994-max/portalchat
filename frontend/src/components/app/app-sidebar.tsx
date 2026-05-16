"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LogOut,
  MessageSquare,
  Phone,
  Settings,
  Users,
} from "lucide-react";

import { Brand } from "@/components/app/brand";
import { ThemeToggle } from "@/components/app/theme-toggle";
import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const NAV: { href: string; label: string; icon: React.ReactNode }[] = [
  {
    href: "/dashboard",
    label: "Números",
    icon: <Phone className="size-4" />,
  },
  {
    href: "/conversations",
    label: "Conversaciones",
    icon: <MessageSquare className="size-4" />,
  },
  {
    href: "/team",
    label: "Equipo",
    icon: <Users className="size-4" />,
  },
  {
    href: "/settings",
    label: "Ajustes",
    icon: <Settings className="size-4" />,
  },
];

export function AppSidebar() {
  const pathname = usePathname();
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

  const initials = (user?.full_name ?? user?.email ?? "?")
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase())
    .join("");

  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
      <div className="flex h-16 items-center px-5">
        <Link href="/dashboard" className="inline-block">
          <Brand size="md" />
        </Link>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-2">
        {NAV.map((item) => {
          const active =
            item.href === "/dashboard"
              ? pathname === "/dashboard" ||
                pathname.startsWith("/numbers")
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/80 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
              )}
            >
              {item.icon}
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-sidebar-border px-3 py-3">
        <div className="flex items-center gap-3 rounded-md px-2 py-2">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-brand-gradient text-sm font-semibold text-white">
            {initials || "?"}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">
              {user?.full_name ?? "Usuario"}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              {user?.email} · {user?.role}
            </p>
          </div>
        </div>
        <div className="mt-2 flex items-center gap-1">
          <ThemeToggle />
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            disabled={signingOut}
            className="flex-1 justify-start"
          >
            <LogOut className="size-4" />
            {signingOut ? "Saliendo…" : "Salir"}
          </Button>
        </div>
      </div>
    </aside>
  );
}
