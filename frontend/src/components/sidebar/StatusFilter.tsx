"use client";

import type { ConversationStatus } from "@/lib/types";

const FILTERS: Array<{ value: ConversationStatus | ""; label: string }> = [
  { value: "", label: "All" },
  { value: "unassigned", label: "Unassigned" },
  { value: "open", label: "Open" },
  { value: "pending", label: "Pending" },
  { value: "closed", label: "Closed" },
];

export function StatusFilter({
  value,
  onChange,
  mineOnly,
  onMineOnlyChange,
}: {
  value: ConversationStatus | "";
  onChange: (value: ConversationStatus | "") => void;
  mineOnly: boolean;
  onMineOnlyChange: (mineOnly: boolean) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      <button
        onClick={() => onMineOnlyChange(!mineOnly)}
        aria-pressed={mineOnly}
        className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
          mineOnly
            ? "border-violet-600 bg-violet-600 text-white shadow-soft"
            : "border-violet-200 text-violet-700 hover:bg-violet-50 dark:border-violet-500/40 dark:text-violet-300 dark:hover:bg-violet-500/10"
        }`}
        title="Only conversations assigned to me"
      >
        Mine
      </button>
      {FILTERS.map((filter) => (
        <button
          key={filter.label}
          onClick={() => onChange(filter.value)}
          className={`rounded-full px-3 py-1 text-xs font-medium transition ${
            value === filter.value
              ? "bg-brand-600 text-white shadow-soft"
              : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700"
          }`}
        >
          {filter.label}
        </button>
      ))}
    </div>
  );
}