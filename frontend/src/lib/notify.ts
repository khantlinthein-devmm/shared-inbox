"use client";

import { useChatStore } from "@/stores/chatStore";
import { channelLabel } from "./format";
import type { WsEvent } from "./types";

const PREF_KEY = "notifications";

export function notificationsEnabled(): boolean {
  try {
    return localStorage.getItem(PREF_KEY) !== "off";
  } catch {
    return true;
  }
}

export function setNotificationsEnabled(on: boolean): void {
  try {
    localStorage.setItem(PREF_KEY, on ? "on" : "off");
  } catch {
    /* storage unavailable; preference just won't persist */
  }
}

let audioCtx: AudioContext | null = null;

// Browsers keep an AudioContext suspended until a user gesture, so this is
// called from click/keydown handlers before the first chime can play.
export function unlockAudio(): void {
  try {
    audioCtx ??= new AudioContext();
    if (audioCtx.state === "suspended") void audioCtx.resume();
  } catch {
    /* Web Audio unsupported */
  }
}

function playChime(): void {
  if (!audioCtx || audioCtx.state !== "running") return;
  const ctx = audioCtx;
  const now = ctx.currentTime;
  [880, 1320].forEach((freq, i) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    const start = now + i * 0.12;
    osc.type = "sine";
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.exponentialRampToValueAtTime(0.2, start + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.25);
    osc.connect(gain).connect(ctx.destination);
    osc.start(start);
    osc.stop(start + 0.3);
  });
}

let unread = 0;
let baseTitle = "";

function bumpTitle(): void {
  if (!baseTitle) baseTitle = document.title.replace(/^\(\d+\)\s*/, "");
  unread += 1;
  document.title = `(${unread}) ${baseTitle}`;
}

function resetTitle(): void {
  if (unread === 0) return;
  unread = 0;
  document.title = baseTitle;
}

function showDesktopNotification(title: string, body: string, conversationId: number): void {
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  try {
    const n = new Notification(title, { body, tag: `conversation-${conversationId}` });
    n.onclick = () => {
      window.focus();
      useChatStore.getState().setActiveConversation(conversationId);
      n.close();
    };
  } catch {
    /* some mobile browsers only allow notifications via a service worker */
  }
}

export function notifyForEvent(event: WsEvent): void {
  if (event.type !== "message:new") return;
  const { message, conversation } = event.payload;
  if (message.sender !== "contact") return;

  const pageVisible = document.visibilityState === "visible";
  const pageFocused = pageVisible && document.hasFocus();
  const viewingThisConversation =
    pageFocused && useChatStore.getState().activeConversationId === conversation.id;

  if (!pageVisible) bumpTitle();
  if (!notificationsEnabled() || viewingThisConversation) return;

  playChime();
  if (!pageFocused) {
    const body = message.text?.trim() || `[${message.message_type}]`;
    showDesktopNotification(
      `${conversation.contact_name} · ${channelLabel(conversation.channel)}`,
      body,
      conversation.id
    );
  }
}

/** Wires the page-level listeners alerts depend on. Returns a cleanup function. */
export function installAlertListeners(): () => void {
  const onVisibility = () => {
    if (document.visibilityState === "visible") resetTitle();
  };
  const onGesture = () => unlockAudio();
  document.addEventListener("visibilitychange", onVisibility);
  window.addEventListener("focus", onVisibility);
  document.addEventListener("pointerdown", onGesture);
  document.addEventListener("keydown", onGesture);
  return () => {
    document.removeEventListener("visibilitychange", onVisibility);
    window.removeEventListener("focus", onVisibility);
    document.removeEventListener("pointerdown", onGesture);
    document.removeEventListener("keydown", onGesture);
    resetTitle();
  };
}
