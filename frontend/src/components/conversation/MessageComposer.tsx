"use client";

import { useRef, useState } from "react";
import { ListPlus, Paperclip, Send, X } from "lucide-react";
import { listConversations, sendMessage, uploadAttachment } from "@/lib/api";
import { useChatStore } from "@/stores/chatStore";
import type { Conversation } from "@/lib/types";
import { QuickReplyPicker } from "./QuickReplyPicker";

export function MessageComposer({ conversation }: { conversation: Conversation }) {
  const [text, setText] = useState("");
  const [showQuick, setShowQuick] = useState(false);
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const statusFilter = useChatStore((s) => s.statusFilter);
  const setConversations = useChatStore((s) => s.setConversations);

  async function refreshList() {
    const updated = await listConversations(statusFilter === "" ? undefined : statusFilter);
    setConversations(updated);
  }

  function insertQuickReply(content: string) {
    setText((current) => (current.trim() ? `${current.trimEnd()} ${content}` : content));
    setShowQuick(false);
    textareaRef.current?.focus();
  }

  async function send() {
    const value = text.trim();
    if (!value || sending) return;
    setSending(true);
    try {
      await sendMessage(conversation.id, value);
      setText("");
      setShowQuick(false);
      await refreshList();
    } catch {
      /* surface via console; realtime WS will reconcile anyway */
    } finally {
      setSending(false);
    }
  }

  async function onFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || uploading) return;
    setUploading(true);
    try {
      await uploadAttachment(conversation.id, file);
      setShowQuick(false);
      await refreshList();
    } catch {
      /* ignore; WS will reconcile / user sees server error in console */
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="border-t border-zinc-200 bg-white p-3 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-end gap-2">
        <button
          onClick={() => setShowQuick((v) => !v)}
          className={`flex items-center gap-1.5 rounded-xl border px-3 py-2.5 text-xs font-medium transition ${
            showQuick
              ? "border-brand-300 bg-brand-50 text-brand-700 dark:border-brand-500 dark:bg-brand-500/10 dark:text-brand-300"
              : "border-zinc-200 bg-white text-zinc-600 hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
          }`}
          title="Quick replies"
        >
          {showQuick ? <X className="h-4 w-4" /> : <ListPlus className="h-4 w-4" />}
          Quick Replies
        </button>

        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="rounded-xl border border-zinc-200 bg-white p-2.5 text-zinc-600 transition hover:bg-zinc-50 disabled:opacity-40 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
          title="Attach a file"
        >
          <Paperclip className="h-5 w-5" />
        </button>
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          onChange={onFileSelected}
          data-testid="attach-input"
        />
        {uploading && <span className="text-xs text-zinc-400">Uploading…</span>}

        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
          placeholder="Type a reply…"
          className="flex-1 resize-none rounded-xl border border-transparent bg-zinc-100 px-4 py-2.5 text-sm outline-none transition placeholder:text-zinc-400 focus:border-brand-400 focus:bg-white focus:ring-4 focus:ring-brand-500/15 dark:bg-zinc-800 dark:focus:bg-zinc-900"
        />

        <button
          onClick={() => void send()}
          disabled={!text.trim() || sending}
          className="rounded-xl bg-gradient-to-br from-brand-500 to-violet-600 p-2.5 text-white shadow-soft transition hover:brightness-110 disabled:opacity-40"
          title="Send"
        >
          <Send className="h-5 w-5" />
        </button>
      </div>

      {showQuick && <QuickReplyPicker onPick={insertQuickReply} />}
    </div>
  );
}