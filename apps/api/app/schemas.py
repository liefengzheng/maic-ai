from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class RegisterInput(ApiModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(alias="displayName", min_length=2, max_length=80)


class LoginInput(ApiModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserOutput(ApiModel):
    id: UUID
    role: str
    email: EmailStr
    display_name: str = Field(alias="displayName")
    avatar_url: str | None = Field(alias="avatarUrl")
    providers: list[str]
    created_at: datetime = Field(alias="createdAt")


class AuthOutput(ApiModel):
    user: UserOutput


class WorkshopBookingInput(ApiModel):
    slot_id: UUID = Field(alias="slotId")
    name: str = Field(min_length=2, max_length=80)
    organization: str | None = Field(default=None, max_length=120)
    contact: str = Field(min_length=3, max_length=120)
    attendee_count: int = Field(alias="attendeeCount", ge=1, le=50)
    topic: str = Field(min_length=2, max_length=160)
    note: str | None = Field(default=None, max_length=2000)


class ConversationInput(ApiModel):
    title: str = Field(default="新对话", min_length=1, max_length=160)
    target_kind: str | None = Field(default=None, alias="targetKind", pattern="^(agent|super_agent)$")
    target_id: UUID | None = Field(default=None, alias="targetId")
    model_id: UUID | None = Field(default=None, alias="modelId")


class ConversationOutput(ApiModel):
    id: UUID
    title: str
    target_kind: str | None = Field(alias="targetKind")
    target_id: UUID | None = Field(alias="targetId")
    target_name: str | None = Field(alias="targetName")
    model_id: UUID = Field(alias="modelId")
    model_name: str = Field(alias="modelName")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class AgentChoiceOutput(ApiModel):
    id: UUID
    kind: str
    name: str
    description: str | None
    system_prompt: str = Field(alias="systemPrompt")


class LlmModelOutput(ApiModel):
    id: UUID
    name: str
    provider: str
    model: str


class SkillInput(ApiModel):
    skill_code: str = Field(alias="skillCode", min_length=1, max_length=100, pattern="^[a-z][a-z0-9_]*$")
    skill_name: str = Field(alias="skillName", min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    skill_type: Literal["local"] = Field(default="local", alias="skillType")
    handler: str = Field(min_length=1, max_length=100, pattern="^[a-z][a-z0-9_]*$")
    input_schema: dict[str, Any] = Field(alias="inputSchema")
    output_schema: dict[str, Any] = Field(default_factory=dict, alias="outputSchema")
    execution_config: dict[str, Any] = Field(default_factory=dict, alias="executionConfig")
    enabled: bool = True
    version: str = Field(min_length=1, max_length=20)


class SkillOutput(SkillInput):
    id: int


class AgentInput(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=160, pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str | None = Field(default=None, max_length=2000)
    system_prompt: str = Field(alias="systemPrompt", min_length=1, max_length=50000)
    enabled: bool = True
    skill_ids: list[int] = Field(default_factory=list, alias="skillIds")


class AgentOutput(AgentChoiceOutput):
    slug: str
    enabled: bool
    skill_ids: list[int] = Field(default_factory=list, alias="skillIds")
    graph_status: str = Field(alias="graphStatus")


class SuperAgentInput(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=160, pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str | None = Field(default=None, max_length=2000)
    system_prompt: str = Field(alias="systemPrompt", min_length=1, max_length=50000)
    enabled: bool = True
    agent_ids: list[UUID] = Field(default_factory=list, alias="agentIds")


class SuperAgentOutput(AgentChoiceOutput):
    slug: str
    enabled: bool
    agent_ids: list[UUID] = Field(default_factory=list, alias="agentIds")


class AgentCatalogOutput(ApiModel):
    skills: list[SkillOutput]
    skill_handlers: list[str] = Field(alias="skillHandlers")
    agents: list[AgentOutput]
    super_agents: list[SuperAgentOutput] = Field(alias="superAgents")


class AgentGraphOutput(ApiModel):
    agent_id: UUID = Field(alias="agentId")
    status: str


class ChatMessageOutput(ApiModel):
    id: UUID
    role: str
    content: str
    created_at: datetime = Field(alias="createdAt")


class ChatRunInput(ApiModel):
    content: str = Field(min_length=1, max_length=50000)


class ApprovalDecisionInput(ApiModel):
    type: Literal["approve", "reject"]
    message: str | None = Field(default=None, max_length=2000)


class ApprovalInput(ApiModel):
    interrupt_id: str = Field(alias="interruptId", min_length=1, max_length=255)
    decisions: list[ApprovalDecisionInput] = Field(min_length=1)