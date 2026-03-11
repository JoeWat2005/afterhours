import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  journeys: defineTable({
    createdAt: v.number(),
    status: v.string()
  }).index("by_created_at", ["createdAt"]),
  safetyReports: defineTable({
    createdAt: v.number(),
    status: v.string()
  }).index("by_created_at", ["createdAt"])
});
