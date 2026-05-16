"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Key, Save, User as UserIcon } from "lucide-react";

import { useAuth } from "@/components/providers/auth-provider";
import { PageHeader } from "@/components/app/page-header";
import { NotificationsCard } from "@/components/settings/notifications-card";
import { WorkspaceCard } from "@/components/settings/workspace-card";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import { useChangeMyPassword, useUpdateMe } from "@/lib/hooks/use-team";

const profileSchema = z.object({
  full_name: z.string().min(2, "Mínimo 2 caracteres").max(200),
});
type ProfileValues = z.infer<typeof profileSchema>;

const passwordSchema = z
  .object({
    current_password: z.string().min(1, "Requerido"),
    new_password: z.string().min(8, "Mínimo 8 caracteres").max(128),
    confirm_password: z.string(),
  })
  .superRefine((data, ctx) => {
    if (data.new_password !== data.confirm_password) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["confirm_password"],
        message: "Las contraseñas no coinciden",
      });
    }
  });
type PasswordValues = z.infer<typeof passwordSchema>;

export default function SettingsPage() {
  const { user, setUser } = useAuth();
  const updateMe = useUpdateMe();
  const changePassword = useChangeMyPassword();

  const profileForm = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { full_name: user?.full_name ?? "" },
  });

  React.useEffect(() => {
    if (user) profileForm.reset({ full_name: user.full_name });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.full_name]);

  const passwordForm = useForm<PasswordValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: {
      current_password: "",
      new_password: "",
      confirm_password: "",
    },
  });

  if (!user) return null;

  const onSaveProfile = async (values: ProfileValues) => {
    try {
      const updated = await updateMe.mutateAsync(values);
      setUser(updated);
      toast.success("Perfil actualizado");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "No pudimos guardar");
    }
  };

  const onChangePassword = async (values: PasswordValues) => {
    try {
      await changePassword.mutateAsync({
        current_password: values.current_password,
        new_password: values.new_password,
      });
      passwordForm.reset();
      toast.success("Contraseña actualizada");
    } catch (e) {
      toast.error(
        e instanceof Error ? e.message : "No pudimos cambiar la contraseña"
      );
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Ajustes" description="Tu perfil y accesos." />

      <Form {...profileForm}>
        <form onSubmit={profileForm.handleSubmit(onSaveProfile)}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <UserIcon className="size-4 text-primary" />
                Perfil
              </CardTitle>
              <CardDescription>
                Esto es lo que ven tus compañeros del equipo.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-5 sm:grid-cols-2">
              <FormField
                control={profileForm.control}
                name="full_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Nombre completo</FormLabel>
                    <FormControl>
                      <Input autoComplete="name" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormItem>
                <FormLabel>Email</FormLabel>
                <FormControl>
                  <Input value={user.email} disabled readOnly />
                </FormControl>
                <FormDescription>
                  El email es identificador de cuenta — cambiarlo
                  requiere re-verificación y todavía no está disponible.
                </FormDescription>
              </FormItem>
              <FormItem>
                <FormLabel>Rol</FormLabel>
                <FormControl>
                  <Input value={user.role} disabled readOnly />
                </FormControl>
                <FormDescription>
                  Solo un owner puede cambiar tu rol desde la sección
                  Equipo.
                </FormDescription>
              </FormItem>
              <FormItem>
                <FormLabel>Estado</FormLabel>
                <FormControl>
                  <Input
                    value={user.is_active ? "Activo" : "Inactivo"}
                    disabled
                    readOnly
                  />
                </FormControl>
              </FormItem>
            </CardContent>
            <CardFooter className="justify-end">
              <Button
                type="submit"
                disabled={
                  updateMe.isPending || !profileForm.formState.isDirty
                }
              >
                <Save className="size-4" />
                {updateMe.isPending ? "Guardando…" : "Guardar perfil"}
              </Button>
            </CardFooter>
          </Card>
        </form>
      </Form>

      <WorkspaceCard />

      <NotificationsCard />

      <Form {...passwordForm}>
        <form onSubmit={passwordForm.handleSubmit(onChangePassword)}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="size-4 text-primary" />
                Contraseña
              </CardTitle>
              <CardDescription>
                Necesitamos tu contraseña actual para confirmar el cambio.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-5 sm:max-w-md">
              <FormField
                control={passwordForm.control}
                name="current_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Contraseña actual</FormLabel>
                    <FormControl>
                      <Input
                        type="password"
                        autoComplete="current-password"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={passwordForm.control}
                name="new_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Contraseña nueva</FormLabel>
                    <FormControl>
                      <Input
                        type="password"
                        autoComplete="new-password"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>Mínimo 8 caracteres.</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={passwordForm.control}
                name="confirm_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Repetí la contraseña nueva</FormLabel>
                    <FormControl>
                      <Input
                        type="password"
                        autoComplete="new-password"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
            <CardFooter className="justify-end">
              <Button type="submit" disabled={changePassword.isPending}>
                <Save className="size-4" />
                {changePassword.isPending
                  ? "Cambiando…"
                  : "Cambiar contraseña"}
              </Button>
            </CardFooter>
          </Card>
        </form>
      </Form>
    </div>
  );
}
