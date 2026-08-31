import { Bot, Check, Plus, Server, Users, Wrench } from "lucide-react";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { apiUrl } from "./api";
import type {
  AgentCatalog,
  ManagedAgent,
  McpServerDefinition,
  SuperAgent,
  ToolDefinition,
} from "./types";

type CatalogSection = "tools" | "mcpServers" | "agents" | "superAgents";
type CatalogResource = ToolDefinition | McpServerDefinition | ManagedAgent | SuperAgent;

interface CatalogDraft {
  name: string;
  slug: string;
  description: string;
  handler: string;
  transport: "http" | "sse";
  url: string;
  systemPrompt: string;
  enabled: boolean;
  toolIds: string[];
  mcpServerIds: string[];
  agentIds: string[];
}

const emptyDraft = (): CatalogDraft => ({
  name: "",
  slug: "",
  description: "",
  handler: "",
  transport: "http",
  url: "",
  systemPrompt: "",
  enabled: true,
  toolIds: [],
  mcpServerIds: [],
  agentIds: [],
});

export function CatalogManager() {
  const [catalog, setCatalog] = useState<AgentCatalog | null>(null);
  const [section, setSection] = useState<CatalogSection>("agents");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<CatalogDraft>(emptyDraft);
  const [status, setStatus] = useState("");
  const [saving, setSaving] = useState(false);

  const loadCatalog = async () => {
    const response = await fetch(apiUrl("/agents/catalog"), { credentials: "include" });
    const payload = (await response.json()) as AgentCatalog & { message?: string };
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
  };

  const editResource = (resource: CatalogResource) => {
    setSelectedId(resource.id);
    setDraft({
      ...emptyDraft(),
      ...resource,
      description: resource.description ?? "",
      handler: "handler" in resource ? resource.handler : "",
      transport: "transport" in resource ? resource.transport : "http",
      url: "url" in resource ? resource.url : "",
      systemPrompt: "systemPrompt" in resource ? resource.systemPrompt : "",
      toolIds: "toolIds" in resource ? resource.toolIds : [],
      mcpServerIds: "mcpServerIds" in resource ? resource.mcpServerIds : [],
      agentIds: "agentIds" in resource ? resource.agentIds : [],
    });
  };

  const save = async (event: FormEvent) => {
    event.preventDefault();
    if (saving) return;
    setSaving(true);
    setStatus("正在保存");
    try {
      const endpoints: Record<CatalogSection, string> = {
        tools: "/agents/tools",
        mcpServers: "/agents/mcp-servers",
        agents: "/agents",
        superAgents: "/agents/super",
      };
      const base = {
        name: draft.name,
        slug: draft.slug,
        description: draft.description || null,
        enabled: draft.enabled,
      };
      const bodies: Record<CatalogSection, object> = {
        tools: { ...base, handler: draft.handler },
        mcpServers: { ...base, transport: draft.transport, url: draft.url },
        agents: {
          ...base,
          systemPrompt: draft.systemPrompt,
          toolIds: draft.toolIds,
          mcpServerIds: draft.mcpServerIds,
        },
        superAgents: {
          ...base,
          systemPrompt: draft.systemPrompt,
          agentIds: draft.agentIds,
        },
      };
      const suffix = selectedId ? `/${selectedId}` : "";
      const response = await fetch(apiUrl(`${endpoints[section]}${suffix}`), {
        method: selectedId ? "PUT" : "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(bodies[section]),
      });
      const payload = (await response.json()) as { id?: string; message?: string };
      if (!response.ok || !payload.id) throw new Error(payload.message ?? "保存失败");
      await loadCatalog();
      setSelectedId(payload.id);
      setStatus("已保存");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "操作失败");
    } finally {
      setSaving(false);
    }
  };

  const resources: CatalogResource[] = catalog?.[section] ?? [];
  const toggleId = (field: "toolIds" | "mcpServerIds" | "agentIds", id: string) => {
    setDraft((current) => ({
      ...current,
      [field]: current[field].includes(id)
        ? current[field].filter((value) => value !== id)
        : [...current[field], id],
    }));
  };

  const options = (
    items: Array<ToolDefinition | McpServerDefinition | ManagedAgent>,
    field: "toolIds" | "mcpServerIds" | "agentIds",
    emptyText: string,
  ) => items.length ? (
    <div className="catalog-options">
      {items.map((item) => (
        <label key={item.id}>
          <input type="checkbox" checked={draft[field].includes(item.id)} onChange={() => toggleId(field, item.id)} />
          <span><strong>{item.name}</strong><small>{item.description || item.slug}</small></span>
        </label>
      ))}
    </div>
  ) : <p className="catalog-empty">{emptyText}</p>;

  const basicFields = <>
    <label>名称<input required maxLength={120} value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} /></label>
    <label>Slug<input required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" value={draft.slug} onChange={(event) => setDraft({ ...draft, slug: event.target.value.toLowerCase() })} /></label>
    <label>描述<textarea className="compact-textarea" maxLength={2000} value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} /></label>
    <label className="catalog-toggle"><input type="checkbox" checked={draft.enabled} onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })} />启用</label>
  </>;

  const title = section === "tools" ? "Tool 基本信息" : section === "mcpServers" ? "MCP 基本信息" : section === "agents" ? "Agent 基本信息" : "Super Agent 基本信息";

  return <>
    <header className="account-heading">
      <h1>Agent 资源管理</h1>
      <p>{status || "配置全局能力与 Agent"}</p>
    </header>
    <div className="catalog-tabs" role="tablist">
      <button className={section === "tools" ? "active" : ""} onClick={() => chooseSection("tools")}><Wrench /> Tools</button>
      <button className={section === "mcpServers" ? "active" : ""} onClick={() => chooseSection("mcpServers")}><Server /> MCPs</button>
      <button className={section === "agents" ? "active" : ""} onClick={() => chooseSection("agents")}><Bot /> Agents</button>
      <button className={section === "superAgents" ? "active" : ""} onClick={() => chooseSection("superAgents")}><Users /> Super Agents</button>
    </div>
    <div className="catalog-resource-bar">
      <button className={!selectedId ? "active" : ""} onClick={() => { setSelectedId(null); setDraft(emptyDraft()); }}><Plus /> 新建</button>
      {resources.map((resource) => <button key={resource.id} className={selectedId === resource.id ? "active" : ""} onClick={() => editResource(resource)}>{resource.name}</button>)}
    </div>
    <form className={`catalog-editor ${section === "tools" || section === "mcpServers" ? "single" : ""}`} onSubmit={save}>
      <section className="catalog-panel agent-create-form">
        <h2>{title}</h2>
        {basicFields}
        {section === "tools" && <label>Handler<input required value={draft.handler} onChange={(event) => setDraft({ ...draft, handler: event.target.value })} placeholder="app.tools.search" /></label>}
        {section === "mcpServers" && <><label>Transport<select value={draft.transport} onChange={(event) => setDraft({ ...draft, transport: event.target.value as "http" | "sse" })}><option value="http">HTTP</option><option value="sse">SSE</option></select></label><label>URL<input required type="url" value={draft.url} onChange={(event) => setDraft({ ...draft, url: event.target.value })} /></label></>}
        {(section === "agents" || section === "superAgents") && <label>System prompt<textarea required value={draft.systemPrompt} onChange={(event) => setDraft({ ...draft, systemPrompt: event.target.value })} /></label>}
        <button disabled={saving} type="submit"><Check /> {saving ? "保存中" : "保存"}</button>
      </section>
      {section === "agents" && <section className="catalog-panel capability-panel"><div><h2>Tools</h2>{options(catalog?.tools ?? [], "toolIds", "暂无 Tool")}</div><div><h2>MCPs</h2>{options(catalog?.mcpServers ?? [], "mcpServerIds", "暂无 MCP")}</div></section>}
      {section === "superAgents" && <section className="catalog-panel capability-panel"><div><h2>Agents</h2>{options(catalog?.agents ?? [], "agentIds", "暂无 Agent")}</div></section>}
    </form>
  </>;
}
