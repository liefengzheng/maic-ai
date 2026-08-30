from datetime import datetime
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
    tenant_id: UUID = Field(alias="tenantId")
    tenant_name: str = Field(alias="tenantName")
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


class ConversationOutput(ApiModel):
    id: UUID
    title: str
    target_kind: str | None = Field(alias="targetKind")
    target_id: UUID | None = Field(alias="targetId")
    target_name: str | None = Field(alias="targetName")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class AgentChoiceOutput(ApiModel):
    id: UUID
    kind: str
    name: str
    description: str | None
    system_prompt: str = Field(alias="systemPrompt")


class AgentCreateInput(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=160, pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str | None = Field(default=None, max_length=2000)
    system_prompt: str = Field(alias="systemPrompt", min_length=1, max_length=50000)
    visibility: str = Field(default="private", pattern="^(private|tenant)$")
    tool_ids: list[UUID] = Field(default_factory=list, alias="toolIds")
    mcp_server_ids: list[UUID] = Field(default_factory=list, alias="mcpServerIds")


class AgentOutput(AgentChoiceOutput):
    slug: str
    visibility: str
    graph_status: str = Field(alias="graphStatus")


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