import { config as loadEnv } from "dotenv";
import { fileURLToPath } from "node:url";
import bcrypt from "bcryptjs";
import cookie from "@fastify/cookie";
import cors from "@fastify/cors";
import oauthPlugin from "@fastify/oauth2";
import Fastify, { type FastifyReply } from "fastify";
import type { AuthResponse, User } from "@maic/types";
import { loginSchema, registerSchema, workshopBookingSchema } from "@maic/validation";
import { db } from "./db.js";
import { issueSession, readSession } from "./auth.js";

loadEnv({ path: fileURLToPath(new URL("../.env", import.meta.url)) });
const app = Fastify({ logger: true });
const webOrigin = process.env.WEB_ORIGIN ?? "http://localhost:5173";
const googleConfigured = Boolean(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET);

await app.register(cors, {
  origin: (origin, callback) => {
    if (!origin || origin === webOrigin || (process.env.NODE_ENV !== "production" && /^http:\/\/localhost:\d+$/.test(origin))) {
      callback(null, true);
      return;
    }
    callback(new Error("Origin is not allowed by CORS"), false);
  },
  credentials: true,
});
await app.register(cookie);
if (googleConfigured) {
  await app.register(oauthPlugin as never, {
    name: "googleOAuth2",
    scope: ["openid", "profile", "email"],
    credentials: { client: { id: process.env.GOOGLE_CLIENT_ID, secret: process.env.GOOGLE_CLIENT_SECRET }, auth: { authorizeHost: "https://accounts.google.com", authorizePath: "/o/oauth2/v2/auth", tokenHost: "https://oauth2.googleapis.com", tokenPath: "/token" } },
    startRedirectPath: "/auth/google",
    callbackUri: process.env.GOOGLE_CALLBACK_URL ?? "http://localhost:3001/auth/google/callback",
  });
}

type UserRow = { id: string; email: string; display_name: string; avatar_url: string | null; created_at: Date; providers: string[] };
const mapUser = (row: UserRow): User => ({ id: row.id, email: row.email, displayName: row.display_name, avatarUrl: row.avatar_url, providers: row.providers as User["providers"], createdAt: row.created_at.toISOString() });
async function loadUser(id: string) {
  const { rows } = await db.query<UserRow>(`SELECT u.id, u.email, u.display_name, u.avatar_url, u.created_at, COALESCE(array_agg(DISTINCT oa.provider) FILTER (WHERE oa.provider IS NOT NULL), ARRAY[]::text[]) providers FROM users u LEFT JOIN oauth_accounts oa ON oa.user_id = u.id WHERE u.id = $1 GROUP BY u.id`, [id]);
  return rows[0] ? mapUser(rows[0]) : null;
}
function setSession(reply: FastifyReply, token: string) { reply.setCookie("maic_session", token, { httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production", path: "/", maxAge: 60 * 60 * 24 * 7 }); }

app.get("/health", async () => ({ ok: true }));
if (!googleConfigured) {
  app.get("/auth/google", async (_request, reply) => reply.code(503).send({ message: "Google 登录尚未配置。请在 apps/api/.env 填写 GOOGLE_CLIENT_ID 和 GOOGLE_CLIENT_SECRET 后重启 API。" }));
}
app.post<{ Body: unknown }>("/auth/register", async (request, reply) => {
  const input = registerSchema.parse(request.body);
  const existing = await db.query("SELECT 1 FROM users WHERE email = $1", [input.email.toLowerCase()]);
  if (existing.rowCount) return reply.code(409).send({ message: "该邮箱已注册" });
  const passwordHash = await bcrypt.hash(input.password, 12);
  const { rows } = await db.query<{ id: string }>("INSERT INTO users (email, display_name, password_hash) VALUES ($1, $2, $3) RETURNING id", [input.email.toLowerCase(), input.displayName, passwordHash]);
  const user = await loadUser(rows[0].id);
  if (!user) throw new Error("Newly created user could not be loaded");
  const token = await issueSession(user); setSession(reply, token); return { user } satisfies AuthResponse;
});
app.post<{ Body: unknown }>("/auth/login", async (request, reply) => {
  const input = loginSchema.parse(request.body);
  const { rows } = await db.query<{ id: string; password_hash: string | null }>("SELECT id, password_hash FROM users WHERE email = $1", [input.email.toLowerCase()]);
  if (!rows[0]) return reply.code(404).send({ message: "该账号尚未注册，请先注册" });
  if (!rows[0].password_hash || !(await bcrypt.compare(input.password, rows[0].password_hash))) return reply.code(401).send({ message: "邮箱或密码不正确" });
  const user = await loadUser(rows[0].id); if (!user) throw new Error("User could not be loaded"); const token = await issueSession(user); setSession(reply, token); return { user } satisfies AuthResponse;
});
app.get("/auth/me", async (request, reply) => { const session = await readSession(request.cookies.maic_session); const user = session?.payload.sub ? await loadUser(session.payload.sub) : null; return user ? { user } : reply.code(401).send({ message: "未登录" }); });
app.post("/auth/logout", async (_request, reply) => { reply.clearCookie("maic_session", { path: "/" }); return reply.code(204).send(); });
app.get("/auth/google/callback", async (request, reply) => {
  if (!("googleOAuth2" in app)) return reply.code(503).send({ message: "Google 登录尚未配置" });
  const googleClient = app as typeof app & { googleOAuth2: { getAccessTokenFromAuthorizationCode: (request: unknown) => Promise<{ token: { id_token?: string } }> } };
  const token = await googleClient.googleOAuth2.getAccessTokenFromAuthorizationCode(request);
  if (!token.token.id_token) return reply.code(401).send({ message: "Google 未返回身份令牌" });
  const profile = JSON.parse(Buffer.from(token.token.id_token.split(".")[1], "base64url").toString()) as { sub: string; email: string; name?: string; picture?: string };
  if (!profile.sub || !profile.email) return reply.code(401).send({ message: "Google 身份信息不完整" });
  const client = await db.connect();
  try { await client.query("BEGIN"); const account = await client.query<{ user_id: string }>("SELECT user_id FROM oauth_accounts WHERE provider = 'google' AND provider_account_id = $1", [profile.sub]); let userId = account.rows[0]?.user_id;
    if (!userId) { const existing = await client.query<{ id: string }>("SELECT id FROM users WHERE email = $1", [profile.email.toLowerCase()]); userId = existing.rows[0]?.id; if (!userId) { const inserted = await client.query<{ id: string }>("INSERT INTO users (email, display_name, avatar_url) VALUES ($1, $2, $3) RETURNING id", [profile.email.toLowerCase(), profile.name ?? profile.email.split("@")[0], profile.picture ?? null]); userId = inserted.rows[0].id; } await client.query("INSERT INTO oauth_accounts (user_id, provider, provider_account_id) VALUES ($1, 'google', $2)", [userId, profile.sub]); }
    await client.query("UPDATE users SET display_name = COALESCE($2, display_name), avatar_url = COALESCE($3, avatar_url), updated_at = now() WHERE id = $1", [userId, profile.name, profile.picture]); await client.query("COMMIT");
    const user = await loadUser(userId!); setSession(reply, await issueSession(user!)); return reply.redirect(`${webOrigin}/chat`);
  } catch (error) { await client.query("ROLLBACK"); throw error; } finally { client.release(); }
});
app.get("/workshop-slots", async () => (await db.query("SELECT * FROM workshop_slots WHERE starts_at > now() AND remaining_seats > 0 ORDER BY starts_at")).rows);
app.post<{ Body: unknown }>("/workshop-bookings", async (request, reply) => { const input = workshopBookingSchema.parse(request.body); const { rows } = await db.query("INSERT INTO workshop_bookings (slot_id, name, organization, contact, attendee_count, topic, note) VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING id", [input.slotId, input.name, input.organization ?? null, input.contact, input.attendeeCount, input.topic, input.note ?? null]); return reply.code(201).send({ id: rows[0].id }); });
app.setErrorHandler((error, _request, reply) => { if (typeof error === "object" && error !== null && "issues" in error) return reply.code(400).send({ message: "请求数据无效", issues: (error as { issues: unknown }).issues }); app.log.error(error); return reply.code(500).send({ message: "服务器错误" }); });
await app.listen({ port: 3001, host: "0.0.0.0" });