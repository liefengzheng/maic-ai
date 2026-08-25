export const capabilities = [
  ["网页端 Chat", "用轻量对话快速梳理问题，留下清晰的下一步。"],
  ["Agent 工作流", "把文件、工具、过程与交付物放进可追踪的执行流。"],
  ["工作区记忆", "为每项工作保留独立上下文，让经验持续生长。"],
  ["Skills 与 MCP", "把团队方法和外部服务连接为可复用能力。"],
] as const;

export const scenes = [
  "把访谈、反馈和 issue 汇总成有证据的优先级。",
  "读取资料、搜索信息并产出结构化研究报告。",
  "把固定的判断标准沉淀成可触发的 Skills。",
  "从移动端或群聊把临时想法派发成任务。",
] as const;

export const changelog = [
  { version: "0.1.0", date: "2026-08-23", items: ["MAIC AI 网页端首个公开版本。", "支持账户、工作坊预约与结构化 Chat。"] },
  { version: "0.0.9", date: "2026-08-16", items: ["完成产品能力与真实场景内容编排。"] },
] as const;