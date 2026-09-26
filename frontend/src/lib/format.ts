import type { ConversationStatus, MessageStatus } from "./types";

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

export function messageStatusName(status: MessageStatus): string {
  const map: Record<string, string> = {
    received: "Received",
    sent: "Sent",
    delivered: "Delivered",
    seen: "Seen",
  };
  return map[status] ?? status;
}