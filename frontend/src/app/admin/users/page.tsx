"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createUser, listAllUsers, updateUser } from "@/lib/api";
import type { User } from "@/lib/types";
import { useAuthStore } from "@/stores/authStore";
import { useMounted } from "@/hooks/useMounted";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function AdminUsersPage() {
  const router = useRouter();
  const mounted = useMounted();
  const token = useAuthStore((s) => s.token);
  const me = useAuthStore((s) => s.user);
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("agent");

  useEffect(() => {
    if (mounted && !token) router.replace("/login");
  }, [mounted, token, router]);

  useEffect(() => {
    if (!token) return;
    listAllUsers().then(setUsers).catch((e) => setError(String(e)));
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
      const created = await createUser({ email, full_name: fullName, password, role });
      setUsers((u) => [...u, created]);
      setEmail("");
      setFullName("");
      setPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive(u: User) {
    setError("");
    try {
      const updated = await updateUser(u.id, { is_active: !u.is_active });
      setUsers((list) => list.map((x) => (x.id === u.id ? updated : x)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  }

  return (
    <main className="min-h-screen bg-zinc-100 px-4 py-8 dark:bg-zinc-950">
      <div className="mx-auto w-full max-w-2xl">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <h1 className="text-lg font-semibold tracking-tight">Team members</h1>
          </div>
          <Link href="/dashboard" className="text-sm text-brand-600 underline dark:text-brand-300">
            Back to dashboard
          </Link>
        </div>

        <form onSubmit={onCreate} className="space-y-3 rounded-2xl border border-zinc-200 bg-white p-6 shadow-soft dark:border-zinc-800 dark:bg-zinc-900">
          <h2 className="text-sm font-semibold">Create agent / admin</h2>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="agent@company.com"
            className="w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm outline-none transition placeholder:text-zinc-400 focus:border-brand-400 focus:ring-4 focus:ring-brand-500/15 dark:border-zinc-700 dark:bg-zinc-800"
          />
          <input
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Full name"
            required
            className="w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm outline-none transition placeholder:text-zinc-400 focus:border-brand-400 focus:ring-4 focus:ring-brand-500/15 dark:border-zinc-700 dark:bg-zinc-800"
          />
          <div className="flex gap-3">
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password (min 6)"
              autoComplete="new-password"
              className="flex-1 rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm outline-none transition placeholder:text-zinc-400 focus:border-brand-400 focus:ring-4 focus:ring-brand-500/15 dark:border-zinc-700 dark:bg-zinc-800"
            />
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm outline-none dark:border-zinc-700 dark:bg-zinc-800"
            >
              <option value="agent">agent</option>
              <option value="admin">admin</option>
            </select>
          </div>
          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
          <button
            type="submit"
            disabled={busy}
            className="rounded-xl bg-gradient-to-r from-brand-600 to-violet-600 px-4 py-2 text-sm font-medium text-white shadow-soft transition hover:brightness-110 disabled:opacity-50"
          >
            {busy ? "Creating…" : "Create user"}
          </button>
        </form>

        <div className="mt-4 space-y-2">
          {users.map((u) => (
            <div
              key={u.id}
              className="flex items-center justify-between rounded-2xl border border-zinc-200 bg-white px-4 py-3 text-sm shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
            >
              <div>
                <p className="font-medium">
                  {u.full_name}{" "}
                  {!u.is_active && (
                    <span className="ml-1 rounded-full bg-red-100 px-1.5 py-0.5 text-[10px] font-medium uppercase text-red-600 dark:bg-red-500/15 dark:text-red-400">
                      disabled
                    </span>
                  )}
                </p>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  {u.email} · {u.role}
                </p>
              </div>
              {u.id !== me.id && (
                <button
                  onClick={() => toggleActive(u)}
                  className="rounded-xl bg-zinc-100 px-3 py-1.5 text-xs font-medium transition hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700"
                >
                  {u.is_active ? "Disable" : "Enable"}
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
