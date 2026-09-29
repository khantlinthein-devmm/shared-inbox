export type Role = "admin" | "agent";

export type Channel = "viber" | "telegram";

export type ConversationStatus = "unassigned" | "open" | "pending" | "closed";

export type MessageSender = "contact" | "agent";

export type MessageStatus = "received" | "sent" | "delivered" | "seen";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export interface Agent {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export interface Conversation {
  id: number;
  channel: Channel;
  contact_user_id: string;
  contact_name: string;
  contact_avatar: string | null;
  status: ConversationStatus;
  unread_count: number;
  assigned_to_id: number | null;
  assigned_to_email: string | null;
  assigned_to_full_name: string | null;
  last_message: string | null;
  last_message_at: string | null;
  message_count: number;
}

export interface Message {
  id: number;
  conversation_id: number;
  sender: MessageSender;
  sender_id: number | null;
  sender_name: string | null;
  message_type: string;
  text: string | null;
  media_url: string | null;
  status: MessageStatus;
  created_at: string;
}

export interface AgentNote {
  id: number;
  conversation_id: number;
  author_id: number;
  author_name: string | null;
  content: string;
  created_at: string;
}

export interface QuickReply {
  id: number;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ConversationDetail {
  conversation: Conversation;
  messages: Message[];
  notes: AgentNote[];
}

export type WsEvent =
  | {
      type: "message:new";
      payload: { message: Message; conversation: Conversation };
    }
  | {
      type: "conversation:updated";
      payload: Conversation;
    }
  | {
      type: "message:status";
      payload: {
        message_id: number;
        conversation_id: number;
        status: MessageStatus;
      };
    }
  | {
      type: "note:new";
      payload: AgentNote;
    };