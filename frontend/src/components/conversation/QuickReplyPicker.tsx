"use client";

import { useEffect, useState } from "react";
import { listQuickReplies } from "@/lib/api";
import type { QuickReply } from "@/lib/types";

export function QuickReplyPicker({ onPick }: { onPick: (text: string) => void }) {
  const [replies, setReplies] = useState<QuickReply[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    listQuickReplies()
      .then(setReplies)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load quick replies"));
  }, []);

  if (error) return <p className="mt-2 text-xs text-red-600 dark:text-red-400">{error}</p>;
  if (replies === null) return <p className="mt-2 text-xs text-zinc-400">Loading quick replies…</p>;
  if (replies.length === 0) {
    return <p className="mt-2 text-xs text-zinc-400">No quick replies yet. An admin can add them under Quick Replies.</p>;
  }

  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {replies.map((reply) => (
        <button
          key={reply.id}
          onClick={() => onPick(reply.content)}
          title={reply.content}
          className="rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700 transition hover:bg-brand-100 dark:border-brand-500/40 dark:bg-brand-500/10 dark:text-brand-200 dark:hover:bg-brand-500/20"
        >
          {reply.title}
        </button>
      ))}
    </div>
  );
}
