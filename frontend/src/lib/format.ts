import type { Channel, ConversationStatus, MessageStatus } from "./types";

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Intl.DateTimeFormat("en", { hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
}

export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return "";
  const date = new Date(iso);
  const diffMs = Date.now() - date.getTime();
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return "now";
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(date);
}

export function statusLabel(status: ConversationStatus | string): string {
  const map: Record<string, string> = {
    unassigned: "Unassigned",
    open: "Open",
    pending: "Pending",
    closed: "Closed",
  };
  return map[status] ?? status;
}

export function statusDotClass(status: ConversationStatus | string): string {
  const map: Record<string, string> = {
    unassigned: "bg-zinc-400",
    open: "bg-emerald-500",
    pending: "bg-amber-500",
    closed: "bg-zinc-300 dark:bg-zinc-600",
  };
  return map[status] ?? "bg-zinc-400";
}

export function channelLabel(channel: Channel | string): string {
  const map: Record<string, string> = {
    viber: "Viber",
    telegram: "Telegram",
    messenger: "Messenger",
    whatsapp: "WhatsApp",
  };
  return map[channel] ?? channel;
}

export function channelBadgeClass(channel: Channel | string): string {
  const map: Record<string, string> = {
    viber: "bg-violet-100 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300",
    telegram: "bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300",
    messenger: "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
    whatsapp: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
  };
  return map[channel] ?? "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300";
}

export function messageStatusName(status: MessageStatus): string {
  const map: Record<string, string> = {
    received: "Received",
    sent: "Sent",
    delivered: "Delivered",
    seen: "Seen",
  };
  return map[status] ?? status;
}