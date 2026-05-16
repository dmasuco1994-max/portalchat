"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Check, Copy, RefreshCw, Save, Trash2 } from "lucide-react";

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
import { API_BASE } from "@/lib/api/config";
import { SUPPORTED_EVENTS } from "@/lib/api/webhooks";
import type { WebhookFormat, WhatsAppNumber } from "@/lib/api/types";
import { useUpdateWebhookConfig } from "@/lib/hooks/use-webhook";

const APIWHA_DEFAULT_URL = "https://s2.neotel.us/NeoWebhook/api/ApiWha";
const NEOTEL_CUSTOM_DEFAULT_URL =
  "https://s2.neotel.cc/neowebhook/api/CustomAccount/Messages/";

const schema = z.object({
  format: z.enum(["portal", "apiwha_neotel", "neotel_custom"]),
  url: z.string().url("Must be a valid URL"),
  active: z.boolean(),
  events: z.array(z.string()),
  rotateSecret: z.boolean(),
  neotelToken: z.string(),
  neotelAccountId: z.string(),
});

type FormValues = z.infer<typeof schema>;

function defaultValues(number: WhatsAppNumber): FormValues {
  const extra = (number.webhook_extra ?? {}) as {
    token?: unknown;
    account_id?: unknown;
  };
  return {
    format: number.webhook_format,
    url: number.webhook_url ?? "",
    active: number.webhook_active,
    events: number.webhook_events ?? [...SUPPORTED_EVENTS],
    rotateSecret: false,
    neotelToken: typeof extra.token === "string" ? extra.token : "",
    neotelAccountId:
      typeof extra.account_id === "string" ? extra.account_id : "",
  };
}

function buildCallbackUrl(accountId: string, token: string): string {
  if (!accountId || !token) return "";
  // Strip trailing /api/v1 if present so we don't double it.
  const base = API_BASE.replace(/\/api\/v1\/?$/, "");
  const apiBase = base.endsWith("/api/v1") ? base : `${base}/api/v1`;
  return `${apiBase}/integrations/neotel/${encodeURIComponent(
    accountId
  )}/send?token=${encodeURIComponent(token)}`;
}

export function WebhookForm({ number }: { number: WhatsAppNumber }) {
  const update = useUpdateWebhookConfig(number.id);
  const [secret, setSecret] = React.useState<string | null>(null);
  const [confirmClear, setConfirmClear] = React.useState(false);
  const [copiedCallback, setCopiedCallback] = React.useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: defaultValues(number),
  });

  React.useEffect(() => {
    form.reset(defaultValues(number));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    number.id,
    number.webhook_url,
    number.webhook_active,
    number.webhook_events,
    number.webhook_format,
    JSON.stringify(number.webhook_extra ?? {}),
  ]);

  const format = form.watch("format");
  const isApiwha = format === "apiwha_neotel";
  const isNeotelCustom = format === "neotel_custom";

  React.useEffect(() => {
    if (isApiwha && !form.getValues("url")) {
      form.setValue("url", APIWHA_DEFAULT_URL);
    } else if (isNeotelCustom && !form.getValues("url")) {
      form.setValue("url", NEOTEL_CUSTOM_DEFAULT_URL);
    }
  }, [isApiwha, isNeotelCustom, form]);

  const onSubmit = async (values: FormValues) => {
    try {
      let extra: Record<string, unknown> | null = null;
      if (values.format === "apiwha_neotel") {
        extra = { token: values.neotelToken || null };
      } else if (values.format === "neotel_custom") {
        if (!values.neotelAccountId.trim()) {
          form.setError("neotelAccountId", {
            message: "Account ID is required for Neotel Custom Provider",
          });
          return;
        }
        extra = { account_id: values.neotelAccountId.trim() };
      }

      const result = await update.mutateAsync({
        url: values.url,
        active: values.active,
        events:
          values.format === "portal"
            ? values.events.length
              ? values.events
              : null
            : null,
        rotate_secret: values.rotateSecret,
        format: values.format,
        extra,
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
      form.reset({
        format: "portal",
        url: "",
        active: false,
        events: [...SUPPORTED_EVENTS],
        rotateSecret: false,
        neotelToken: "",
        neotelAccountId: "",
      });
      toast.success("Webhook cleared");
      setConfirmClear(false);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not clear webhook");
    }
  };

  const hasExistingConfig = !!number.webhook_url;
  const savedExtra = (number.webhook_extra ?? {}) as {
    callback_token?: unknown;
    account_id?: unknown;
  };
  const callbackUrl =
    typeof savedExtra.account_id === "string" &&
    typeof savedExtra.callback_token === "string"
      ? buildCallbackUrl(savedExtra.account_id, savedExtra.callback_token)
      : "";

  const copyCallback = async () => {
    if (!callbackUrl) return;
    try {
      await navigator.clipboard.writeText(callbackUrl);
      setCopiedCallback(true);
      setTimeout(() => setCopiedCallback(false), 1500);
      toast.success("Copied to clipboard");
    } catch {
      toast.error("Couldn't copy — copy it manually");
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <Card>
          <CardHeader>
            <CardTitle>CRM webhook</CardTitle>
            <CardDescription>
              {isApiwha
                ? "Apiwha-compatible form-encoded POST. No HMAC."
                : isNeotelCustom
                  ? "Neotel Custom Provider — bidirectional. We POST inbound to the Messages URL; Neotel POSTs outbound to the callback URL shown below."
                  : "We POST signed JSON. Signature header: X-WhatsApp-Portal-Signature: sha256=<hex>."}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <FormField
              control={form.control}
              name="format"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Wire format</FormLabel>
                  <FormControl>
                    <select
                      value={field.value}
                      onChange={(e) =>
                        field.onChange(e.target.value as WebhookFormat)
                      }
                      className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    >
                      <option value="portal">
                        Portal — JSON + HMAC (default)
                      </option>
                      <option value="apiwha_neotel">
                        APIWha (Neotel CAPIWHA) — inbound only
                      </option>
                      <option value="neotel_custom">
                        Neotel Custom Provider — bidirectional
                      </option>
                    </select>
                  </FormControl>
                  <FormDescription>
                    {isNeotelCustom
                      ? "We forward inbound messages + status updates as Custom Provider JSON, and expose a callback URL so Neotel can dispatch agent replies through Evolution."
                      : isApiwha
                        ? "Forwards only inbound text messages, form-encoded, no signature. Cannot send."
                        : "Forwards every event you pick below as signed JSON."}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="url"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    {isNeotelCustom ? "Messages endpoint URL" : "Endpoint URL"}
                  </FormLabel>
                  <FormControl>
                    <Input
                      type="url"
                      placeholder={
                        isApiwha
                          ? APIWHA_DEFAULT_URL
                          : isNeotelCustom
                            ? `${NEOTEL_CUSTOM_DEFAULT_URL}<channel>`
                            : "https://crm.example.com/webhooks/whatsapp"
                      }
                      {...field}
                    />
                  </FormControl>
                  {isNeotelCustom && (
                    <FormDescription>
                      Include the channel segment (and optionally{" "}
                      <code>@provider</code>). We derive the Events URL by
                      swapping <code>/Messages/</code> → <code>/Events/</code>.
                    </FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />

            {isApiwha && (
              <>
                <FormField
                  control={form.control}
                  name="neotelToken"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Neotel Token (optional)</FormLabel>
                      <FormControl>
                        <Input placeholder="MAf5psdL3-AP5BX…" {...field} />
                      </FormControl>
                      <FormDescription>
                        Sent as <code>apikey</code> in the form body. Apiwha
                        always includes this; Neotel may validate against it.
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className="rounded-md border border-sky-500/40 bg-sky-500/5 p-3 text-sm">
                  <p className="font-medium">Match on Neotel side</p>
                  <p className="mt-1 text-muted-foreground">
                    The <code>Cuenta</code> field in Neotel must equal this
                    number&apos;s paired phone (digits only):
                  </p>
                  <p className="mt-1 font-mono">
                    {number.phone_number ?? (
                      <span className="text-destructive">
                        Number not paired yet — pair the QR first
                      </span>
                    )}
                  </p>
                </div>
              </>
            )}

            {isNeotelCustom && (
              <>
                <FormField
                  control={form.control}
                  name="neotelAccountId"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Account ID</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="e.g. acme-prod-line-1"
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        The <code>accountId</code> we send to Neotel on every
                        inbound message. Neotel echoes it back when it POSTs
                        agent replies, so we use it to route the outbound
                        callback to this number. Pick something stable and
                        unique across your numbers.
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {callbackUrl && (
                  <div className="rounded-md border border-emerald-500/40 bg-emerald-500/5 p-3 text-sm">
                    <p className="font-medium">Outbound callback URL</p>
                    <p className="mt-1 text-muted-foreground">
                      Paste this into Neotel&apos;s Custom Provider configuration
                      as the <code>Host URL</code>. Treat it like a secret —
                      anyone with this URL can dispatch messages through your
                      number.
                    </p>
                    <div className="mt-2 flex items-stretch gap-2">
                      <code className="flex-1 overflow-x-auto break-all rounded-md border bg-background p-2 font-mono text-xs">
                        {callbackUrl}
                      </code>
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        onClick={copyCallback}
                        aria-label="Copy callback URL"
                      >
                        {copiedCallback ? (
                          <Check className="size-4" />
                        ) : (
                          <Copy className="size-4" />
                        )}
                      </Button>
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">
                      For local dev, replace the host with your tunneled URL
                      (ngrok / cloudflared) — Neotel must be able to reach it.
                    </p>
                  </div>
                )}

                {!number.phone_number && (
                  <div className="rounded-md border border-amber-500/40 bg-amber-500/5 p-3 text-sm">
                    <span className="text-destructive">
                      Pair the QR before saving
                    </span>{" "}
                    — the <code>contactNumber</code> field requires the paired
                    phone.
                  </div>
                )}
              </>
            )}

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

            {!isApiwha && !isNeotelCustom && (
              <div className="space-y-2">
                <Label>Events</Label>
                <FormDescription>
                  Pick which Evolution events to forward. All five selected =
                  full fan-out.
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
            )}

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
                      <FormLabel>
                        {isNeotelCustom
                          ? "Rotate callback token"
                          : isApiwha
                            ? "Rotate placeholder secret"
                            : "Rotate signing secret"}
                      </FormLabel>
                      <FormDescription>
                        {isNeotelCustom
                          ? "Generates a new token for the outbound callback URL. The old URL stops working — update Neotel's config."
                          : isApiwha
                            ? "Rotates the internal placeholder. Not user-visible."
                            : "Generates a new HMAC secret on save. The old one stops working immediately."}
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
              {update.isPending ? "Saving…" : "Save"}
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
