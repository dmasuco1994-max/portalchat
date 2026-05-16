"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Building2, Save } from "lucide-react";

import { useAuth } from "@/components/providers/auth-provider";
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
import { Skeleton } from "@/components/ui/skeleton";
import { useUpdateWorkspace, useWorkspace } from "@/lib/hooks/use-settings";

const schema = z.object({
  name: z.string().min(2, "Mínimo 2 caracteres").max(120),
});

type FormValues = z.infer<typeof schema>;

export function WorkspaceCard() {
  const { user } = useAuth();
  const isOwner = user?.role === "owner";
  const { data, isPending } = useWorkspace();
  const update = useUpdateWorkspace();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "" },
  });

  React.useEffect(() => {
    if (data) form.reset({ name: data.name });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.name]);

  if (isPending || !data) {
    return <Skeleton className="h-[200px] w-full rounded-xl" />;
  }

  const onSubmit = async (values: FormValues) => {
    try {
      await update.mutateAsync(values.name.trim());
      toast.success("Workspace actualizado");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "No pudimos guardar");
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="size-4 text-primary" />
              Workspace
            </CardTitle>
            <CardDescription>
              El nombre y el identificador de la organización.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-5 sm:grid-cols-2">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Nombre</FormLabel>
                  <FormControl>
                    <Input disabled={!isOwner} {...field} />
                  </FormControl>
                  {!isOwner && (
                    <FormDescription>
                      Solo un owner puede renombrar el workspace.
                    </FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormItem>
              <FormLabel>Slug</FormLabel>
              <FormControl>
                <Input value={data.slug} disabled readOnly />
              </FormControl>
              <FormDescription>
                Identificador inmutable — cambiarlo rompería URLs cacheadas
                de integraciones.
              </FormDescription>
            </FormItem>
          </CardContent>
          <CardFooter className="justify-end">
            <Button
              type="submit"
              disabled={
                !isOwner || update.isPending || !form.formState.isDirty
              }
            >
              <Save className="size-4" />
              {update.isPending ? "Guardando…" : "Guardar"}
            </Button>
          </CardFooter>
        </Card>
      </form>
    </Form>
  );
}
