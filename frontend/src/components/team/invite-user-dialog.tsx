"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { UserPlus } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
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
import { useInviteUser } from "@/lib/hooks/use-team";

const schema = z.object({
  email: z.string().email("Email inválido"),
  full_name: z.string().min(2, "Mínimo 2 caracteres").max(200),
  role: z.enum(["owner", "admin", "member"]),
  password: z.string().min(8, "Mínimo 8 caracteres").max(128),
});

type FormValues = z.infer<typeof schema>;

export function InviteUserDialog({
  canAssignOwner = false,
}: {
  canAssignOwner?: boolean;
}) {
  const [open, setOpen] = React.useState(false);
  const invite = useInviteUser();
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      email: "",
      full_name: "",
      role: "member",
      password: "",
    },
  });

  const onSubmit = async (values: FormValues) => {
    try {
      await invite.mutateAsync(values);
      toast.success(`Invitación creada para ${values.email}`);
      form.reset();
      setOpen(false);
    } catch (e) {
      toast.error(
        e instanceof Error ? e.message : "No pudimos crear la invitación"
      );
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <UserPlus className="size-4" />
          Invitar usuario
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Sumar a alguien al equipo</DialogTitle>
          <DialogDescription>
            En esta fase usamos password provisional — compartilo con la persona
            por canal seguro. En Phase 7+ migramos a magic-link.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            id="invite-form"
            className="space-y-4"
          >
            <FormField
              control={form.control}
              name="full_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Nombre completo</FormLabel>
                  <FormControl>
                    <Input placeholder="María Pérez" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email</FormLabel>
                  <FormControl>
                    <Input type="email" placeholder="maria@empresa.com" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
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
                      className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    >
                      <option value="member">Member — solo lectura</option>
                      <option value="admin">Admin — config + envío</option>
                      {canAssignOwner && (
                        <option value="owner">Owner — control total</option>
                      )}
                    </select>
                  </FormControl>
                  <FormDescription>
                    Members ven conversaciones pero no editan webhooks ni
                    mandan mensajes. Admins manejan números y webhooks.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Contraseña inicial</FormLabel>
                  <FormControl>
                    <Input
                      type="text"
                      autoComplete="new-password"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Compartila con la persona por canal seguro — la cambiarán
                    después del primer login.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </form>
        </Form>
        <DialogFooter>
          <Button
            type="button"
            variant="ghost"
            onClick={() => setOpen(false)}
            disabled={invite.isPending}
          >
            Cancelar
          </Button>
          <Button type="submit" form="invite-form" disabled={invite.isPending}>
            {invite.isPending ? "Creando…" : "Crear invitación"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
