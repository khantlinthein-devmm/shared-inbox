"use client";

import { useState } from "react";
import { Bell, BellOff } from "lucide-react";
import { notificationsEnabled, setNotificationsEnabled, unlockAudio } from "@/lib/notify";

function permission(): NotificationPermission | "unsupported" {
  return typeof window !== "undefined" && "Notification" in window ? Notification.permission : "unsupported";
}

export function NotificationToggle() {
  const [enabled, setEnabled] = useState(notificationsEnabled);
  const [perm, setPerm] = useState(permission);

  // While alerts are on but desktop permission is still undecided, a click
  // asks for permission; otherwise it toggles alerts on/off.
  async function onClick() {
    unlockAudio();
    if (perm === "default") setPerm(await Notification.requestPermission());
    if (enabled && perm === "default") return;
    const next = !enabled;
    setNotificationsEnabled(next);
    setEnabled(next);
  }

  const title = !enabled
    ? "Alerts off — click to enable"
    : perm === "granted"
      ? "Sound + desktop alerts on"
      : perm === "default"
        ? "Sound alerts on — click to allow desktop notifications"
        : "Sound alerts on (desktop notifications blocked in browser settings)";

  return (
    <button
      onClick={() => void onClick()}
      className={`flex h-8 w-8 items-center justify-center rounded-full transition hover:bg-zinc-100 dark:hover:bg-zinc-800 ${
        enabled ? "text-brand-600 dark:text-brand-300" : "text-zinc-400"
      }`}
      title={title}
      aria-label={title}
    >
      {enabled ? <Bell className="h-4 w-4" /> : <BellOff className="h-4 w-4" />}
    </button>
  );
}
