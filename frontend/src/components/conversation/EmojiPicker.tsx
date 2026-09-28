"use client";

import { useEffect, useRef } from "react";

const EMOJIS = [
  "😀", "😃", "😄", "😁", "😊", "🙂", "😉", "😍", "🥰", "😘", "😋", "😎",
  "🤗", "🤔", "😐", "😅", "😂", "🤣", "😢", "😭", "😮", "😴", "😷", "🥺",
  "😡", "😤", "🙏", "👍", "👎", "👌", "👏", "🙌", "👋", "🤝", "💪", "✌️",
  "❤️", "🧡", "💛", "💚", "💙", "💜", "💯", "✨", "🔥", "🎉", "🎁", "⭐",
  "✅", "❌", "⚠️", "❓", "❗", "📦", "🚚", "💰", "💳", "🧾", "📞", "📍",
  "⏰", "📅", "📷", "📎", "💬", "📝", "🛒", "🏠", "☕", "🌸", "🌞", "🌧️",
];

export function EmojiPicker({ onPick, onClose }: { onPick: (emoji: string) => void; onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  return (
    <div
      ref={ref}
      role="dialog"
      aria-label="Emoji picker"
      className="absolute bottom-full left-0 z-20 mb-2 grid w-80 grid-cols-8 gap-1 rounded-2xl border border-zinc-200 bg-white p-2 shadow-lg dark:border-zinc-700 dark:bg-zinc-900"
    >
      {EMOJIS.map((emoji) => (
        <button
          key={emoji}
          type="button"
          onClick={() => onPick(emoji)}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-xl transition hover:bg-zinc-100 dark:hover:bg-zinc-800"
        >
          {emoji}
        </button>
      ))}
    </div>
  );
}
