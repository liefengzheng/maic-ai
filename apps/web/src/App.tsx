import { useAtom } from "jotai";
import {
  ArrowLeft,
  Bot,
  BotMessageSquare,
  Check,
  CircleUserRound,
  CreditCard,
  Home as HomeIcon,
  KeyRound,
  Lightbulb,
  LogOut,
  MessageSquareText,
  PanelLeft,
  Plus,
  Search,
  SendHorizontal,
  Settings,
  Settings2,
  Sparkles,
  Upload,
} from "lucide-react";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
  Link,
  NavLink,
  Navigate,
  Route,
  Routes,
  useNavigate,
} from "react-router-dom";
import { apiUrl } from "./api";
import { CatalogManager } from "./CatalogManager";
import { capabilities, changelog, scenes } from "./content";
import { authResolvedAtom, userAtom } from "./state";
import type { AgentChoice, ChatMessage, Conversation, User } from "./types";
import { loginSchema, registerSchema } from "./validation";

function AgentMark({ compact = false }: { compact?: boolean }) {
  return (
    <span
      className={`agent-mark${compact ? " compact" : ""}`}
      aria-hidden="true"
    >
      <BotMessageSquare />
      <Sparkles />
    </span>
  );
}

function Header() {
  const [user] = useAtom(userAtom);
  return (
    <header className="site-header">
      <Link className="brand" to="/">
        <AgentMark compact /> MAIC AI <small>TOP</small>
      </Link>
      <nav>
        <NavLink to="/product">产品能力</NavLink>
        <NavLink to="/workflow-memory">工作记忆</NavLink>
        <NavLink to="/scenes">真实场景</NavLink>
        <NavLink to="/workshops">工作坊</NavLink>
        <NavLink to="/changelog">更新日志</NavLink>
        <NavLink to="/chat">网页版 Chat</NavLink>
      </nav>
      <div className="header-actions">
        {user ? (
          <Link className="user-link" to="/account">
            {user.displayName}
          </Link>
        ) : (
          <Link className="text-link" to="/login">
            登录
          </Link>
        )}
        <Link className="button dark" to="/chat">
          进入 Chat
        </Link>
      </div>
    </header>
  );
}

function ProductSection() {
  return (
    <section id="product" className="hero-section">
      <p className="eyebrow">01 -- PRODUCT LOGIC</p>
      <h1>
        不是把所有事都塞进聊天框，
        <br />
        而是给不同工作选择不同模式。
      </h1>
      <div className="split-cards">
        <article>
          <MessageSquareText />
          <p className="eyebrow">网页端 CHAT</p>
          <h2>网页端保留快速问答入口。</h2>
          <p>轻量问答、快速构思与已有网页能力，打开即用。</p>
        </article>
        <article>
          <Bot />
          <p className="eyebrow">AGENT</p>
          <h2>复杂任务，交给 Agent 推进结果。</h2>
          <p>把文件、过程、权限和交付物收进可追踪的执行流。</p>
        </article>
      </div>
    </section>
  );
}

function WorkflowMemorySection() {
  return (
    <section id="workflow-memory" className="editorial-section">
      <p className="eyebrow">02 -- WORKFLOW MEMORY</p>
      <h2>每一次工作，都成为下一次更好的开始。</h2>
      <div className="feature-grid">
        {capabilities.map(([title, description]) => (
          <article key={title}>
            <Check />
            <h3>{title}</h3>
            <p>{description}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function ScenesSection() {
  return (
    <section id="scenes" className="editorial-section scenes-section">
      <p className="eyebrow">03 -- REAL SCENES</p>
      <h2>
        真实工作里的 AI，
        <br />
        不只要回答，还要推进和交付。
      </h2>
      <ol>
        {scenes.map((scene, index) => (
          <li key={scene}>
            <span>0{index + 1}</span>
            {scene}
          </li>
        ))}
      </ol>
    </section>
  );
}

function Home() {
  return (
    <div className="marketing-page">
      <Header />
      <main>
        <ProductSection />
        <WorkflowMemorySection />
        <ScenesSection />
        <section className="editorial-section">
          <p className="eyebrow">04 -- WORKSHOP</p>
          <h2>从真实工作出发，设计可以持续迭代的流程。</h2>
          <Link className="button dark" to="/workshops">
            查看工作坊预约
          </Link>
        </section>
      </main>
      <Footer />
    </div>
  );
}

function Product() {
  return (
    <MarketingPage>
      <ProductSection />
    </MarketingPage>
  );
}

function WorkflowMemory() {
  return (
    <MarketingPage>
      <WorkflowMemorySection />
    </MarketingPage>
  );
}

function Scenes() {
  return (
    <MarketingPage>
      <ScenesSection />
    </MarketingPage>
  );
}

function MarketingPage({ children }: { children: React.ReactNode }) {
  return (
    <div className="marketing-page">
      <Header />
      <main>{children}</main>
      <Footer />
    </div>
  );
}

function Footer() {
  return (
    <footer>
      <strong className="footer-brand">
        <AgentMark compact /> MAIC AI
      </strong>
      <span>COLOPHON</span>
      <Link to="/workshops">工作坊</Link>
      <Link to="/changelog">更新日志</Link>
      <Link to="/login">登录</Link>
    </footer>
  );
}

function Login() {
  const [user, setUser] = useAtom(userAtom);
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [toast, setToast] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 5_000);
  };
  const login = async (event: FormEvent) => {
    event.preventDefault();
    const parsed = loginSchema.safeParse({ email, password });
    if (!accepted) return showToast("请先同意用户协议和隐私政策");
    if (!parsed.success) return showToast(parsed.error.issues[0].message);
    setSubmitting(true);
    try {
      const response = await fetch(apiUrl("/auth/login"), {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(parsed.data),
      });
      const payload = (await response.json()) as {
        user?: User;
        message?: string;
      };
      if (!response.ok || !payload.user) {
        showToast(
          response.status === 401
            ? "Request failed with status code 401"
            : (payload.message ??
                `Request failed with status code ${response.status}`),
        );
        return;
      }
      setUser(payload.user);
      navigate("/chat");
    } catch {
      showToast("Request failed: unable to reach the API");
    } finally {
      setSubmitting(false);
    }
  };
  if (user) return <Navigate to="/chat" replace />;
  return (
    <main className="auth-page">
      {toast && (
        <div className="toast toast-error" role="alert">
          {toast}
        </div>
      )}
      <section className="login-panel">
        <Link className="back-link" to="/">
          <ArrowLeft /> 返回官网首页
        </Link>
        <div className="login-brand">
          <AgentMark />
          <h1>MAIC AI</h1>
        </div>
        <p>登录您的账号</p>
        <form onSubmit={login}>
          <label>
            邮箱
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              placeholder="your@email.com"
              required
            />
          </label>
          <label>
            密码
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              required
            />
          </label>
          <label className="consent">
            <input
              checked={accepted}
              onChange={(e) => setAccepted(e.target.checked)}
              type="checkbox"
            />{" "}
            我已阅读并同意《用户协议》和《隐私政策》
          </label>
          <button className="button submit" type="submit" disabled={submitting}>
            {submitting ? "登录中..." : "登录"}
          </button>
        </form>
        <div className="or">或</div>
        <a className="google-button" href={apiUrl("/auth/google")}>
          <span className="google-g" aria-hidden="true">
            G
          </span>
          <span>使用 Google 登录</span>
        </a>
        <p className="muted">
          还没有账号？{" "}
          <Link className="auth-link" to="/register">
            立即注册
          </Link>
        </p>
      </section>
    </main>
  );
}

function Register() {
  const [user, setUser] = useAtom(userAtom);
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState("");
  const register = async (event: FormEvent) => {
    event.preventDefault();
    if (!accepted) return setError("请先同意用户协议和隐私政策");
    if (password !== confirmPassword) return setError("两次输入的密码不一致");
    const parsed = registerSchema.safeParse({ displayName, email, password });
    if (!parsed.success) return setError(parsed.error.issues[0].message);
    const response = await fetch(apiUrl("/auth/register"), {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(parsed.data),
    });
    const payload = (await response.json()) as {
      user?: User;
      message?: string;
    };
    if (!response.ok || !payload.user)
      return setError(payload.message ?? "注册失败，请稍后重试");
    setUser(payload.user);
    navigate("/account");
  };
  if (user) return <Navigate to="/account" replace />;
  return (
    <main className="auth-page">
      <section className="login-panel">
        <Link className="back-link" to="/">
          <ArrowLeft /> 返回官网首页
        </Link>
        <div className="login-brand">
          <AgentMark />
          <h1>MAIC AI</h1>
        </div>
        <p>创建您的账号</p>
        <form onSubmit={register}>
          <label>
            姓名
            <input
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder="您的姓名"
              required
            />
          </label>
          <label>
            邮箱
            <input
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              type="email"
              placeholder="your@email.com"
              required
            />
          </label>
          <label>
            密码
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              placeholder="至少 8 位"
              required
            />
          </label>
          <label>
            确认密码
            <input
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              type="password"
              placeholder="再次输入密码"
              required
            />
          </label>
          <label className="consent">
            <input
              checked={accepted}
              onChange={(event) => setAccepted(event.target.checked)}
              type="checkbox"
            />{" "}
            我已阅读并同意《用户协议》和《隐私政策》
          </label>
          {error && <p className="form-error">{error}</p>}
          <button className="button submit" type="submit">
            注册
          </button>
        </form>
        <div className="or">或</div>
        <a className="google-button" href={apiUrl("/auth/google")}>
          <span className="google-g" aria-hidden="true">
            G
          </span>
          <span>使用 Google 注册</span>
        </a>
        <p className="muted">
          已有账号？ <Link to="/login">立即登录</Link>
        </p>
      </section>
    </main>
  );
}

type AccountSection =
  | "billing"
  | "usage"
  | "agents"
  | "models"
  | "prompts"
  | "keys"
  | "profile"
  | "changelog";

function Account() {
  const [user, setUser] = useAtom(userAtom);
  const [section, setSection] = useState<AccountSection>("billing");
  const logout = async () => {
    await fetch(apiUrl("/auth/logout"), {
      method: "POST",
      credentials: "include",
    }).catch(() => undefined);
    setUser(null);
  };
  if (!user) return <Navigate to="/login" replace />;
  const nav: [AccountSection, string, typeof CreditCard][] = [
    ["billing", "订阅与计费", CreditCard],
    ["usage", "用量日志", Settings2],
    ["models", "模型配置", Sparkles],
    ["prompts", "提示词管理", MessageSquareText],
    ["keys", "API Keys", KeyRound],
    ["profile", "个人资料", CircleUserRound],
    ["changelog", "更新日志", MessageSquareText],
  ];
  if (user.role === "admin") {
    nav.splice(2, 0, ["agents", "Agent 管理", Bot]);
  }
  return (
    <div className="account-layout">
      <aside>
        <Link to="/chat" className="back-link">
          <ArrowLeft /> 返回聊天
        </Link>
        <h2>个人中心</h2>
        <nav className="account-nav">
          {nav.map(([id, label, Icon]) => (
            <button
              className={section === id ? "active" : ""}
              key={id}
              onClick={() => setSection(id)}
            >
              <Icon />
              {label}
            </button>
          ))}
        </nav>
        <button className="account-logout" onClick={logout}>
          <LogOut />
          退出登录
        </button>
      </aside>
      <main className="account-main">
        <AccountPanel section={section} user={user} setUser={setUser} />
      </main>
    </div>
  );
}

function AccountPanel({
  section,
  user,
  setUser,
}: {
  section: AccountSection;
  user: User;
  setUser: (user: User) => void;
}) {
  const [prompts, setPrompts] = useState(["默认系统提示词"]);
  const [promptName, setPromptName] = useState("");
  const [apiKeys, setApiKeys] = useState<string[]>([]);
  const [name, setName] = useState(user.displayName);
  if (section === "agents") return <CatalogManager />;
  if (section === "billing")
    return (
      <>
        <header className="account-heading">
          <h1>订阅与计费</h1>
          <p>查看余额，选择订阅档位</p>
        </header>
        <section className="balance">
          <div className="balance-total">
            <small>总可用额度</small>
            <strong>0.00 积分</strong>
          </div>
          <div className="balance-stats">
            <small>
              累计充值<b>0.00 积分</b>
            </small>
            <small>
              本月用量<b>0.00 积分</b>
            </small>
            <small>
              累计用量<b>0.00 积分</b>
            </small>
          </div>
        </section>
        <p className="plan-lead">推荐从低档位开始，随时可叠加更多额度。</p>
        <section className="plans">
          {[
            ["Lite", "¥100", "100 积分/月"],
            ["Standard", "¥200", "210 积分/月"],
            ["Pro", "¥500", "530 积分/月"],
            ["Max", "¥1000", "1100 积分/月"],
          ].map(([title, price, quota]) => (
            <article key={title} className={title.toLowerCase()}>
              <h3>{title}</h3>
              <small>{quota}</small>
              <strong>
                {price}
                <em>/月</em>
              </strong>
              <button>立即订阅 · {price}</button>
              <hr />
              <p>
                包含：
                <br />✓ 全部顶尖 AI 模型
                <br />✓ Claude API 访问
                <br />✓ MAIC Agent
                <br />✓ Agent 开发
                <br />✓ 多模态模型支持
              </p>
            </article>
          ))}
        </section>
        <section className="account-note">
          ⓘ 所有模型价格均与官方 API 计价保持一致。订阅有效期 31
          天，额度按购买顺序优先消耗。
        </section>
      </>
    );
  if (section === "usage")
    return (
      <>
        <header className="account-heading">
          <h1>用量日志</h1>
          <p>查看你的模型用量</p>
        </header>
        <div className="account-tabs">
          <button className="active">Chat</button>
          <button>Speech</button>
          <button>Tool</button>
          <button>Agents</button>
        </div>
        <section className="usage-stats">
          {[
            ["Requests", "0"],
            ["Input Tokens", "0"],
            ["Output Tokens", "0"],
            ["Total Cost", "0.000000 积分"],
          ].map(([label, value]) => (
            <article key={label}>
              <small>{label}</small>
              <strong>{value}</strong>
            </article>
          ))}
        </section>
        <div className="period-tabs">
          <button className="active">今天</button>
          <button>昨天</button>
          <button>全部</button>
        </div>
        <section className="account-table">
          <div className="empty-state">No data</div>
        </section>
      </>
    );
  if (section === "models")
    return (
      <>
        <header className="account-heading">
          <h1>模型配置</h1>
          <p>查看可用的 AI 模型和计费信息</p>
        </header>
        <div className="account-tabs">
          <button className="active">语言模型</button>
          <button>多模态模型</button>
        </div>
        {[
          [
            "Anthropic",
            [
              "Claude Sonnet 5.67 折",
              "Claude Opus 5",
              "Claude Opus 4.8",
              "Claude Fable 5",
            ],
          ],
          ["DeepClaude", ["DeepGeminiPro"]],
        ].map(([provider, models]) => (
          <section className="model-group" key={provider as string}>
            <h2>{provider as string}</h2>
            <small>{(models as string[]).length} 个可用模型</small>
            {(models as string[]).map((model) => (
              <label key={model}>
                <span>
                  <strong>{model}</strong>
                  <small>{model.toLowerCase().replaceAll(" ", "-")}</small>
                </span>
                <b>推荐</b>
                <em>
                  输入：$2.0000/1M
                  <br />
                  输出：$10.0000/1M
                </em>
              </label>
            ))}
          </section>
        ))}
      </>
    );
  if (section === "prompts")
    return (
      <div className="prompts-page">
        <aside>
          <label className="prompt-search">
            <Search />
            <input placeholder="搜索提示词..." />
          </label>
          <button
            className="new-prompt"
            onClick={() => {
              if (promptName.trim()) {
                setPrompts([...prompts, promptName.trim()]);
                setPromptName("");
              }
            }}
          >
            ＋ 新建提示词
          </button>
          <input
            value={promptName}
            onChange={(event) => setPromptName(event.target.value)}
            placeholder="新提示词名称"
          />
          <p>我的提示词</p>
          {prompts.map((prompt) => (
            <button className="prompt-item" key={prompt}>
              {prompt}
            </button>
          ))}
        </aside>
        <section>
          <header className="account-heading">
            <h1>MAIC 默认系统提示词</h1>
            <p>默认提示词</p>
          </header>
          <article className="prompt-content">
            你首先是一个大型模型，这我们当然知道。你现在的任务是作为 MAIC AI
            助手，帮助我解决实际问题。
            <br />
            <br />
            请根据上下文尽可能直接解决问题；当信息不足时，再提出清晰的补充问题。输出应结构化、可执行，并保持必要的简洁。
          </article>
        </section>
      </div>
    );
  if (section === "keys")
    return (
      <>
        <header className="account-heading account-heading-row">
          <span>
            <h1>API Keys</h1>
            <p>管理您的 API 密钥，用于访问 MAIC API</p>
          </span>
          <button
            onClick={() =>
              setApiKeys([
                ...apiKeys,
                `maic_${crypto.randomUUID().replaceAll("-", "").slice(0, 24)}`,
              ])
            }
          >
            ＋ 创建 API Key
          </button>
        </header>
        <section className="api-guide">
          <h2>API 使用说明</h2>
          <p>
            使用 API Key 可以通过 HTTP 请求访问 MAIC API，兼容 OpenAI 格式。
          </p>
          <pre>
            curl https://api.maic.ai/v1/chat/completions{`\n`} -H
            "Authorization: Bearer YOUR_API_KEY"
          </pre>
        </section>
        <section className="account-table">
          <h2>API Keys 列表</h2>
          {apiKeys.length ? (
            apiKeys.map((key) => (
              <label className="key-row" key={key}>
                <span>
                  <strong>{key}</strong>
                  <small>刚刚创建</small>
                </span>
                <button
                  onClick={() =>
                    setApiKeys(apiKeys.filter((item) => item !== key))
                  }
                >
                  撤销
                </button>
              </label>
            ))
          ) : (
            <div className="empty-state">
              尚未创建 API Keys
              <br />
              <small>点击上方按钮创建您的第一个 API Key</small>
            </div>
          )}
        </section>
      </>
    );
  if (section === "profile")
    return (
      <>
        <header className="account-heading">
          <h1>个人资料</h1>
          <p>管理您的账户信息和头像</p>
        </header>
        <section className="profile-form avatar-panel">
          <h2>头像设置</h2>
          <p>上传一张图片作为您的头像</p>
          <div className="avatar-row">
            <span>{user.displayName.slice(0, 1).toUpperCase()}</span>
            <button>选择图片</button>
          </div>
        </section>
        <section className="profile-form">
          <h2>基本信息</h2>
          <label>
            用户名称
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label>
            邮箱地址
            <input value={user.email} readOnly />
          </label>
          <button
            onClick={() =>
              setUser({ ...user, displayName: name.trim() || user.displayName })
            }
          >
            保存更改
          </button>
        </section>
      </>
    );
  return (
    <>
      <header className="account-heading">
        <h1>更新日志</h1>
        <p>查看最新的功能更新和说明</p>
      </header>
      <article className="release-card">
        <small>v0.1.0 · 2026-08-23</small>
        <h2>MAIC AI v0.1.0 更新</h2>
        <h3>新功能</h3>
        <p>账户中心、会话恢复、网页 Chat 工作台及订阅页面首次发布。</p>
        <h3>改进</h3>
        <p>统一深色控制台界面和模型、提示词、API Key 管理流程。</p>
      </article>
    </>
  );
}

function Workshops() {
  return (
    <>
      <Header />
      <main className="content-page">
        <p className="eyebrow">MAIC WORKSHOP</p>
        <h1>把你的工作，拆成 AI 真能接手的流程。</h1>
        <section className="booking">
          <div>
            <p className="eyebrow">01 -- BOOKING</p>
            <h2>提交预约申请</h2>
            <p>每次 60 分钟，从你正在进行的业务开始梳理。</p>
          </div>
          <form>
            <input placeholder="姓名" />
            <input placeholder="公司 / 团队" />
            <input placeholder="联系方式" />
            <select>
              <option>选择预约时间</option>
              <option>周二 11:00 - 12:00</option>
              <option>周四 14:00 - 15:00</option>
            </select>
            <textarea placeholder="最关注的主题" />
            <button className="button dark">提交预约</button>
          </form>
        </section>
        <section className="agenda">
          <p className="eyebrow">03 -- AGENDA</p>
          <h2>工作坊会围绕一条实际导入路径推进。</h2>
          {[
            "先区分 Chat 和 Agent",
            "再搭工作区",
            "沉淀 Skills 与 MCP",
            "最后接入远程触发",
          ].map((item) => (
            <article key={item}>
              <h3>{item}</h3>
              <p>
                从真实流程、已有资料和交付标准出发，形成能够继续试点的方案。
              </p>
            </article>
          ))}
        </section>
      </main>
      <Footer />
    </>
  );
}

function Changelog() {
  return (
    <>
      <Header />
      <main className="content-page">
        <p className="eyebrow">MAIC AI CHANGELOG</p>
        <h1>更新日志</h1>
        {changelog.map((release) => (
          <article className="release" key={release.version}>
            <p>
              V{release.version} · {release.date}
            </p>
            <h2>MAIC AI v{release.version} 更新</h2>
            <ul>
              {release.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
        ))}
      </main>
      <Footer />
    </>
  );
}

function Chat() {
  const [user] = useAtom(userAtom);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<
    Pick<ChatMessage, "role" | "content">[]
  >([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [availableAgents, setAvailableAgents] = useState<AgentChoice[]>([]);
  const [selectedAgentKey, setSelectedAgentKey] = useState("default");
  const [conversationSearch, setConversationSearch] = useState("");
  const [activeConversationId, setActiveConversationId] = useState<
    string | null
  >(null);
  const [agentStatus, setAgentStatus] = useState("");
  const [sending, setSending] = useState(false);
  const activeConversation = conversations.find(
    ({ id }) => id === activeConversationId,
  );
  const selectedAgent = availableAgents.find(
    ({ id, kind }) => `${kind}:${id}` === selectedAgentKey,
  );
  const visibleConversations = conversations.filter(({ title }) =>
    title
      .toLocaleLowerCase()
      .includes(conversationSearch.trim().toLocaleLowerCase()),
  );

  useEffect(() => {
    if (!user) return;
    const loadConversations = async () => {
      const [conversationResponse, agentResponse] = await Promise.all([
        fetch(apiUrl("/conversations"), { credentials: "include" }),
        fetch(apiUrl("/agents/available"), { credentials: "include" }),
      ]);
      if (!conversationResponse.ok) return;
      const loaded = (await conversationResponse.json()) as Conversation[];
      setConversations(loaded);
      if (agentResponse.ok) {
        setAvailableAgents((await agentResponse.json()) as AgentChoice[]);
      }
      if (loaded[0]) {
        setActiveConversationId(loaded[0].id);
        setSelectedAgentKey(
          loaded[0].targetId
            ? `${loaded[0].targetKind}:${loaded[0].targetId}`
            : "default",
        );
      }
    };
    void loadConversations();
  }, [user]);

  useEffect(() => {
    if (!activeConversationId) {
      setMessages([]);
      return;
    }
    void fetch(apiUrl(`/conversations/${activeConversationId}/messages`), {
      credentials: "include",
    })
      .then((response) => (response.ok ? response.json() : []))
      .then((loaded: ChatMessage[]) => setMessages(loaded));
  }, [activeConversationId]);

  const beginConversation = (agentKey = selectedAgentKey) => {
    setMessages([]);
    setActiveConversationId(null);
    setSelectedAgentKey(agentKey);
    setAgentStatus("");
  };

  const openConversation = (conversation: Conversation) => {
    setActiveConversationId(conversation.id);
    setSelectedAgentKey(
      conversation.targetId
        ? `${conversation.targetKind}:${conversation.targetId}`
        : "default",
    );
    setAgentStatus("");
  };

  const createConversation = async () => {
    const response = await fetch(apiUrl("/conversations"), {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        title: "新对话",
        targetKind: selectedAgent?.kind ?? null,
        targetId: selectedAgent?.id ?? null,
      }),
    });
    if (!response.ok) throw new Error("创建对话失败");
    const conversation = (await response.json()) as Conversation;
    setConversations((current) => [conversation, ...current]);
    setActiveConversationId(conversation.id);
    return conversation.id;
  };

  const send = async () => {
    const content = draft.trim();
    if (!content || sending) return;
    setSending(true);
    setAgentStatus("正在思考");
    setDraft("");
    try {
      const conversationId =
        activeConversationId ?? (await createConversation());
      setMessages((current) => [
        ...current,
        { role: "user", content },
        { role: "assistant", content: "" },
      ]);
      const response = await fetch(
        apiUrl(`/conversations/${conversationId}/runs`),
        {
          method: "POST",
          credentials: "include",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ content }),
        },
      );
      if (!response.ok) {
        const error = (await response.json().catch(() => null)) as {
          message?: string;
        } | null;
        throw new Error(error?.message ?? "Agent 请求失败");
      }
      if (!response.body) throw new Error("Agent 请求失败");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        buffer += decoder.decode(value, { stream: !done });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";
        for (const event of events) {
          const eventName = event.match(/^event: (.+)$/m)?.[1];
          const rawData = event.match(/^data: (.+)$/m)?.[1];
          if (!rawData) continue;
          const payload = JSON.parse(rawData) as {
            content?: string;
            agent?: string;
            root?: boolean;
            name?: string;
            status?: string;
            message?: string;
          };
          if (
            eventName === "token" &&
            (payload.root === true ||
              (payload.root === undefined &&
                payload.agent === "coordinator")) &&
            payload.content
          ) {
            setMessages((current) =>
              current.map((message, index) =>
                index === current.length - 1
                  ? { ...message, content: message.content + payload.content }
                  : message,
              ),
            );
          } else if (eventName === "tool") {
            setAgentStatus(
              `${payload.agent}: ${payload.name} ${payload.status === "started" ? "运行中" : "已完成"}`,
            );
          } else if (eventName === "error") {
            throw new Error(payload.message ?? "Agent 执行失败");
          }
        }
        if (done) break;
      }
      setAgentStatus("");
    } catch (error) {
      setMessages((current) =>
        current.at(-1)?.role === "assistant" && !current.at(-1)?.content
          ? current.slice(0, -1)
          : current,
      );
      setAgentStatus(error instanceof Error ? error.message : "发送失败");
    } finally {
      setSending(false);
    }
  };

  if (!user) return <Login />;
  return (
    <main className="chat-workspace">
      <aside className="chat-sidebar">
        <div className="chat-brand">
          <AgentMark compact />
          <strong>MAIC AI</strong>
          <small>Chat 工作台</small>
        </div>
        <button className="new-chat" onClick={() => beginConversation()}>
          <Plus /> 创建新对话
        </button>
        <section className="agent-selector" aria-label="可用 Agent">
          <p className="chat-group-label">可用 Agent</p>
          <button
            className={`agent-option${selectedAgentKey === "default" ? " active" : ""}`}
            onClick={() => beginConversation("default")}
          >
            <Bot />
            <span>
              <strong>MAIC AI</strong>
              <small>默认协调 Agent</small>
            </span>
          </button>
          {availableAgents.map((agent) => {
            const key = `${agent.kind}:${agent.id}`;
            return (
              <button
                className={`agent-option${selectedAgentKey === key ? " active" : ""}`}
                key={key}
                title={agent.description ?? agent.name}
                onClick={() => beginConversation(key)}
              >
                {agent.kind === "super_agent" ? <Sparkles /> : <Bot />}
                <span>
                  <strong>{agent.name}</strong>
                  <small>
                    {agent.kind === "super_agent" ? "SuperAgent" : "Agent"}
                  </small>
                </span>
              </button>
            );
          })}
        </section>
        <p className="chat-group-label history-label">历史记录</p>
        <label className="chat-search">
          <Search />
          <input
            value={conversationSearch}
            onChange={(event) => setConversationSearch(event.target.value)}
            placeholder="搜索对话..."
          />
        </label>
        <div className="conversation-list">
          {visibleConversations.map((conversation) => (
            <button
              className={`conversation${conversation.id === activeConversationId ? " active" : ""}`}
              key={conversation.id}
              title={conversation.targetName ?? "MAIC AI"}
              onClick={() => openConversation(conversation)}
            >
              {conversation.title}
            </button>
          ))}
          {visibleConversations.length === 0 && (
            <p className="chat-sidebar-note">
              {conversationSearch ? "没有匹配的对话" : "还没有历史对话"}
            </p>
          )}
        </div>
        <div className="chat-sidebar-bottom">
          <Link to="/">
            <HomeIcon /> 官网首页
          </Link>
          <Link to="/account">
            <CircleUserRound /> 个人中心
          </Link>
          <Link to="/account">
            <CreditCard /> 订阅与计费
          </Link>
          <button>
            <Upload /> 导入对话
          </button>
          <Link to="/changelog">
            <MessageSquareText /> 更新日志
          </Link>
          <div className="chat-user">
            <span>{user.displayName.slice(0, 1).toUpperCase()}</span>
            <div>
              <strong>{user.displayName}</strong>
              <small>{user.email}</small>
            </div>
            <Link to="/account" aria-label="账户设置">
              <Settings />
            </Link>
          </div>
        </div>
      </aside>
      <section className="chat-main">
        <header className="chat-topbar">
          <h1>{activeConversation?.title ?? "新对话"}</h1>
          <div>
            <button aria-label="切换侧栏">
              <PanelLeft />
            </button>
            <span className="system-prompt">
              <MessageSquareText /> {selectedAgent?.name ?? "MAIC AI"}
            </span>
          </div>
        </header>
        <div className="chat-messages">
          {messages.map((message, index) => (
            <div
              className={`chat-message-row ${message.role}`}
              key={`${message.role}-${index}`}
            >
              {message.role === "user" ? (
                <span
                  className="chat-message-avatar user-avatar"
                  aria-label={`${user.displayName} 的头像`}
                >
                  {user.avatarUrl ? (
                    <img src={user.avatarUrl} alt="" />
                  ) : (
                    user.displayName.slice(0, 1).toUpperCase()
                  )}
                </span>
              ) : (
                <span
                  className="chat-message-avatar agent-avatar"
                  aria-label={`${selectedAgent?.name ?? "MAIC AI"} 的图标`}
                >
                  <AgentMark compact />
                </span>
              )}
              <article className={`chat-message ${message.role}`}>
                {message.content}
              </article>
            </div>
          ))}
          {agentStatus && <p className="chat-sidebar-note">{agentStatus}</p>}
        </div>
        <div className="chat-composer">
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void send();
              }
            }}
            placeholder="有什么可以帮助到你的？"
          />
          <div className="composer-toolbar">
            <button aria-label="添加附件">
              <Plus />
            </button>
            <button aria-label="启用思考">
              <Lightbulb />
            </button>
            <span>0%</span>
            <div className="model-picker-anchor">
              <span className="model-select">
                <Bot /> <span>{selectedAgent?.name ?? "MAIC AI"}</span>
              </span>
            </div>
            <button
              className="send-button"
              onClick={() => void send()}
              aria-label="发送"
              disabled={sending}
            >
              <SendHorizontal />
            </button>
          </div>
        </div>
        <p className="chat-hint">
          MAIC 支持临时对话模式，按 <kbd>Ctrl</kbd> + <kbd>T</kbd>{" "}
          可开启临时对话。
        </p>
      </section>
    </main>
  );
}

export default function App() {
  const [, setUser] = useAtom(userAtom);
  const [authResolved, setAuthResolved] = useAtom(authResolvedAtom);
  useEffect(() => {
    fetch(apiUrl("/auth/me"), { credentials: "include" })
      .then(async (response) =>
        response.ok ? ((await response.json()) as { user: User }).user : null,
      )
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setAuthResolved(true));
  }, [setAuthResolved, setUser]);
  if (!authResolved)
    return (
      <main className="session-loading" aria-label="正在恢复登录状态">
        <AgentMark />
      </main>
    );
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/account" element={<Account />} />
      <Route path="/product" element={<Product />} />
      <Route path="/workflow-memory" element={<WorkflowMemory />} />
      <Route path="/scenes" element={<Scenes />} />
      <Route path="/workshops" element={<Workshops />} />
      <Route path="/changelog" element={<Changelog />} />
      <Route path="/chat" element={<Chat />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
