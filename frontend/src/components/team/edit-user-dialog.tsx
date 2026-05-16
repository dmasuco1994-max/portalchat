"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Save } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useUpdateUser } from "@/lib/hooks/use-team";
import type { Role, User } from "@/lib/api/types";

const schema = z.object({
  full_name: z.string().min(2, "Mínimo 2 caracteres").max(200),
  role: z.enum(["owner", "admin", "member"]),
  is_active: z.boolean(),
});

type FormValues = z.infer<typeof schema>;

interface Props {
  user: User | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  canChangeRole: boolean;
  /** True if the viewer is editing themselves — we hide the role + active
   *  toggles because those are admin-driven. */
  isSelf: boolean;
}

export function EditUserDialog({
  user,
  open,
  onOpenChange,
  canChangeRole,
  isSelf,
}: Props) {
  const update = useUpdateUser();
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      full_name: user?.full_name ?? "",
      role: (user?.role ?? "member") as Role,
      is_active: user?.is_active ?? true,
    },
  });

  React.useEffect(() => {
    if (user) {
      form.reset({
        full_name: user.full_name,
        role: user.role,
        is_active: user.is_active,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  if (!user) return null;

  const onSubmit = async (values: FormValues) => {
    try {
      await update.mutateAsync({
        id: user.id,
        input: {
          full_name: values.full_name,
          role: canChangeRole && !isSelf ? values.role : undefined,
          is_active: !isSelf ? values.is_active : undefined,
        },
      });
      toast.success("Usuario actualizado");
      onOpenChange(false);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "No pudimos actualizar");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Editar usuario</DialogTitle>
          <DialogDescription>
            {user.email}
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form
            id="edit-user-form"
            onSubmit={form.handleSubmit(onSubmit)}
            className="space-y-4"
          >
            <FormField
              control={form.control}
              name="full_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Nombre completo</FormLabel>
                  <FormControl>
                    <Input autoComplete="off" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            {!isSelf && (
              <FormField
                control={form.control}
                name="role"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Rol</FormLabel>
                    <FormControl>
                      <select
                        value={field.value}
                        onChange={field.onChange}
                        disabled={!canChangeRole}
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        <option value="member">Member</option>
                        <option value="admin">Admin</option>
                        {canChangeRole && (
                          <option value="owner">Owner</option>
                        )}
                      </select>
                    </FormControl>
                    {!canChangeRole && (
                      <FormDescription>
                        Solo un owner puede cambiar roles.
                      </FormDescription>
                    )}
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}
            {!isSelf && (
              <FormField
                control={form.control}
                name="is_active"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-3">
                    <FormControl>
                      <input
                        type="checkbox"
                        checked={field.value}
                        onChange={field.onChange}
                        className="mt-1 size-4 rounded border-input"
                      />
                    </FormControl>
                    <div className="space-y-0.5">
                      <FormLabel>Activo</FormLabel>
                      <FormDescription>
                        Si lo desactivás, no puede iniciar sesión pero
                        sus mensajes y permisos quedan intactos para
                        reactivar después.
                      </FormDescription>
                    </div>
                  </FormItem>
                )}
              />
            )}
          </form>
        </Form>
        <DialogFooter>
          <Button
            type="button"
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={update.isPending}
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            form="edit-user-form"
            disabled={update.isPending || !form.formState.isDirty}
          >
            <Save className="size-4" />
            {update.isPending ? "Guardando…" : "Guardar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
