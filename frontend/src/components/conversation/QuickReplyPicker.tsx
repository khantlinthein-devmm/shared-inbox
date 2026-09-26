"use client";

import { QUICK_REPLIES } from "@/lib/quickReplies";

export function QuickReplyPicker({ onPick }: { onPick: (text: string) => void }) {
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {QUICK_REPLIES.map((reply) => (
        <button
          key={reply}
          onClick={() => onPick(reply)}
          className="rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700 transition hover:bg-brand-100 dark:border-brand-500/40 dark:bg-brand-500/10 dark:text-brand-200 dark:hover:bg-brand-500/20"
        >
          {reply}
        </button>
      ))}
    </div>
  );
}