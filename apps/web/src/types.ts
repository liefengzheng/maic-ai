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
  modelId: string;
  modelName: string;
  createdAt: string;
  updatedAt: string;
}

export interface LlmModel {
  id: string;
  name: string;
  provider: string;
  model: string;
}

export type AgentKind = "agent" | "super_agent";

export interface AgentChoice {
  id: string;
  kind: AgentKind;
  name: string;
  description: string | null;
  systemPrompt: string;
}

export interface SkillDefinition {
  id: number;
  skillCode: string;
  skillName: string;
  description: string;
  skillType: "local";
  handler: string;
  inputSchema: Record<string, unknown>;
  outputSchema: Record<string, unknown>;
  executionConfig: Record<string, unknown>;
  enabled: boolean;
  version: string;
}

export interface ManagedAgent extends AgentChoice {
  kind: "agent";
  slug: string;
  enabled: boolean;
  skillIds: number[];
  graphStatus: string;
}

export interface SuperAgent extends AgentChoice {
  kind: "super_agent";
  slug: string;
  enabled: boolean;
  agentIds: string[];
}

export interface AgentCatalog {
  skills: SkillDefinition[];
  skillHandlers: string[];
  agents: ManagedAgent[];
  superAgents: SuperAgent[];
}
