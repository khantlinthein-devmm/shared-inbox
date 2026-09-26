"use client";

import { useEffect, useMemo, useState } from "react";
import { listConversations } from "@/lib/api";
import { useChatStore } from "@/stores/chatStore";

/**
 * Loads the conversation list (server-filtered by status) plus a 15s polling
 * fallback. Real-time updates arrive via useWebSocket -> chatStore.applyEvent.
 */
export function useConversations() {
  const conversations = useChatStore((s) => s.conversations);
  const statusFilter = useChatStore((s) => s.statusFilter);
  const searchQuery = useChatStore((s) => s.searchQuery);
  const setConversations = useChatStore((s) => s.setConversations);
  const setStatusFilter = useChatStore((s) => s.setStatusFilter);
  const setSearchQuery = useChatStore((s) => s.setSearchQuery);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);

    const load = () =>
      listConversations(statusFilter === "" ? undefined : statusFilter)
        .then((rows) => {
          if (active) setConversations(rows);
        })
        .catch(() => {})
        .finally(() => {
          if (active) setLoading(false);
        });

    load();
    const poll = setInterval(load, 15_000);
    return () => {
      active = false;
      clearInterval(poll);
    };
  }, [statusFilter, setConversations]);

  const filtered = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return conversations;
    return conversations.filter(
      (c) =>
        c.contact_name.toLowerCase().includes(query) ||
        (c.last_message ?? "").toLowerCase().includes(query)
    );
  }, [conversations, searchQuery]);

  return {
    filtered,
    loading,
    statusFilter,
    setStatusFilter,
    searchQuery,
    setSearchQuery,
  };
}