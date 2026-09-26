"use client";

const GRADIENTS = [
  "from-brand-500 to-violet-600",
  "from-fuchsia-500 to-brand-600",
  "from-indigo-500 to-brand-600",
  "from-violet-500 to-purple-700",
  "from-purple-500 to-brand-700",
  "from-brand-400 to-indigo-600",
];

function hashName(name: string): number {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  }
  return hash % GRADIENTS.length;
}

export function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function ContactAvatar({
  name,
  size = "md",
}: {
  name: string;
  size?: "sm" | "md" | "lg";
}) {
  const dims =
    size === "sm" ? "h-8 w-8 text-[11px]" : size === "lg" ? "h-11 w-11 text-sm" : "h-10 w-10 text-xs";
  return (
    <div
      aria-hidden
      className={`flex shrink-0 items-center justify-center rounded-full bg-gradient-to-br font-semibold text-white shadow-soft ${GRADIENTS[hashName(name)]} ${dims}`}
    >
      {initialsOf(name)}
    </div>
  );
}
