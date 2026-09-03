import {
  Bot,
  Check,
  Plus,
  Sparkles,
  Trash2,
  Users,
} from "lucide-react";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { apiUrl } from "./api";
import type {
  AgentCatalog,
  ManagedAgent,
  SkillDefinition,
  SuperAgent,
} from "./types";

type CatalogSection = "skills" | "agents" | "superAgents";
type CatalogResource =
  | SkillDefinition
  | ManagedAgent
  | SuperAgent;

interface CatalogDraft {
  name: string;
  slug: string;
  description: string;
  handler: string;
  version: string;
  inputSchema: string;
  outputSchema: string;
  executionConfig: string;
  systemPrompt: string;
  enabled: boolean;
  skillIds: number[];
  agentIds: string[];
}

type JsonDraftField = "inputSchema" | "outputSchema" | "executionConfig";

const emptyDraft = (): CatalogDraft => ({
  name: "",
  slug: "",
  description: "",
  handler: "",
  version: "1.0",
  inputSchema:
    '{\n  "type": "object",\n  "properties": {},\n  "required": [],\n  "additionalProperties": false\n}',
  outputSchema: "{}",
  executionConfig: "{}",
  systemPrompt: "",
  enabled: true,
  skillIds: [],
  agentIds: [],
});

export function CatalogManager() {
  const [catalog, setCatalog] = useState<AgentCatalog | null>(null);
  const [section, setSection] = useState<CatalogSection>("agents");
  const [selectedId, setSelectedId] = useState<string | number | null>(null);
  const [draft, setDraft] = useState<CatalogDraft>(emptyDraft);
  const [status, setStatus] = useState("");
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const loadCatalog = async () => {
    const response = await fetch(apiUrl("/agents/catalog"), {
      credentials: "include",
    });
    const payload = (await response.json()) as AgentCatalog & {
      message?: string;
    };
    if (!response.ok) throw new Error(payload.message ?? "目录加载失败");
    setCatalog(payload);
  };

  /* oxlint-disable react/set-state-in-effect -- Fetch catalog state on mount. */
  useEffect(() => {
    void loadCatalog().catch((error: unknown) =>
      setStatus(error instanceof Error ? error.message : "目录加载失败"),
    );
  }, []);
  /* oxlint-enable react/set-state-in-effect */

  const chooseSection = (next: CatalogSection) => {
    setSection(next);
    setSelectedId(null);
    setDraft(emptyDraft());
    setStatus("");
    setFormError("");
  };

  const editResource = (resource: CatalogResource) => {
    setSelectedId(resource.id);
    setDraft({
      ...emptyDraft(),
      ...resource,
      name: "skillName" in resource ? resource.skillName : resource.name,
      slug: "skillCode" in resource ? resource.skillCode : resource.slug,
      description: resource.description ?? "",
      handler: "handler" in resource ? resource.handler : "",
      version: "version" in resource ? resource.version : "1.0",
      inputSchema:
        "inputSchema" in resource
          ? JSON.stringify(resource.inputSchema, null, 2)
          : emptyDraft().inputSchema,
      outputSchema:
        "outputSchema" in resource
          ? JSON.stringify(resource.outputSchema, null, 2)
          : "{}",
      executionConfig:
        "executionConfig" in resource
          ? JSON.stringify(resource.executionConfig, null, 2)
          : "{}",
      systemPrompt: "systemPrompt" in resource ? resource.systemPrompt : "",
      skillIds: "skillIds" in resource ? resource.skillIds : [],
      agentIds: "agentIds" in resource ? resource.agentIds : [],
    });
  };

  const save = async (event: FormEvent) => {
    event.preventDefault();
    if (saving) return;
    setSaving(true);
    setStatus("正在保存");
    setFormError("");
    try {
      const endpoints: Record<CatalogSection, string> = {
        skills: "/agents/skills",
        agents: "/agents",
        superAgents: "/agents/super",
      };
      const base = {
        name: draft.name,
        slug: draft.slug,
        description: draft.description || null,
        enabled: draft.enabled,
      };
      let body: object;
      if (section === "skills") {
        try {
          body = {
            skillCode: draft.slug,
            skillName: draft.name,
            description: draft.description,
            skillType: "local",
            handler: draft.handler,
            inputSchema: JSON.parse(draft.inputSchema) as unknown,
            outputSchema: JSON.parse(draft.outputSchema) as unknown,
            executionConfig: JSON.parse(draft.executionConfig) as unknown,
            enabled: draft.enabled,
            version: draft.version,
          };
        } catch {
          throw new Error("Schema 或 Execution Config 不是有效的 JSON");
        }
      } else if (section === "agents") {
        body = {
          ...base,
          systemPrompt: draft.systemPrompt,
          skillIds: draft.skillIds,
        };
      } else {
        body = {
          ...base,
          systemPrompt: draft.systemPrompt,
          agentIds: draft.agentIds,
        };
      }
      const suffix = selectedId ? `/${selectedId}` : "";
      const response = await fetch(apiUrl(`${endpoints[section]}${suffix}`), {
        method: selectedId ? "PUT" : "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      const payload = (await response.json()) as {
        id?: string | number;
        message?: string;
      };
      if (!response.ok || !payload.id)
        throw new Error(payload.message ?? "保存失败");
      await loadCatalog();
      setSelectedId(payload.id);
      setStatus("已保存");
    } catch (error) {
      const message = error instanceof Error ? error.message : "操作失败";
      setStatus(message);
      setFormError(message);
    } finally {
      setSaving(false);
    }
  };

  const deleteSkill = async () => {
    if (section !== "skills" || typeof selectedId !== "number" || saving)
      return;
    if (!window.confirm("确定删除这个 Skill？")) return;

    setSaving(true);
    setStatus("正在删除");
    try {
      const response = await fetch(apiUrl(`/agents/skills/${selectedId}`), {
        method: "DELETE",
        credentials: "include",
      });
      if (!response.ok) {
        const payload = (await response.json()) as { message?: string };
        throw new Error(payload.message ?? "删除失败");
      }
      await loadCatalog();
      setSelectedId(null);
      setDraft(emptyDraft());
      setStatus("已删除");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "删除失败");
    } finally {
      setSaving(false);
    }
  };

  const resources: CatalogResource[] = catalog?.[section] ?? [];
  const selectedSkillIsAssigned =
    section === "skills" &&
    typeof selectedId === "number" &&
    (catalog?.agents.some((agent) => agent.skillIds.includes(selectedId)) ??
      false);
  const toggleAgentId = (id: string) => {
    setDraft((current) => ({
      ...current,
      agentIds: current.agentIds.includes(id)
        ? current.agentIds.filter((value) => value !== id)
        : [...current.agentIds, id],
    }));
  };

  const toggleSkillId = (id: number) => {
    setDraft((current) => ({
      ...current,
      skillIds: current.skillIds.includes(id)
        ? current.skillIds.filter((value) => value !== id)
        : [...current.skillIds, id],
    }));
  };

  const formatJsonField = (field: JsonDraftField) => {
    try {
      const formatted = JSON.stringify(JSON.parse(draft[field]), null, 2);
      setDraft((current) => ({ ...current, [field]: formatted }));
      setFormError("");
    } catch {
      setFormError("JSON 格式无效，请检查括号、引号和逗号");
    }
  };

  const agentOptions = (items: ManagedAgent[]) =>
    items.length ? (
      <div className="catalog-options">
        {items.map((item) => (
          <label key={item.id}>
            <input
              type="checkbox"
              checked={draft.agentIds.includes(item.id)}
              onChange={() => toggleAgentId(item.id)}
            />
            <span>
              <strong>{item.name}</strong>
              <small>{item.description || item.slug}</small>
            </span>
          </label>
        ))}
      </div>
    ) : (
      <p className="catalog-empty">暂无 Agent</p>
    );

  const basicFields = (
    <>
      <label>
        名称
        <input
          required
          maxLength={120}
          value={draft.name}
          onChange={(event) => setDraft({ ...draft, name: event.target.value })}
        />
      </label>
      <label>
        {section === "skills" ? "Skill Code" : "Slug"}
        <input
          required
          pattern={
            section === "skills"
              ? "[a-z][a-z0-9_]*"
              : "[a-z0-9]+(?:-[a-z0-9]+)*"
          }
          value={draft.slug}
          onChange={(event) =>
            setDraft({ ...draft, slug: event.target.value.toLowerCase() })
          }
        />
      </label>
      <label>
        描述
        <textarea
          className="compact-textarea"
          maxLength={2000}
          value={draft.description}
          onChange={(event) =>
            setDraft({ ...draft, description: event.target.value })
          }
        />
      </label>
      <label className="catalog-toggle">
        <input
          type="checkbox"
          checked={draft.enabled}
          onChange={(event) =>
            setDraft({ ...draft, enabled: event.target.checked })
          }
        />
        启用
      </label>
    </>
  );

  const title =
    section === "skills"
      ? "Skill 基本信息"
      : section === "agents"
        ? "Agent 基本信息"
        : "Super Agent 基本信息";

  return (
    <>
      <header className="account-heading">
        <h1>Agent 资源管理</h1>
        <p>{status || "配置全局能力与 Agent"}</p>
      </header>
      <div className="catalog-tabs" role="tablist">
        <button
          className={section === "skills" ? "active" : ""}
          onClick={() => chooseSection("skills")}
        >
          <Sparkles /> Skills
        </button>
        <button
          className={section === "agents" ? "active" : ""}
          onClick={() => chooseSection("agents")}
        >
          <Bot /> Agents
        </button>
        <button
          className={section === "superAgents" ? "active" : ""}
          onClick={() => chooseSection("superAgents")}
        >
          <Users /> Super Agents
        </button>
      </div>
      <div className="catalog-resource-bar">
        <button
          className={!selectedId ? "active" : ""}
          onClick={() => {
            setSelectedId(null);
            setDraft(emptyDraft());
            setFormError("");
          }}
        >
          <Plus /> 新建
        </button>
        {resources.map((resource) => (
          <button
            key={resource.id}
            className={selectedId === resource.id ? "active" : ""}
            onClick={() => editResource(resource)}
          >
            {"skillName" in resource ? resource.skillName : resource.name}
          </button>
        ))}
      </div>
      <form
        className={`catalog-editor ${section === "skills" ? "skill-editor" : ""}`}
        onSubmit={save}
      >
        <section className={`catalog-panel agent-create-form ${section === "skills" ? "skill-form" : ""}`}>
          <h2>{title}</h2>
          {section === "skills" && (
            <div className="skill-form-columns">
              <div className="skill-form-details">
                {basicFields}
                <label>
                  Handler
                  <select
                    required
                    value={draft.handler}
                    onChange={(event) =>
                      setDraft({ ...draft, handler: event.target.value })
                    }
                  >
                    <option value="">请选择 Skill</option>
                    {(catalog?.skillHandlers ?? []).map((handler) => (
                      <option key={handler} value={handler}>
                        {handler}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  版本
                  <input
                    required
                    maxLength={20}
                    value={draft.version}
                    onChange={(event) =>
                      setDraft({ ...draft, version: event.target.value })
                    }
                  />
                </label>
              </div>
              <div className="skill-form-schemas">
                <label>
                  Input Schema
                  <textarea
                    required
                    value={draft.inputSchema}
                    onBlur={() => formatJsonField("inputSchema")}
                    onChange={(event) =>
                      setDraft({ ...draft, inputSchema: event.target.value })
                    }
                  />
                </label>
                <label>
                  Output Schema
                  <textarea
                    required
                    value={draft.outputSchema}
                    onBlur={() => formatJsonField("outputSchema")}
                    onChange={(event) =>
                      setDraft({ ...draft, outputSchema: event.target.value })
                    }
                  />
                </label>
                <label>
                  Execution Config
                  <textarea
                    required
                    value={draft.executionConfig}
                    onBlur={() => formatJsonField("executionConfig")}
                    onChange={(event) =>
                      setDraft({ ...draft, executionConfig: event.target.value })
                    }
                  />
                </label>
              </div>
            </div>
          )}
          {section !== "skills" && basicFields}
          {(section === "agents" || section === "superAgents") && (
            <label>
              System prompt
              <textarea
                required
                value={draft.systemPrompt}
                onChange={(event) =>
                  setDraft({ ...draft, systemPrompt: event.target.value })
                }
              />
            </label>
          )}
          {formError && <p className="catalog-form-error">{formError}</p>}
          <div className="catalog-form-actions">
            <button disabled={saving} type="submit">
              <Check /> {saving ? "保存中" : "保存"}
            </button>
            {section === "skills" && selectedId !== null && (
              <button
                className="danger"
                disabled={saving || selectedSkillIsAssigned}
                title={
                  selectedSkillIsAssigned
                    ? "该 Skill 已关联 Agent，无法删除"
                    : "删除 Skill"
                }
                type="button"
                onClick={() => void deleteSkill()}
              >
                <Trash2 /> 删除
              </button>
            )}
          </div>
        </section>
        {section === "agents" && (
          <section className="catalog-panel capability-panel">
            <div>
              <h2>Skills</h2>
              {(catalog?.skills ?? []).length ? (
                <div className="catalog-options">
                  {(catalog?.skills ?? []).map((skill) => (
                    <label key={skill.id}>
                      <input
                        type="checkbox"
                        checked={draft.skillIds.includes(skill.id)}
                        onChange={() => toggleSkillId(skill.id)}
                      />
                      <span>
                        <strong>{skill.skillName}</strong>
                        <small>{skill.description || skill.skillCode}</small>
                      </span>
                    </label>
                  ))}
                </div>
              ) : (
                <p className="catalog-empty">暂无 Skill</p>
              )}
            </div>
          </section>
        )}
        {section === "superAgents" && (
          <section className="catalog-panel capability-panel">
            <div>
              <h2>Agents</h2>
              {agentOptions(catalog?.agents ?? [])}
            </div>
          </section>
        )}
      </form>
    </>
  );
}
