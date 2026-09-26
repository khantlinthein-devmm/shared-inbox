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
}: {
  value: ConversationStatus | "";
  onChange: (value: ConversationStatus | "") => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
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