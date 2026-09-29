"use client";

import { useState } from "react";
import { Phone, Video } from "lucide-react";
import { startCall } from "@/lib/api";

const buttonClass =
  "flex h-9 w-9 items-center justify-center rounded-full text-zinc-500 transition hover:bg-brand-50 hover:text-brand-600 disabled:opacity-40 dark:text-zinc-400 dark:hover:bg-brand-500/10 dark:hover:text-brand-300";

export function CallButtons({
  conversationId,
  onError,
}: {
  conversationId: number;
  onError: (message: string) => void;
}) {
  const [busy, setBusy] = useState(false);

  async function call(video: boolean) {
    onError("");
    // Open the tab synchronously inside the click so popup blockers allow it,
    // then point it at the room once the backend has sent the invite.
    const tab = window.open("about:blank", "_blank");
    setBusy(true);
    try {
      const { join_url } = await startCall(conversationId, video);
      if (tab) {
        tab.opener = null;
        tab.location.href = join_url;
      } else {
        window.open(join_url, "_blank", "noopener");
      }
    } catch (err) {
      tab?.close();
      onError(err instanceof Error ? err.message : "Could not start the call");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-1">
      <button onClick={() => void call(false)} disabled={busy} className={buttonClass} title="Voice call">
        <Phone className="h-4 w-4" />
      </button>
      <button onClick={() => void call(true)} disabled={busy} className={buttonClass} title="Video call">
        <Video className="h-4 w-4" />
      </button>
    </div>
  );
}
