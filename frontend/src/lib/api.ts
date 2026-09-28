"use client";

import type {
  Agent,
  AgentNote,
  Conversation,
  ConversationDetail,
  ConversationStatus,
  LoginResponse,
  Message,
  QuickReply,
  User,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const AUTH_KEY = "auth";

interface StoredAuth {
  access_token: string;
  user: User;
}

function readAuth(): StoredAuth | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(AUTH_KEY);
    return raw ? (JSON.parse(raw) as StoredAuth) : null;
  } catch {
    return null;
  }
}

export function getToken(): string | null {
  return readAuth()?.access_token ?? null;
}

export function getStoredUser(): User | null {
  return readAuth()?.user ?? null;
}

export function storeSession(session: LoginResponse): void {
  localStorage.setItem(AUTH_KEY, JSON.stringify({ access_token: session.access_token, user: session.user }));
}

export function clearSession(): void {
  localStorage.removeItem(AUTH_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* ignore body parse errors */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function login(email: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function listConversations(status?: ConversationStatus): Promise<Conversation[]> {
  const query = status ? `?status=${status}` : "";
  return request<Conversation[]>(`/api/v1/conversations${query}`);
}

export function getConversationDetail(id: number): Promise<ConversationDetail> {
  return request<ConversationDetail>(`/api/v1/conversations/${id}`);
}

export function sendMessage(conversationId: number, text: string): Promise<Message> {
  return request<Message>(`/api/v1/conversations/${conversationId}/messages`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export function uploadAttachment(conversationId: number, file: File): Promise<Message> {
  const form = new FormData();
  form.append("file", file);
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(`${API_URL}/api/v1/conversations/${conversationId}/attachments`, {
    method: "POST",
    body: form,
    headers,
  }).then((res) => {
    if (!res.ok) {
      throw new Error(`${res.status} ${res.statusText}`);
    }
    return res.json() as Promise<Message>;
  });
}

export function updateConversation(id: number, patch: Record<string, unknown>): Promise<Conversation> {
  return request<Conversation>(`/api/v1/conversations/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export function listNotes(conversationId: number): Promise<AgentNote[]> {
  return request<AgentNote[]>(`/api/v1/conversations/${conversationId}/notes`);
}

export function createNote(conversationId: number, content: string): Promise<AgentNote> {
  return request<AgentNote>(`/api/v1/conversations/${conversationId}/notes`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function listAgents(): Promise<Agent[]> {
  return request<Agent[]>(`/api/v1/users/agents`);
}

export function listAllUsers(): Promise<User[]> {
  return request<User[]>(`/api/v1/users`);
}

export function createUser(payload: {
  email: string;
  full_name: string;
  password: string;
  role: string;
}): Promise<User> {
  return request<User>(`/api/v1/users`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateUser(id: number, patch: Record<string, unknown>): Promise<User> {
  return request<User>(`/api/v1/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export function listQuickReplies(): Promise<QuickReply[]> {
  return request<QuickReply[]>(`/api/v1/quick-replies`);
}

export function createQuickReply(payload: { title: string; content: string }): Promise<QuickReply> {
  return request<QuickReply>(`/api/v1/quick-replies`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateQuickReply(
  id: number,
  patch: { title?: string; content?: string }
): Promise<QuickReply> {
  return request<QuickReply>(`/api/v1/quick-replies/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export function deleteQuickReply(id: number): Promise<void> {
  return request<void>(`/api/v1/quick-replies/${id}`, { method: "DELETE" });
}