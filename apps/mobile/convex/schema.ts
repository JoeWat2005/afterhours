import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  journeys: defineTable({
    userId: v.string(),
    start: v.string(),
    destination: v.string(),
    createdAt: v.number(),
    status: v.string()
  })
    .index("by_user", ["userId"])
    .index("by_created_at", ["createdAt"]),

  safetyReports: defineTable({
    userId: v.string(),
    apiReportId: v.optional(v.string()),
    latitude: v.optional(v.number()),
    longitude: v.optional(v.number()),
    location: v.string(),
    description: v.optional(v.string()),
    category: v.string(),
    createdAt: v.number(),
    status: v.string()
  })
    .index("by_created_at", ["createdAt"])
    .index("by_api_report_id", ["apiReportId"]),

  users: defineTable({
    name: v.string(),
    email: v.string(),
    clerkId: v.string(),
  }).index("by_clerk_id", ["clerkId"]),
});
