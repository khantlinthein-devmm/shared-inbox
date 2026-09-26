"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { LogIn, MessagesSquare } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function LoginPage() {
  const router = useRouter();
  const login = useAuthStore((s) => s.login);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch {
      setError("Invalid email or password");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-zinc-100 px-4 dark:bg-zinc-950">
      {/* Ambient gradient blobs */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-brand-500/25 blur-3xl dark:bg-brand-600/20" />
        <div className="absolute -bottom-32 -right-32 h-96 w-96 rounded-full bg-violet-500/20 blur-3xl dark:bg-violet-600/15" />
      </div>

      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>

      <div className="relative w-full max-w-sm animate-fade-up rounded-3xl border border-white/40 bg-white/80 p-8 shadow-soft backdrop-blur-xl dark:border-zinc-800 dark:bg-zinc-900/80">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-violet-700 text-white shadow-soft">
            <MessagesSquare className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight">
              {process.env.NEXT_PUBLIC_APP_NAME ?? "Shared Inbox"}
            </h1>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Multi-agent support dashboard
            </p>
          </div>
        </div>

        <form onSubmit={onSubmit} className="mt-8 space-y-4">
          <div>
            <label htmlFor="email" className="mb-1.5 block text-xs font-medium text-zinc-600 dark:text-zinc-300">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3.5 py-2.5 text-sm outline-none transition placeholder:text-zinc-400 focus:border-brand-400 focus:ring-4 focus:ring-brand-500/15 dark:border-zinc-700 dark:bg-zinc-800 dark:placeholder:text-zinc-500"
              placeholder="admin@example.com"
            />
          </div>
          <div>
            <label htmlFor="password" className="mb-1.5 block text-xs font-medium text-zinc-600 dark:text-zinc-300">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3.5 py-2.5 text-sm outline-none transition placeholder:text-zinc-400 focus:border-brand-400 focus:ring-4 focus:ring-brand-500/15 dark:border-zinc-700 dark:bg-zinc-800 dark:placeholder:text-zinc-500"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-500/10 dark:text-red-400">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-brand-600 to-violet-600 py-2.5 text-sm font-medium text-white shadow-soft transition hover:brightness-110 active:brightness-95 disabled:opacity-50"
          >
            <LogIn className="h-4 w-4" />
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </main>
  );
}