"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { LogOut, MessagesSquare, User as UserIcon, Wifi, WifiOff } from "lucide-react";
import { AgentInfoPanel } from "@/components/panel/AgentInfoPanel";
import { ConversationList } from "@/components/sidebar/ConversationList";
import { ConversationThread } from "@/components/conversation/ConversationThread";
import { NotificationToggle } from "@/components/NotificationToggle";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useMounted } from "@/hooks/useMounted";
import { useAuthStore } from "@/stores/authStore";
import { useChatStore } from "@/stores/chatStore";

export default function DashboardPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const activeConversationId = useChatStore((s) => s.activeConversationId);
  const wsStatus = useWebSocket(Boolean(token));
  // Auth state comes from localStorage, which does not exist during SSR.
  // Render nothing until mounted so server HTML matches the first client render.
  const mounted = useMounted();

  useEffect(() => {
    if (!token) router.replace("/login");
  }, [token, router]);

  if (!mounted || !token || !user) return null;

  const hasConversation = activeConversationId !== null;

  return (
    <div className="flex h-screen flex-col bg-zinc-100 dark:bg-zinc-950">
      <header className="flex h-16 shrink-0 items-center justify-between border-b border-zinc-200 bg-white/80 px-5 backdrop-blur-xl dark:border-zinc-800 dark:bg-zinc-900/80">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-violet-700 text-white shadow-soft">
            <MessagesSquare className="h-4 w-4" />
          </div>
          <span className="text-sm font-semibold tracking-tight">
            {process.env.NEXT_PUBLIC_APP_NAME ?? "Shared Inbox"}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <span
            className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
              wsStatus === "open"
                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                : "bg-zinc-500/10 text-zinc-400"
            }`}
          >
            <span className={`relative flex h-2 w-2`}>
              <span
                className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 ${
                  wsStatus === "open" ? "bg-emerald-500" : "bg-zinc-400"
                }`}
              />
              <span
                className={`relative inline-flex h-2 w-2 rounded-full ${
                  wsStatus === "open" ? "bg-emerald-500" : "bg-zinc-400"
                }`}
              />
            </span>
            {wsStatus === "open" ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
            {wsStatus === "open" ? "Live" : "Reconnecting…"}
          </span>

          <span className="hidden items-center gap-2 text-sm text-zinc-600 sm:flex dark:text-zinc-300">
            <UserIcon className="h-4 w-4 text-zinc-400" />
            {user.full_name}
            <span className="rounded-full bg-brand-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-brand-700 dark:text-brand-300">
              {user.role}
            </span>
          </span>

          {user.role === "admin" && (
            <>
              <Link
                href="/admin/users"
                className="rounded-full border border-zinc-200 px-3 py-1 text-xs font-medium text-zinc-600 transition hover:border-brand-300 hover:text-brand-600 dark:border-zinc-700 dark:text-zinc-300 dark:hover:border-brand-500 dark:hover:text-brand-300"
              >
                Team
              </Link>
              <Link
                href="/admin/quick-replies"
                className="rounded-full border border-zinc-200 px-3 py-1 text-xs font-medium text-zinc-600 transition hover:border-brand-300 hover:text-brand-600 dark:border-zinc-700 dark:text-zinc-300 dark:hover:border-brand-500 dark:hover:text-brand-300"
              >
                Quick Replies
              </Link>
            </>
          )}

          <NotificationToggle />
          <ThemeToggle />

          <button
            onClick={() => {
              logout();
              router.replace("/login");
            }}
            className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
            title="Log out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <ConversationList />

        <div className="flex min-w-0 flex-1 flex-col">
          {hasConversation ? <ConversationThread /> : <EmptyCenter />}
        </div>

        <div className="hidden w-[320px] shrink-0 border-l border-zinc-200 bg-white lg:block dark:border-zinc-800 dark:bg-zinc-900">
          {hasConversation ? <AgentInfoPanel /> : null}
        </div>
      </div>
    </div>
  );
}

function EmptyCenter() {
  return (
    <div className="flex flex-1 items-center justify-center bg-zinc-50 text-zinc-400 dark:bg-zinc-950 dark:text-zinc-500">
      <div className="text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl bg-gradient-to-br from-brand-500/15 to-violet-500/15 text-brand-500 dark:text-brand-300">
          <MessagesSquare className="h-8 w-8" />
        </div>
        <p className="mt-4 text-sm font-medium text-zinc-600 dark:text-zinc-300">
          Select a conversation to start replying
        </p>
        <p className="mt-1 text-xs">New messages from any connected channel appear here in real time</p>
      </div>
    </div>
  );
}