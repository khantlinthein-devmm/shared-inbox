"use client";

import { useEffect, useMemo, useState } from "react";
import { Send, StickyNote, UserRound } from "lucide-react";
import { createNote, listAgents, listNotes, updateConversation } from "@/lib/api";
import { statusLabel } from "@/lib/format";
import { useChatStore } from "@/stores/chatStore";
import type { ConversationStatus } from "@/lib/types";

const STATUSES: ConversationStatus[] = ["unassigned", "open", "pending", "closed"];

export function AgentInfoPanel() {
  const conversationId = useChatStore((s) => s.activeConversationId);
  const conversations = useChatStore((s) => s.conversations);
  const agents = useChatStore((s) => s.agents);
  const setAgents = useChatStore((s) => s.setAgents);
  const setNotes = useChatStore((s) => s.setNotes);
  const addNote = useChatStore((s) => s.addNote);
  const notes = useChatStore((s) =>
    conversationId ? (s.notes[conversationId] ?? []) : []
  );
  const [noteDraft, setNoteDraft] = useState("");
  const [saving, setSaving] = useState(false);

  const conversation = useMemo(
    () => conversations.find((c) => c.id === conversationId),
    [conversations, conversationId]
  );

  useEffect(() => {
    if (!conversationId) return;
    listAgents().then(setAgents).catch(() => {});
    listNotes(conversationId)
      .then((fetched) => setNotes(conversationId, fetched))
      .catch(() => {});
  }, [conversationId, setAgents, setNotes]);

  async function patch(update: Record<string, unknown>) {
    if (!conversation) return;
    try {
      await updateConversation(conversation.id, update);
    } catch {
      /* WS broadcast reconciles UI */
    }
  }

  async function submitNote() {
    const content = noteDraft.trim();
    if (!content || !conversationId || saving) return;
    setSaving(true);
    try {
      const note = await createNote(conversationId, content);
      addNote(note);
      setNoteDraft("");
    } catch {
      /* ignore */
    } finally {
      setSaving(false);
    }
  }

  if (!conversation) return null;

  return (
    <aside className="flex h-full flex-col gap-3 overflow-y-auto p-3">
      <section className="rounded-2xl border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-800 dark:bg-zinc-800/50">
        <h3 className="flex items-center gap-2 text-sm font-semibold tracking-tight">
          <UserRound className="h-4 w-4 text-brand-500" /> Contact
        </h3>
        <dl className="mt-3 space-y-2 text-sm">
          <div>
            <dt className="text-[11px] font-medium uppercase tracking-wide text-zinc-400">Name</dt>
            <dd className="font-medium">{conversation.contact_name}</dd>
          </div>
          <div>
            <dt className="text-[11px] font-medium uppercase tracking-wide text-zinc-400">Viber ID</dt>
            <dd className="truncate font-mono text-xs text-zinc-600 dark:text-zinc-300">
              {conversation.contact_user_id}
            </dd>
          </div>
          <div>
            <dt className="text-[11px] font-medium uppercase tracking-wide text-zinc-400">Messages</dt>
            <dd className="font-medium">{conversation.message_count}</dd>
          </div>
        </dl>
      </section>

      <section className="rounded-2xl border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-800 dark:bg-zinc-800/50">
        <h3 className="text-sm font-semibold tracking-tight">Assignment</h3>

        <label className="mt-3 block text-xs font-medium text-zinc-500 dark:text-zinc-400">Agent</label>
        <select
          value={conversation.assigned_to_id?.toString() ?? ""}
          onChange={(e) => void patch({ assigned_to_id: e.target.value === "" ? 0 : Number(e.target.value) })}
          className="mt-1 w-full rounded-xl border border-zinc-200 bg-white p-2 text-sm outline-none transition focus:border-brand-400 focus:ring-4 focus:ring-brand-500/15 dark:border-zinc-700 dark:bg-zinc-800"
        >
          <option value="">Unassigned</option>
          {agents.map((agent) => (
            <option key={agent.id} value={agent.id}>
              {agent.full_name}
            </option>
          ))}
        </select>

        <label className="mt-3 block text-xs font-medium text-zinc-500 dark:text-zinc-400">Status</label>
        <select
          value={conversation.status}
          onChange={(e) => void patch({ status: e.target.value })}
          className="mt-1 w-full rounded-xl border border-zinc-200 bg-white p-2 text-sm outline-none transition focus:border-brand-400 focus:ring-4 focus:ring-brand-500/15 dark:border-zinc-700 dark:bg-zinc-800"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {statusLabel(s)}
            </option>
          ))}
        </select>
      </section>

      <section className="flex flex-1 flex-col rounded-2xl border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-800 dark:bg-zinc-800/50">
        <h3 className="flex items-center gap-2 text-sm font-semibold tracking-tight">
          <StickyNote className="h-4 w-4 text-brand-500" /> Internal Notes
        </h3>

        <div className="mt-3 flex-1 space-y-2 overflow-y-auto">
          {notes.length === 0 ? (
            <p className="text-xs text-zinc-400">No notes yet.</p>
          ) : (
            notes.map((note) => (
              <div key={note.id} className="rounded-xl border border-amber-200/60 bg-amber-50 p-3 dark:border-amber-400/20 dark:bg-amber-400/10">
                <p className="text-xs font-medium text-zinc-700 dark:text-zinc-200">{note.author_name ?? "Agent"}</p>
                <p className="mt-1 text-xs leading-relaxed text-zinc-600 dark:text-zinc-300">{note.content}</p>
              </div>
            ))
          )}
        </div>

        <div className="mt-3 flex gap-2">
          <input
            value={noteDraft}
            onChange={(e) => setNoteDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void submitNote();
              }
            }}
            placeholder="Add a note…"
            className="flex-1 rounded-xl border border-transparent bg-zinc-100 px-3 py-2 text-sm outline-none transition placeholder:text-zinc-400 focus:border-brand-400 focus:bg-white focus:ring-4 focus:ring-brand-500/15 dark:bg-zinc-800 dark:focus:bg-zinc-900"
          />
          <button
            onClick={() => void submitNote()}
            disabled={!noteDraft.trim() || saving}
            className="rounded-xl bg-gradient-to-br from-brand-500 to-violet-600 p-2 text-white shadow-soft transition hover:brightness-110 disabled:opacity-40"
            title="Save note"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </section>
    </aside>
  );
}