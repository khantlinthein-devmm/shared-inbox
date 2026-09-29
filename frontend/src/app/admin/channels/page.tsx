"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Check, Copy } from "lucide-react";
import { connectChannel, disconnectChannel, getChannels, setPublicUrl } from "@/lib/api";
import { channelBadgeClass } from "@/lib/format";
import type { Channel, ChannelStatus, ChannelsOverview } from "@/lib/types";
import { useAuthStore } from "@/stores/authStore";
import { useMounted } from "@/hooks/useMounted";
import { ThemeToggle } from "@/components/ThemeToggle";

const inputClass =
  "w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm outline-none transition placeholder:text-zinc-400 focus:border-brand-400 focus:ring-4 focus:ring-brand-500/15 dark:border-zinc-700 dark:bg-zinc-800";

interface FieldSpec {
  key: string;
  label: string;
  secret?: boolean;
  help: string;
}

const FIELDS: Record<Channel, FieldSpec[]> = {
  telegram: [{ key: "bot_token", label: "Bot token", secret: true, help: "Telegram → @BotFather → /newbot" }],
  viber: [{ key: "auth_token", label: "Auth token", secret: true, help: "partners.viber.com → your bot → Auth token" }],
  messenger: [
    { key: "page_access_token", label: "Page access token", secret: true, help: "Meta app → Messenger → Generate token for your Page" },
    { key: "app_secret", label: "App secret", secret: true, help: "Meta app → App settings → Basic → App secret" },
  ],
  whatsapp: [
    { key: "access_token", label: "Access token", secret: true, help: "Permanent System User token with whatsapp_business_messaging" },
    { key: "phone_number_id", label: "Phone number ID", help: "Meta app → WhatsApp → API Setup" },
    { key: "app_secret", label: "App secret", secret: true, help: "Meta app → App settings → Basic → App secret" },
  ],
};

const DETAIL_LABELS: Record<string, (v: string) => string> = {
  bot_username: (v) => `@${v}`,
  account_name: (v) => v,
  page_name: (v) => `Page: ${v}`,
  display_phone: (v) => v,
  verified_name: (v) => v,
};

function CopyField({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div>
      <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-400">{label}</p>
      <div className="mt-1 flex items-center gap-2">
        <code className="min-w-0 flex-1 truncate rounded-lg bg-zinc-100 px-2 py-1.5 text-xs dark:bg-zinc-800">{value}</code>
        <button
          type="button"
          onClick={() => {
            void navigator.clipboard?.writeText(value);
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          }}
          className="rounded-lg p-1.5 text-zinc-500 transition hover:bg-zinc-100 dark:hover:bg-zinc-800"
          title={`Copy ${label}`}
        >
          {copied ? <Check className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}

function ChannelCard({ status, onChange }: { status: ChannelStatus; onChange: (s: ChannelStatus) => void }) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [autoReply, setAutoReply] = useState(status.fields.auto_reply ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [warnings, setWarnings] = useState<string[]>([]);
  const fields = FIELDS[status.channel];
  const isMeta = status.channel === "messenger" || status.channel === "whatsapp";

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setWarnings([]);
    try {
      const updated = await connectChannel(status.channel, { ...values, auto_reply: autoReply });
      onChange(updated);
      setWarnings(updated.warnings ?? []);
      setValues({});
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connection failed");
    } finally {
      setBusy(false);
    }
  }

  async function onDisconnect() {
    if (!window.confirm(`Disconnect ${status.label}? New messages will stop arriving.`)) return;
    setBusy(true);
    setError("");
    try {
      onChange(await disconnectChannel(status.channel));
      setWarnings([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Disconnect failed");
    } finally {
      setBusy(false);
    }
  }

  const details = Object.entries(status.details)
    .filter(([key]) => DETAIL_LABELS[key])
    .map(([key, value]) => DETAIL_LABELS[key](value));

  return (
    <form
      onSubmit={onSubmit}
      aria-label={`${status.label} settings`}
      className="flex flex-col gap-3 rounded-2xl border border-zinc-200 bg-white p-5 shadow-soft dark:border-zinc-800 dark:bg-zinc-900"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${channelBadgeClass(status.channel)}`}>
            {status.label}
          </span>
          {details.length > 0 && <p className="mt-1.5 text-sm font-medium">{details.join(" · ")}</p>}
        </div>
        <span
          className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold ${
            status.connected
              ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
              : "bg-zinc-500/10 text-zinc-500"
          }`}
        >
          {status.connected ? (status.source === "env" ? "Connected (.env)" : "Connected") : "Not connected"}
        </span>
      </div>

      {fields.map((field) => (
        <label key={field.key} className="block">
          <span className="text-xs font-medium">{field.label}</span>
          <input
            type={field.secret ? "password" : "text"}
            autoComplete="off"
            value={values[field.key] ?? ""}
            onChange={(e) => setValues((v) => ({ ...v, [field.key]: e.target.value }))}
            placeholder={status.fields[field.key] ? `${status.fields[field.key]} (leave blank to keep)` : ""}
            className={`${inputClass} mt-1`}
          />
          <span className="mt-0.5 block text-[11px] text-zinc-400">{field.help}</span>
        </label>
      ))}

      <label className="block">
        <span className="text-xs font-medium">Auto-reply (optional)</span>
        <input
          value={autoReply}
          onChange={(e) => setAutoReply(e.target.value)}
          placeholder="Sent automatically when a customer writes"
          className={`${inputClass} mt-1`}
        />
      </label>

      {status.connected && status.webhook_auto && (
        <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
          Webhook is registered automatically at <code className="break-all">{status.webhook_url}</code>
        </p>
      )}

      {status.connected && isMeta && status.verify_token && (
        <div className="space-y-2 rounded-xl border border-blue-200 bg-blue-50/60 p-3 dark:border-blue-500/30 dark:bg-blue-500/5">
          <p className="text-xs font-semibold">Finish in the Meta App Dashboard</p>
          <p className="text-[11px] text-zinc-600 dark:text-zinc-400">
            {status.channel === "messenger" ? "Messenger" : "WhatsApp"} → Webhooks → paste these two values, verify, then
            subscribe to <b>messages</b>
            {status.channel === "messenger" ? ", message_deliveries and message_reads" : ""}.
          </p>
          <CopyField label="Callback URL" value={status.webhook_url} />
          <CopyField label="Verify token" value={status.verify_token} />
        </div>
      )}

      {warnings.map((w) => (
        <p key={w} className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:bg-amber-500/10 dark:text-amber-300">
          {w}
        </p>
      ))}
      {error && <p className="text-xs text-red-600 dark:text-red-400">{error}</p>}

      <div className="mt-auto flex gap-2 pt-1">
        <button
          type="submit"
          disabled={busy}
          className="rounded-xl bg-gradient-to-r from-brand-600 to-violet-600 px-4 py-2 text-sm font-medium text-white shadow-soft transition hover:brightness-110 disabled:opacity-50"
        >
          {busy ? "Checking…" : status.connected ? "Save" : "Connect"}
        </button>
        {status.connected && status.source === "ui" && (
          <button
            type="button"
            onClick={() => void onDisconnect()}
            disabled={busy}
            className="rounded-xl bg-red-50 px-4 py-2 text-sm font-medium text-red-600 transition hover:bg-red-100 disabled:opacity-50 dark:bg-red-500/10 dark:text-red-400"
          >
            Disconnect
          </button>
        )}
      </div>
    </form>
  );
}

export default function AdminChannelsPage() {
  const router = useRouter();
  const mounted = useMounted();
  const token = useAuthStore((s) => s.token);
  const me = useAuthStore((s) => s.user);
  const [overview, setOverview] = useState<ChannelsOverview | null>(null);
  const [publicUrl, setPublicUrlInput] = useState("");
  const [urlBusy, setUrlBusy] = useState(false);
  const [urlMessage, setUrlMessage] = useState<{ text: string; error?: boolean } | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (mounted && !token) router.replace("/login");
  }, [mounted, token, router]);

  useEffect(() => {
    if (!token || me?.role !== "admin") return;
    getChannels()
      .then((data) => {
        setOverview(data);
        setPublicUrlInput(data.public_url);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [token, me?.role]);

  if (!mounted || !token || !me) return null;
  if (me.role !== "admin") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-zinc-100 dark:bg-zinc-950">
        <div className="rounded-2xl border border-zinc-200 bg-white p-8 text-sm shadow-soft dark:border-zinc-800 dark:bg-zinc-900">
          <p className="font-semibold">Admins only</p>
          <Link href="/dashboard" className="mt-2 block text-brand-600 underline dark:text-brand-300">
            Back to dashboard
          </Link>
        </div>
      </main>
    );
  }

  async function onSaveUrl(e: FormEvent) {
    e.preventDefault();
    setUrlBusy(true);
    setUrlMessage(null);
    try {
      const data = await setPublicUrl(publicUrl);
      setOverview(data);
      setPublicUrlInput(data.public_url);
      const problems = Object.entries(data.warnings ?? {}).map(([ch, w]) => `${ch}: ${w}`);
      setUrlMessage(
        problems.length
          ? { text: problems.join(" "), error: true }
          : { text: "Saved. Connected Telegram/Viber webhooks now point here." }
      );
    } catch (err) {
      setUrlMessage({ text: err instanceof Error ? err.message : "Save failed", error: true });
    } finally {
      setUrlBusy(false);
    }
  }

  function updateChannel(updated: ChannelStatus) {
    setOverview((o) => o && { ...o, channels: o.channels.map((c) => (c.channel === updated.channel ? updated : c)) });
  }

  return (
    <main className="min-h-screen bg-zinc-100 px-4 py-8 dark:bg-zinc-950">
      <div className="mx-auto w-full max-w-4xl">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <h1 className="text-lg font-semibold tracking-tight">Channels</h1>
          </div>
          <Link href="/dashboard" className="text-sm text-brand-600 underline dark:text-brand-300">
            Back to dashboard
          </Link>
        </div>

        {error && <p className="mb-4 text-sm text-red-600 dark:text-red-400">{error}</p>}

        <form
          onSubmit={onSaveUrl}
          className="mb-4 space-y-2 rounded-2xl border border-zinc-200 bg-white p-5 shadow-soft dark:border-zinc-800 dark:bg-zinc-900"
        >
          <label className="block">
            <span className="text-sm font-semibold">Public server URL</span>
            <span className="mt-0.5 block text-xs text-zinc-500 dark:text-zinc-400">
              The https address messaging apps use to reach this server (e.g. your ngrok URL). Update it here whenever it
              changes.
            </span>
            <div className="mt-2 flex gap-2">
              <input
                value={publicUrl}
                onChange={(e) => setPublicUrlInput(e.target.value)}
                placeholder="https://your-name.ngrok-free.app"
                className={inputClass}
              />
              <button
                type="submit"
                disabled={urlBusy}
                className="shrink-0 rounded-xl bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:brightness-110 disabled:opacity-50"
              >
                {urlBusy ? "Saving…" : "Save"}
              </button>
            </div>
          </label>
          {overview && !overview.public_url_ok && (
            <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:bg-amber-500/10 dark:text-amber-300">
              Messaging apps can&apos;t reach {overview.public_url}. Set a public https URL before connecting channels.
            </p>
          )}
          {urlMessage && (
            <p className={`text-xs ${urlMessage.error ? "text-red-600 dark:text-red-400" : "text-emerald-600 dark:text-emerald-400"}`}>
              {urlMessage.text}
            </p>
          )}
        </form>

        <div className="grid gap-4 md:grid-cols-2">
          {overview?.channels.map((status) => (
            <ChannelCard key={status.channel} status={status} onChange={updateChannel} />
          ))}
        </div>
      </div>
    </main>
  );
}
