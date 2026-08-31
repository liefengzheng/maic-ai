export type AuthProvider = "credentials" | "google";

export interface User {
  id: string;
  role: "admin" | "user";
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

export interface Conversation {
  id: string;
  title: string;
  targetKind: AgentKind | null;
  targetId: string | null;
  targetName: string | null;
  createdAt: string;
  updatedAt: string;
}

export type AgentKind = "agent" | "super_agent";

export interface AgentChoice {
  id: string;
  kind: AgentKind;
  name: string;
  description: string | null;
  systemPrompt: string;
}

export interface ToolDefinition {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  handler: string;
  enabled: boolean;
}

export interface McpServerDefinition {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  transport: "http" | "sse";
  url: string;
  enabled: boolean;
}

export interface ManagedAgent extends AgentChoice {
  kind: "agent";
  slug: string;
  enabled: boolean;
  toolIds: string[];
  mcpServerIds: string[];
  graphStatus: string;
}

export interface SuperAgent extends AgentChoice {
  kind: "super_agent";
  slug: string;
  enabled: boolean;
  agentIds: string[];
}

export interface AgentCatalog {
  tools: ToolDefinition[];
  mcpServers: McpServerDefinition[];
  agents: ManagedAgent[];
  superAgents: SuperAgent[];
}
