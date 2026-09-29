"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { getConversationDetail } from "@/lib/api";
import { useChatStore } from "@/stores/chatStore";
import { statusLabel } from "@/lib/format";
import { Message } from "@/lib/types";
import { ContactAvatar } from "@/components/ContactAvatar";
import { CallButtons } from "./CallButtons";
import { MessageBubble } from "./MessageBubble";
import { MessageComposer } from "./MessageComposer";

export function ConversationThread() {
  const conversationId = useChatStore((s) => s.activeConversationId);
  const conversations = useChatStore((s) => s.conversations);
  const setMessages = useChatStore((s) => s.setMessages);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [callError, setCallError] = useState("");

  useEffect(() => setCallError(""), [conversationId]);

  const conversation = useMemo(
    () => conversations.find((c) => c.id === conversationId),
    [conversations, conversationId]
  );

  const loadedMessages = useChatStore((s) =>
    conversationId ? (s.messages[conversationId] ?? []) : []
  );
  const messages = useMemo(
    () => [...loadedMessages].sort((a, b) => a.created_at.localeCompare(b.created_at)),
    [loadedMessages]
  );

  useEffect(() => {
    if (!conversationId) return;
    let active = true;
    getConversationDetail(conversationId)
      .then((detail) => {
        if (active) setMessages(conversationId, detail.messages);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [conversationId, setMessages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, conversationId]);

  if (!conversation) return null;

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-3 border-b border-zinc-200 bg-white/80 px-5 py-3 backdrop-blur-xl dark:border-zinc-800 dark:bg-zinc-900/80">
        <ContactAvatar name={conversation.contact_name} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold tracking-tight">{conversation.contact_name}</p>
          <p className="truncate font-mono text-[11px] text-zinc-400">{conversation.contact_user_id}</p>
        </div>
        <CallButtons conversationId={conversation.id} onError={setCallError} />
        <span className="rounded-full bg-brand-500/10 px-2.5 py-1 text-[11px] font-semibold text-brand-700 dark:text-brand-300">
          {statusLabel(conversation.status)}
        </span>
      </header>
      {callError && (
        <p className="border-b border-red-200 bg-red-50 px-5 py-2 text-xs text-red-600 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
          Call failed: {callError}
        </p>
      )}

      <div className="flex-1 space-y-3 overflow-y-auto bg-zinc-50 p-5 dark:bg-zinc-950">
        {messages.map((msg: Message) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      <MessageComposer conversation={conversation} />
    </div>
  );
}