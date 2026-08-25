export type AuthProvider = "credentials" | "google";

export interface User {
  id: string;
  email: string;
  displayName: string;
  avatarUrl: string | null;
  providers: AuthProvider[];
  createdAt: string;
}

export interface AuthResponse {
  user: User;
}

export interface WorkshopBookingInput {
  name: string;
  organization?: string;
  contact: string;
  attendeeCount: number;
  slotId: string;
  topic: string;
  note?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
}