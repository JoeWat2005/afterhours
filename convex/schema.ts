import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  journeys: defineTable({
    userId: v.string(),
    start: v.string(),
    destination: v.string(),
    createdAt: v.number(),
    status: v.string()
  }).index("by_user", ["userId"]).index("by_created_at", ["createdAt"]),

  safetyReports: defineTable({
    userId: v.string(),
    location: v.string(),
    description: v.optional(v.string()),
    category: v.string(),
    createdAt: v.number(),
    status: v.string()
  }).index("by_created_at", ["createdAt"]),
});
