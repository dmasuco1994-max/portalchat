"use client";

import * as React from "react";
import { Users } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "@/components/providers/auth-provider";
import { EmptyState } from "@/components/app/empty-state";
import { PageHeader } from "@/components/app/page-header";
import { InviteUserDialog } from "@/components/team/invite-user-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useDeleteUser,
  useTeam,
  useUpdateUser,
} from "@/lib/hooks/use-team";
import type { Role, User } from "@/lib/api/types";

const ROLE_LABEL: Record<Role, string> = {
  owner: "Owner",
  admin: "Admin",
  member: "Member",
};

const ROLE_VARIANT: Record<Role, React.ComponentProps<typeof Badge>["variant"]> = {
  owner: "default",
  admin: "secondary",
  member: "outline",
};

export default function TeamPage() {
  const { user: me } = useAuth();
  const { data, isPending, error } = useTeam();
  const updateUser = useUpdateUser();
  const deleteUser = useDeleteUser();

  const isOwner = me?.role === "owner";
  const isAdmin = me?.role === "admin" || isOwner;
  const [confirmDelete, setConfirmDelete] = React.useState<User | null>(null);

  return (
    <div>
      <PageHeader
        title="Equipo"
        description="Miembros del workspace y sus permisos."
        actions={isAdmin && <InviteUserDialog canAssignOwner={isOwner} />}
      />

      {isPending && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-[72px] w-full rounded-xl" />
          ))}
        </div>
      )}

      {error && (
        <p className="text-sm text-destructive">{error.message}</p>
      )}

      {data && data.length === 0 && (
        <EmptyState
          icon={<Users className="size-6" />}
          title="Sos el único en el workspace"
          description="Sumá a tu equipo cuando estés listo — podés asignar roles distintos para limitar qué puede hacer cada uno."
          action={isAdmin && <InviteUserDialog canAssignOwner={isOwner} />}
        />
      )}

      {data && data.length > 0 && (
        <Card>
          <CardContent className="p-0">
            <div className="divide-y">
              {data.map((u) => {
                const isMe = u.id === me?.id;
                const initials = (u.full_name || u.email)
                  .split(/[\s@.]+/)
                  .filter(Boolean)
                  .slice(0, 2)
                  .map((s) => s[0]?.toUpperCase())
                  .join("");
                return (
                  <div
                    key={u.id}
                    className="flex flex-wrap items-center gap-3 px-4 py-3"
                  >
                    <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-brand-gradient text-sm font-semibold text-white">
                      {initials || "?"}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="truncate font-medium">
                          {u.full_name}
                          {isMe && (
                            <span className="ml-2 text-xs font-normal text-muted-foreground">
                              (vos)
                            </span>
                          )}
                        </p>
                        <Badge variant={ROLE_VARIANT[u.role]}>
                          {ROLE_LABEL[u.role]}
                        </Badge>
                        {!u.is_active && (
                          <Badge variant="outline" className="text-muted-foreground">
                            Inactivo
                          </Badge>
                        )}
                      </div>
                      <p className="truncate text-sm text-muted-foreground">
                        {u.email}
                      </p>
                    </div>
                    {isAdmin && !isMe && (
                      <div className="flex items-center gap-2">
                        {isOwner && u.role !== "owner" && (
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={updateUser.isPending}
                            onClick={async () => {
                              try {
                                await updateUser.mutateAsync({
                                  id: u.id,
                                  input: {
                                    role:
                                      u.role === "admin" ? "member" : "admin",
                                  },
                                });
                                toast.success("Rol actualizado");
                              } catch (e) {
                                toast.error(
                                  e instanceof Error ? e.message : "Falló"
                                );
                              }
                            }}
                          >
                            {u.role === "admin"
                              ? "Bajar a Member"
                              : "Promover a Admin"}
                          </Button>
                        )}
                        {isOwner && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive hover:text-destructive"
                            onClick={() => setConfirmDelete(u)}
                          >
                            Eliminar
                          </Button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      <ConfirmDialog
        open={!!confirmDelete}
        onOpenChange={(open) => !open && setConfirmDelete(null)}
        title={`¿Eliminar a ${confirmDelete?.full_name}?`}
        description="Pierde acceso al workspace inmediatamente. Esto no se puede deshacer."
        confirmLabel="Eliminar"
        destructive
        loading={deleteUser.isPending}
        onConfirm={async () => {
          if (!confirmDelete) return;
          try {
            await deleteUser.mutateAsync(confirmDelete.id);
            toast.success("Usuario eliminado");
            setConfirmDelete(null);
          } catch (e) {
            toast.error(e instanceof Error ? e.message : "Falló");
          }
        }}
      />
    </div>
  );
}
