"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { RefreshCw, Save, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { SecretDisplay } from "@/components/webhook/secret-display";
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
import { Label } from "@/components/ui/label";
import { SUPPORTED_EVENTS } from "@/lib/api/webhooks";
import type { WhatsAppNumber } from "@/lib/api/types";
import { useUpdateWebhookConfig } from "@/lib/hooks/use-webhook";

const schema = z.object({
  url: z.string().url("Must be a valid URL"),
  active: z.boolean(),
  events: z.array(z.string()),
  rotateSecret: z.boolean(),
});

type FormValues = z.infer<typeof schema>;

function defaultValues(number: WhatsAppNumber): FormValues {
  return {
    url: number.webhook_url ?? "",
    active: number.webhook_active,
    events: number.webhook_events ?? [...SUPPORTED_EVENTS],
    rotateSecret: false,
  };
}

export function WebhookForm({ number }: { number: WhatsAppNumber }) {
  const update = useUpdateWebhookConfig(number.id);
  const [secret, setSecret] = React.useState<string | null>(null);
  const [confirmClear, setConfirmClear] = React.useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: defaultValues(number),
  });

  // Reset the form when the number changes (e.g. after we navigate or invalidate).
  React.useEffect(() => {
    form.reset(defaultValues(number));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [number.id, number.webhook_url, number.webhook_active, number.webhook_events]);

  const onSubmit = async (values: FormValues) => {
    try {
      const result = await update.mutateAsync({
        url: values.url,
        active: values.active,
        events: values.events.length ? values.events : null,
        rotate_secret: values.rotateSecret,
      });
      if (result.secret) {
        setSecret(result.secret);
      } else {
        toast.success("Webhook saved");
      }
      form.setValue("rotateSecret", false);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not save webhook");
    }
  };

  const onClear = async () => {
    try {
      await update.mutateAsync({ url: null });
      form.reset({ url: "", active: false, events: [...SUPPORTED_EVENTS], rotateSecret: false });
      toast.success("Webhook cleared");
      setConfirmClear(false);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not clear webhook");
    }
  };

  const hasExistingConfig = !!number.webhook_url;

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <Card>
          <CardHeader>
            <CardTitle>CRM webhook</CardTitle>
            <CardDescription>
              We POST signed JSON to your URL for each event below. Signature
              header: <code>X-WhatsApp-Portal-Signature: sha256=&lt;hex&gt;</code>.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <FormField
              control={form.control}
              name="url"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Endpoint URL</FormLabel>
                  <FormControl>
                    <Input
                      type="url"
                      placeholder="https://crm.example.com/webhooks/whatsapp"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="active"
              render={({ field }) => (
                <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                  <FormControl>
                    <input
                      type="checkbox"
                      checked={field.value}
                      onChange={field.onChange}
                      className="mt-1 size-4 rounded border-input"
                    />
                  </FormControl>
                  <div className="space-y-0.5">
                    <FormLabel>Active</FormLabel>
                    <FormDescription>
                      Pause deliveries without losing the config.
                    </FormDescription>
                  </div>
                </FormItem>
              )}
            />

            <div className="space-y-2">
              <Label>Events</Label>
              <FormDescription>
                Pick which Evolution events to forward. All five selected = full
                fan-out.
              </FormDescription>
              <FormField
                control={form.control}
                name="events"
                render={({ field }) => (
                  <FormItem>
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      {SUPPORTED_EVENTS.map((ev) => {
                        const checked = field.value.includes(ev);
                        return (
                          <label
                            key={ev}
                            className="flex cursor-pointer items-center gap-2 rounded-md border p-2 text-sm hover:bg-muted/40"
                          >
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={(e) => {
                                const next = e.target.checked
                                  ? [...field.value, ev]
                                  : field.value.filter((x) => x !== ev);
                                field.onChange(next);
                              }}
                              className="size-4 rounded border-input"
                            />
                            <span className="font-mono">{ev}</span>
                          </label>
                        );
                      })}
                    </div>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {hasExistingConfig && (
              <FormField
                control={form.control}
                name="rotateSecret"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border border-amber-500/40 bg-amber-500/5 p-3">
                    <FormControl>
                      <input
                        type="checkbox"
                        checked={field.value}
                        onChange={field.onChange}
                        className="mt-1 size-4 rounded border-input"
                      />
                    </FormControl>
                    <div className="space-y-0.5">
                      <FormLabel>Rotate signing secret</FormLabel>
                      <FormDescription>
                        Generates a new HMAC secret on save. The old one stops
                        working immediately — make sure you can update your CRM.
                      </FormDescription>
                    </div>
                  </FormItem>
                )}
              />
            )}
          </CardContent>
          <CardFooter className="flex flex-wrap justify-between gap-2">
            {hasExistingConfig ? (
              <Button
                type="button"
                variant="ghost"
                onClick={() => setConfirmClear(true)}
                disabled={update.isPending}
              >
                <Trash2 className="size-4" />
                Clear webhook
              </Button>
            ) : (
              <span />
            )}
            <Button type="submit" disabled={update.isPending}>
              {form.watch("rotateSecret") ? (
                <RefreshCw className="size-4" />
              ) : (
                <Save className="size-4" />
              )}
              {update.isPending ? "Saving…" : hasExistingConfig ? "Save" : "Save and generate secret"}
            </Button>
          </CardFooter>
        </Card>
      </form>

      <SecretDisplay secret={secret} onDismiss={() => setSecret(null)} />

      <ConfirmDialog
        open={confirmClear}
        onOpenChange={setConfirmClear}
        title="Clear webhook configuration?"
        description="This removes the URL, events, secret and disables deliveries. Past delivery history stays in the debug log."
        confirmLabel="Clear"
        loading={update.isPending}
        destructive
        onConfirm={onClear}
      />
    </Form>
  );
}
