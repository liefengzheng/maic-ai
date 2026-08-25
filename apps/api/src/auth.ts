import type { User } from "@maic/types";
import { SignJWT, jwtVerify } from "jose";

const secret = new TextEncoder().encode(process.env.JWT_SECRET ?? "development-only-secret-change-me-now");

export async function issueSession(user: User) {
  return new SignJWT({ email: user.email, name: user.displayName })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(user.id)
    .setIssuedAt()
    .setExpirationTime("7d")
    .sign(secret);
}

export async function readSession(token?: string) {
  if (!token) return null;
  try { return await jwtVerify(token, secret); } catch { return null; }
}