"use client";

import { create } from "zustand";
import type {
  Agent,
  AgentNote,
  Conversation,
  ConversationStatus,
  Message,
  MessageStatus,
  WsEvent,
} from "@/lib/types";

interface ChatState {
  conversations: Conversation[];
  agents: Agent[];
  activeConversationId: number | null;
  messages: Record<number, Message[]>;
  notes: Record<number, AgentNote[]>;
  statusFilter: ConversationStatus | "";
  searchQuery: string;

  setConversations: (conversations: Conversation[]) => void;
  setAgents: (agents: Agent[]) => void;
  setActiveConversation: (id: number | null) => void;
  setMessages: (conversationId: number, messages: Message[]) => void;
  setNotes: (conversationId: number, notes: AgentNote[]) => void;
  addNote: (note: AgentNote) => void;
  upsertConversation: (conversation: Conversation) => void;
  upsertMessage: (conversationId: number, message: Message) => void;
  updateMessageStatus: (
    conversationId: number,
    messageId: number,
    status: MessageStatus
  ) => void;
  setStatusFilter: (filter: ConversationStatus | "") => void;
  setSearchQuery: (query: string) => void;
  applyEvent: (event: WsEvent) => void;
}

export const useChatStore = create<ChatState>()((set) => ({
  conversations: [],
  agents: [],
  activeConversationId: null,
  messages: {},
  notes: {},
  statusFilter: "",
  searchQuery: "",

  setConversations: (conversations) => set({ conversations }),
  setAgents: (agents) => set({ agents }),
  setActiveConversation: (activeConversationId) => set({ activeConversationId }),
  setMessages: (conversationId, messages) =>
    set((s) => ({ messages: { ...s.messages, [conversationId]: messages } })),
  setNotes: (conversationId, notes) =>
    set((s) => ({ notes: { ...s.notes, [conversationId]: notes } })),

  addNote: (note) =>
    set((s) => {
      const existing = s.notes[note.conversation_id] ?? [];
      return {
        notes: {
          ...s.notes,
          [note.conversation_id]: [...existing.filter((n) => n.id !== note.id), note],
        },
      };
    }),

  upsertConversation: (conversation) =>
    set((s) => {
      const exists = s.conversations.some((c) => c.id === conversation.id);
      return {
        conversations: exists
          ? s.conversations.map((c) => (c.id === conversation.id ? conversation : c))
          : [conversation, ...s.conversations],
      };
    }),

  upsertMessage: (conversationId, message) =>
    set((s) => {
      const existing = s.messages[conversationId] ?? [];
      const exists = existing.some((m) => m.id === message.id);
      const messages = exists
        ? existing.map((m) => (m.id === message.id ? message : m))
        : [...existing, message];
      return { messages: { ...s.messages, [conversationId]: messages } };
    }),

  updateMessageStatus: (conversationId, messageId, status) =>
    set((s) => {
      const existing = s.messages[conversationId] ?? [];
      return {
        messages: {
          ...s.messages,
          [conversationId]: existing.map((m) => (m.id === messageId ? { ...m, status } : m)),
        },
      };
    }),

  setStatusFilter: (statusFilter) => set({ statusFilter }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),

  applyEvent: (event) => {
    if (event.type === "message:new") {
      useChatStore.setState((s) => {
        const { message, conversation } = event.payload;
        const conversationExists = s.conversations.some((c) => c.id === conversation.id);
        const conversations = conversationExists
          ? s.conversations.map((c) => (c.id === conversation.id ? conversation : c))
          : [conversation, ...s.conversations];

        const existing = s.messages[message.conversation_id] ?? [];
        const messages = existing.some((m) => m.id === message.id)
          ? existing
          : [...existing, message];

        return {
          conversations,
          messages: { ...s.messages, [message.conversation_id]: messages },
        };
      });
    } else if (event.type === "conversation:updated") {
      useChatStore.setState((s) => {
        const exists = s.conversations.some((c) => c.id === event.payload.id);
        return {
          conversations: exists
            ? s.conversations.map((c) => (c.id === event.payload.id ? event.payload : c))
            : [event.payload, ...s.conversations],
        };
      });
    } else if (event.type === "message:status") {
      useChatStore.setState((s) => {
        const existing = s.messages[event.payload.conversation_id] ?? [];
        return {
          messages: {
            ...s.messages,
            [event.payload.conversation_id]: existing.map((m) =>
              m.id === event.payload.message_id ? { ...m, status: event.payload.status } : m
            ),
          },
        };
      });
    } else if (event.type === "note:new") {
      const note = event.payload;
      useChatStore.setState((s) => {
        const existing = s.notes[note.conversation_id] ?? [];
        return {
          notes: {
            ...s.notes,
            [note.conversation_id]: [...existing.filter((n) => n.id !== note.id), note],
          },
        };
      });
    }
  },
}));