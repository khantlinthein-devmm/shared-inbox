"use client";

import { ExternalLink } from "lucide-react";
import { Check, CheckCheck } from "lucide-react";
import { formatTime } from "@/lib/format";
import { useMounted } from "@/hooks/useMounted";
import type { Message } from "@/lib/types";

const STATUS_ICONS: Record<string, React.ReactNode> = {
  sent: <Check className="h-3 w-3" />,
  delivered: <CheckCheck className="h-3 w-3" />,
  seen: <CheckCheck className="h-3 w-3 text-white/80" />,
  received: null,
};

const IMAGE_EXT = /\.(png|jpe?g|gif|webp)$/i;

function Attachment({ message }: { message: Message }) {
  const media = message.media_url;
  if (!media) return null;

  if (IMAGE_EXT.test(media)) {
    return (
      <a href={media} target="_blank" rel="noreferrer" className="block">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={media}
          alt={message.text ?? "attachment"}
          className="max-h-60 w-full rounded-lg object-cover"
        />
      </a>
    );
  }

  return (
    <a
      href={media}
      target="_blank"
      rel="noreferrer"
      className="flex items-center gap-2 rounded-xl bg-zinc-100 px-3 py-2 text-sm font-medium text-zinc-700 transition hover:bg-zinc-200 dark:bg-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-600"
    >
      <ExternalLink className="h-4 w-4" />
      <span className="truncate">{message.text ?? "Attachment"}</span>
    </a>
  );
}

export function MessageBubble({ message }: { message: Message }) {
  const isOwn = message.sender === "agent";
  // formatTime depends on the browser timezone, which differs from the
  // server render. Render a stable placeholder until mounted to avoid
  // hydration mismatches.
  const mounted = useMounted();

  return (
    <div className={`flex animate-fade-up ${isOwn ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[70%] rounded-2xl px-3.5 py-2 ${
          isOwn
            ? "rounded-br-md bg-gradient-to-br from-brand-500 to-violet-600 text-white shadow-soft"
            : "rounded-bl-md border border-zinc-200 bg-white text-zinc-800 shadow-sm dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
        }`}
      >
        {!isOwn && message.sender_name && (
          <p className="text-xs font-medium text-brand-600 dark:text-brand-300">{message.sender_name}</p>
        )}
        <Attachment message={message} />
        {message.text && (
          <p className="mt-1 whitespace-pre-wrap break-words text-sm">{message.text}</p>
        )}
        <div
          className={`mt-1 flex items-center justify-end gap-1 text-[10px] ${
            isOwn ? "text-brand-100" : "text-zinc-400"
          }`}
        >
          {mounted ? formatTime(message.created_at) : ""}
          {isOwn && STATUS_ICONS[message.status]}
        </div>
      </div>
    </div>
  );
}