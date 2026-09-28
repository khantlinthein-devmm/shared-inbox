"use client";

import { useRef, useState } from "react";
import { ListPlus, Mic, Paperclip, Send, Smile, Trash2, X } from "lucide-react";
import { listConversations, sendMessage, uploadAttachment } from "@/lib/api";
import { useVoiceRecorder } from "@/hooks/useVoiceRecorder";
import { useChatStore } from "@/stores/chatStore";
import type { Conversation } from "@/lib/types";
import { EmojiPicker } from "./EmojiPicker";
import { QuickReplyPicker } from "./QuickReplyPicker";

const iconButton =
  "rounded-xl border border-zinc-200 bg-white p-2.5 text-zinc-600 transition hover:bg-zinc-50 disabled:opacity-40 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800";

function formatDuration(total: number): string {
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

export function MessageComposer({ conversation }: { conversation: Conversation }) {
  const [text, setText] = useState("");
  const [showQuick, setShowQuick] = useState(false);
  const [showEmoji, setShowEmoji] = useState(false);
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recorder = useVoiceRecorder();
  const statusFilter = useChatStore((s) => s.statusFilter);
  const setConversations = useChatStore((s) => s.setConversations);

  async function refreshList() {
    const updated = await listConversations(statusFilter === "" ? undefined : statusFilter);
    setConversations(updated);
  }

  function insertAtCursor(snippet: string) {
    const el = textareaRef.current;
    const start = el?.selectionStart ?? text.length;
    const end = el?.selectionEnd ?? text.length;
    setText(text.slice(0, start) + snippet + text.slice(end));
    requestAnimationFrame(() => {
      el?.focus();
      el?.setSelectionRange(start + snippet.length, start + snippet.length);
    });
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
    setError("");
    try {
      await sendMessage(conversation.id, value);
      setText("");
      setShowQuick(false);
      await refreshList();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Message could not be sent");
    } finally {
      setSending(false);
    }
  }

  async function upload(file: File, voice = false) {
    setUploading(true);
    setError("");
    try {
      await uploadAttachment(conversation.id, file, { voice });
      setShowQuick(false);
      await refreshList();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function onFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (file && !uploading) await upload(file);
  }

  async function startRecording() {
    setError("");
    try {
      await recorder.start();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start recording");
    }
  }

  async function sendRecording() {
    const file = await recorder.stop();
    if (file) await upload(file, true);
  }

  return (
    <div className="border-t border-zinc-200 bg-white p-3 dark:border-zinc-800 dark:bg-zinc-900">
      {recorder.recording ? (
        <div className="flex items-center gap-2">
          <button onClick={recorder.cancel} className={iconButton} title="Discard recording">
            <Trash2 className="h-5 w-5" />
          </button>
          <div className="flex flex-1 items-center gap-2 rounded-xl bg-red-50 px-4 py-2.5 text-sm font-medium text-red-600 dark:bg-red-500/10 dark:text-red-400">
            <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-red-500" />
            Recording {formatDuration(recorder.seconds)}
          </div>
          <button
            onClick={() => void sendRecording()}
            className="rounded-xl bg-gradient-to-br from-brand-500 to-violet-600 p-2.5 text-white shadow-soft transition hover:brightness-110"
            title="Send voice message"
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
      ) : (
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

          <div className="relative">
            <button onClick={() => setShowEmoji((v) => !v)} className={iconButton} title="Emoji">
              <Smile className="h-5 w-5" />
            </button>
            {showEmoji && <EmojiPicker onPick={insertAtCursor} onClose={() => setShowEmoji(false)} />}
          </div>

          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className={iconButton}
            title="Send a photo, video or file"
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

          <button
            onClick={() => void startRecording()}
            disabled={uploading}
            className={iconButton}
            title="Record a voice message"
          >
            <Mic className="h-5 w-5" />
          </button>

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
      )}

      {uploading && <p className="mt-2 text-xs text-zinc-400">Sending attachment…</p>}
      {error && <p className="mt-2 text-xs text-red-600 dark:text-red-400">{error}</p>}
      {showQuick && !recorder.recording && <QuickReplyPicker onPick={insertQuickReply} />}
    </div>
  );
}
