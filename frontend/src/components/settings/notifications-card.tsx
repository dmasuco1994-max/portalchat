"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Bell, Save, Send } from "lucide-react";

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
import {
  useNotifications,
  useTestNotifications,
  useUpdateNotifications,
} from "@/lib/hooks/use-settings";

const schema = z.object({
  telegram_bot_token: z.string(),
  telegram_chat_id: z.string(),
  notify_on_number_disconnected: z.boolean(),
  notify_on_webhook_abandoned: z.boolean(),
});

type FormValues = z.infer<typeof schema>;

export function NotificationsCard() {
  const { user } = useAuth();
  const canEdit = user?.role === "owner" || user?.role === "admin";
  const { data, isPending } = useNotifications();
  const update = useUpdateNotifications();
  const test = useTestNotifications();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      telegram_bot_token: "",
      telegram_chat_id: "",
      notify_on_number_disconnected: true,
      notify_on_webhook_abandoned: true,
    },
  });

  React.useEffect(() => {
    if (data) {
      form.reset({
        telegram_bot_token: "",
        telegram_chat_id: data.telegram_chat_id ?? "",
        notify_on_number_disconnected: data.notify_on_number_disconnected,
        notify_on_webhook_abandoned: data.notify_on_webhook_abandoned,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    data?.telegram_chat_id,
    data?.notify_on_number_disconnected,
    data?.notify_on_webhook_abandoned,
    data?.has_telegram_bot_token,
  ]);

  const onSubmit = async (values: FormValues) => {
    try {
      await update.mutateAsync({
        // Empty string = "no change" if a token is already saved; otherwise it
        // gets sent as empty and the backend interprets that as "clear".
        telegram_bot_token: values.telegram_bot_token.trim()
          ? values.telegram_bot_token.trim()
          : data?.has_telegram_bot_token
            ? null
            : null,
        telegram_chat_id: values.telegram_chat_id.trim() || null,
        notify_on_number_disconnected: values.notify_on_number_disconnected,
        notify_on_webhook_abandoned: values.notify_on_webhook_abandoned,
      });
      form.setValue("telegram_bot_token", "");
      toast.success("Notificaciones guardadas");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "No pudimos guardar");
    }
  };

  const onTest = async () => {
    try {
      const result = await test.mutateAsync();
      if (result.success) {
        toast.success("Mensaje de prueba enviado");
      } else {
        toast.error(result.detail || "Telegram rechazó el envío");
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "No pudimos enviar");
    }
  };

  if (isPending || !data) {
    return <Skeleton className="h-[480px] w-full rounded-xl" />;
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="size-4 text-primary" />
              Notificaciones (Telegram)
            </CardTitle>
            <CardDescription>
              Recibí alertas en un chat de Telegram cuando un número se
              desconecta o una entrega de webhook agota sus reintentos. Creá un
              bot con{" "}
              <a
                href="https://t.me/BotFather"
                target="_blank"
                rel="noreferrer"
                className="text-primary underline-offset-2 hover:underline"
              >
                @BotFather
              </a>
              , obtené el token, mandale un mensaje al bot desde el chat
              destino, y pegá el <code>chat id</code> que aparezca al hacer{" "}
              <code>https://api.telegram.org/bot&lt;token&gt;/getUpdates</code>.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <FormField
              control={form.control}
              name="telegram_bot_token"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Bot Token</FormLabel>
                  <FormControl>
                    <Input
                      type="password"
                      autoComplete="off"
                      placeholder={
                        data.has_telegram_bot_token
                          ? `Configurado (${data.telegram_bot_token_hint}) — dejá vacío para mantenerlo`
                          : "123456789:AAA..."
                      }
                      disabled={!canEdit}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    {data.has_telegram_bot_token
                      ? "Ya hay un token guardado. Solo lo cambiamos si pegás uno nuevo acá."
                      : "El token completo que te devuelve BotFather al crear el bot."}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="telegram_chat_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Chat ID</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="-1001234567890 ó 123456789"
                      disabled={!canEdit}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Para chats privados con un bot: tu user id. Para grupos:
                    el id negativo del grupo. Se obtiene en{" "}
                    <code>/getUpdates</code> después de mandarle un mensaje al
                    bot.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="rounded-md border p-3 space-y-3">
              <p className="text-sm font-medium">¿Cuándo te avisamos?</p>
              <FormField
                control={form.control}
                name="notify_on_number_disconnected"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                    <FormControl>
                      <input
                        type="checkbox"
                        checked={field.value}
                        onChange={field.onChange}
                        disabled={!canEdit}
                        className="mt-1 size-4 rounded border-input"
                      />
                    </FormControl>
                    <div className="space-y-0.5">
                      <FormLabel>Número desconectado</FormLabel>
                      <FormDescription>
                        Cuando un número paireado pasa de{" "}
                        <code>connected</code> a <code>disconnected</code> (la
                        sesión de WhatsApp se cae).
                      </FormDescription>
                    </div>
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="notify_on_webhook_abandoned"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                    <FormControl>
                      <input
                        type="checkbox"
                        checked={field.value}
                        onChange={field.onChange}
                        disabled={!canEdit}
                        className="mt-1 size-4 rounded border-input"
                      />
                    </FormControl>
                    <div className="space-y-0.5">
                      <FormLabel>Webhook abandonado</FormLabel>
                      <FormDescription>
                        Cuando una entrega al CRM agota sus 5 reintentos
                        (algo del lado del receptor está roto y conviene
                        intervenir manual).
                      </FormDescription>
                    </div>
                  </FormItem>
                )}
              />
            </div>
          </CardContent>
          <CardFooter className="flex flex-wrap justify-between gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={onTest}
              disabled={
                !canEdit ||
                !data.has_telegram_bot_token ||
                !data.telegram_chat_id ||
                test.isPending
              }
            >
              <Send className="size-4" />
              {test.isPending ? "Enviando…" : "Enviar mensaje de prueba"}
            </Button>
            <Button
              type="submit"
              disabled={!canEdit || update.isPending || !form.formState.isDirty}
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
