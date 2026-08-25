import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("请输入有效的邮箱地址"),
  password: z.string().min(8, "密码至少需要 8 位"),
});

export const registerSchema = loginSchema.extend({
  displayName: z.string().trim().min(2, "显示名称至少需要 2 个字符").max(80),
});

export const workshopBookingSchema = z.object({
  name: z.string().trim().min(2),
  organization: z.string().trim().max(120).optional(),
  contact: z.string().trim().min(3).max(120),
  attendeeCount: z.coerce.number().int().min(1).max(50),
  slotId: z.string().uuid(),
  topic: z.string().trim().min(2).max(160),
  note: z.string().trim().max(2_000).optional(),
});