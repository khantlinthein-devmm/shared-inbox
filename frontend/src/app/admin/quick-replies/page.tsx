"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createQuickReply, deleteQuickReply, listQuickReplies, updateQuickReply } from "@/lib/api";
import type { QuickReply } from "@/lib/types";
import { useAuthStore } from "@/stores/authStore";
import { useMounted } from "@/hooks/useMounted";
import { ThemeToggle } from "@/components/ThemeToggle";

const inputClass =
  "w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm outline-none transition placeholder:text-zinc-400 focus:border-brand-400 focus:ring-4 focus:ring-brand-500/15 dark:border-zinc-700 dark:bg-zinc-800";

export default function AdminQuickRepliesPage() {
  const router = useRouter();
  const mounted = useMounted();
  const token = useAuthStore((s) => s.token);
  const me = useAuthStore((s) => s.user);
  const [replies, setReplies] = useState<QuickReply[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");

  useEffect(() => {
    if (mounted && !token) router.replace("/login");
  }, [mounted, token, router]);

  useEffect(() => {
    if (!token) return;
    listQuickReplies().then(setReplies).catch((e) => setError(String(e)));
  }, [token]);

  if (!mounted || !token || !me) return null;
  if (me.role !== "admin") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-zinc-100 dark:bg-zinc-950">
        <div className="rounded-2xl border border-zinc-200 bg-white p-8 text-sm shadow-soft dark:border-zinc-800 dark:bg-zinc-900">
          <p className="font-semibold">Admins only</p>
          <Link href="/dashboard" className="mt-2 block text-brand-600 underline dark:text-brand-300">
            Back to dashboard
          </Link>
        </div>
      </main>
    );
  }

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const created = await createQuickReply({ title, content });
      setReplies((list) => [...list, created].sort((a, b) => a.title.localeCompare(b.title)));
      setTitle("");
      setContent("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  function startEdit(reply: QuickReply) {
    setEditingId(reply.id);
    setEditTitle(reply.title);
    setEditContent(reply.content);
  }

  async function saveEdit(id: number) {
    setError("");
    try {
      const updated = await updateQuickReply(id, { title: editTitle, content: editContent });
      setReplies((list) => list.map((r) => (r.id === id ? updated : r)));
      setEditingId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  }

  async function remove(reply: QuickReply) {
    if (!window.confirm(`Delete quick reply "${reply.title}"?`)) return;
    setError("");
    try {
      await deleteQuickReply(reply.id);
      setReplies((list) => list.filter((r) => r.id !== reply.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  return (
    <main className="min-h-screen bg-zinc-100 px-4 py-8 dark:bg-zinc-950">
      <div className="mx-auto w-full max-w-2xl">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <h1 className="text-lg font-semibold tracking-tight">Quick replies</h1>
          </div>
          <Link href="/dashboard" className="text-sm text-brand-600 underline dark:text-brand-300">
            Back to dashboard
          </Link>
        </div>

        <form
          onSubmit={onCreate}
          className="space-y-3 rounded-2xl border border-zinc-200 bg-white p-6 shadow-soft dark:border-zinc-800 dark:bg-zinc-900"
        >
          <h2 className="text-sm font-semibold">Add a quick reply</h2>
          <input
            required
            maxLength={80}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Label shown to agents (e.g. Greeting)"
            className={inputClass}
          />
          <textarea
            required
            maxLength={4000}
            rows={3}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Message text inserted into the reply box"
            className={`${inputClass} resize-y`}
          />
          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
          <button
            type="submit"
            disabled={busy}
            className="rounded-xl bg-gradient-to-r from-brand-600 to-violet-600 px-4 py-2 text-sm font-medium text-white shadow-soft transition hover:brightness-110 disabled:opacity-50"
          >
            {busy ? "Saving…" : "Add quick reply"}
          </button>
        </form>

        <div className="mt-4 space-y-2">
          {replies.length === 0 && (
            <p className="px-1 text-sm text-zinc-500 dark:text-zinc-400">No quick replies yet.</p>
          )}
          {replies.map((reply) => (
            <div
              key={reply.id}
              className="rounded-2xl border border-zinc-200 bg-white px-4 py-3 text-sm shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
            >
              {editingId === reply.id ? (
                <div className="space-y-2">
                  <input
                    maxLength={80}
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className={inputClass}
                  />
                  <textarea
                    maxLength={4000}
                    rows={3}
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className={`${inputClass} resize-y`}
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => saveEdit(reply.id)}
                      disabled={!editTitle.trim() || !editContent.trim()}
                      className="rounded-xl bg-brand-600 px-3 py-1.5 text-xs font-medium text-white transition hover:brightness-110 disabled:opacity-50"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="rounded-xl bg-zinc-100 px-3 py-1.5 text-xs font-medium transition hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-medium">{reply.title}</p>
                    <p className="mt-0.5 whitespace-pre-wrap break-words text-xs text-zinc-500 dark:text-zinc-400">
                      {reply.content}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <button
                      onClick={() => startEdit(reply)}
                      className="rounded-xl bg-zinc-100 px-3 py-1.5 text-xs font-medium transition hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => remove(reply)}
                      className="rounded-xl bg-red-50 px-3 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-100 dark:bg-red-500/10 dark:text-red-400 dark:hover:bg-red-500/20"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
