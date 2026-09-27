"use client";

import { Inbox, Search } from "lucide-react";
import { useConversations } from "@/hooks/useConversations";
import { useMounted } from "@/hooks/useMounted";
import { channelBadgeClass, channelLabel, formatRelative, statusDotClass, statusLabel } from "@/lib/format";
import { useChatStore } from "@/stores/chatStore";
import { ContactAvatar } from "@/components/ContactAvatar";
import { StatusFilter } from "./StatusFilter";

export function ConversationList() {
  const {
    filtered,
    statusFilter,
    setStatusFilter,
    searchQuery,
    setSearchQuery,
  } = useConversations();
  const activeId = useChatStore((s) => s.activeConversationId);
  const setActiveConversation = useChatStore((s) => s.setActiveConversation);
  // formatRelative uses Date.now(), which differs between the server render
  // and client hydration. Render a stable placeholder until mounted.
  const mounted = useMounted();

  return (
    <aside className="flex h-full w-[340px] shrink-0 flex-col border-r border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
      <div className="space-y-3 border-b border-zinc-200 p-3 dark:border-zinc-800">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conversations…"
            className="w-full rounded-xl border border-transparent bg-zinc-100 py-2 pl-9 pr-3 text-sm outline-none transition placeholder:text-zinc-400 focus:border-brand-400 focus:bg-white focus:ring-4 focus:ring-brand-500/15 dark:bg-zinc-800 dark:focus:bg-zinc-900"
          />
        </div>
        <StatusFilter value={statusFilter} onChange={setStatusFilter} />
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-12 text-zinc-400">
            <Inbox className="h-8 w-8" />
            <p className="text-sm">No conversations</p>
          </div>
        ) : (
          filtered.map((conversation) => {
            const active = conversation.id === activeId;
            return (
              <button
                key={conversation.id}
                onClick={() => setActiveConversation(conversation.id)}
                className={`relative mb-1 flex w-full gap-3 rounded-2xl px-3 py-3 text-left transition ${
                  active
                    ? "bg-brand-50 shadow-sm ring-1 ring-inset ring-brand-200 dark:bg-brand-500/10 dark:ring-brand-500/30"
                    : "hover:bg-zinc-100 dark:hover:bg-zinc-800"
                }`}
              >
                {active && (
                  <span className="absolute left-0 top-3 h-[calc(100%-1.5rem)] w-1 rounded-full bg-gradient-to-b from-brand-500 to-violet-600" />
                )}
                <ContactAvatar name={conversation.contact_name} size="md" />
                <span className="min-w-0 flex-1">
                  <span className="flex items-center justify-between gap-2">
                    <span
                      className={`truncate text-sm font-semibold ${
                        active ? "text-brand-900 dark:text-brand-100" : ""
                      }`}
                    >
                      {conversation.contact_name}
                    </span>
                    <span className="ml-2 shrink-0 text-[10px] font-medium uppercase tracking-wide text-zinc-400">
                      {mounted ? formatRelative(conversation.last_message_at) : ""}
                    </span>
                  </span>

                  <span className="mt-1 flex items-center gap-1.5">
                    <span
                      className={`shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${channelBadgeClass(
                        conversation.channel
                      )}`}
                    >
                      {channelLabel(conversation.channel)}
                    </span>
                    <span className={`h-2 w-2 shrink-0 rounded-full ${statusDotClass(conversation.status)}`} />
                    <span className="text-[11px] font-medium text-zinc-400">
                      {statusLabel(conversation.status)}
                    </span>
                    <span className="truncate text-xs text-zinc-500 dark:text-zinc-400">
                      {conversation.last_message ?? "No messages yet"}
                    </span>
                  </span>

                  {conversation.assigned_to_full_name && (
                    <span className="mt-1 block truncate text-[10px] text-zinc-400">
                      Assigned to {conversation.assigned_to_full_name}
                    </span>
                  )}
                </span>
              </button>
            );
          })
        )}
      </div>
    </aside>
  );
}