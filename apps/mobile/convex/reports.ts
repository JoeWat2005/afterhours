import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

async function getOptionalIdentity(ctx: any) {
  return await ctx.auth.getUserIdentity();
}

export const listReports = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db.query("safetyReports").order("desc").take(25);
  }
});

export const createReport = mutation({
  args: {
    apiReportId: v.optional(v.string()),
    latitude: v.optional(v.number()),
    longitude: v.optional(v.number()),
    location: v.string(),
    description: v.string(),
    category: v.union(
      v.literal("crime"),
      v.literal("lighting"),
      v.literal("unpaved"),
      v.literal("sketchy"),
      v.literal("other")
    ),
  },

  handler: async (ctx, args) => {
    const identity = await getOptionalIdentity(ctx);

    return ctx.db.insert("safetyReports", {
      userId: identity?.subject ?? "anonymous",
      apiReportId: args.apiReportId,
      latitude: args.latitude,
      longitude: args.longitude,
      location: args.location,
      category: args.category,
      description: args.description,
      createdAt: Date.now(),
      status: "pending-review"
    });
  }
});

export const upsertReportFromApi = mutation({
  args: {
    apiReportId: v.string(),
    latitude: v.number(),
    longitude: v.number(),
    location: v.string(),
    description: v.string(),
    category: v.union(
      v.literal("crime"),
      v.literal("lighting"),
      v.literal("unpaved"),
      v.literal("sketchy"),
      v.literal("other")
    ),
    createdAt: v.optional(v.number()),
    status: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const identity = await getOptionalIdentity(ctx);
    const existing = await ctx.db
      .query("safetyReports")
      .withIndex("by_api_report_id", (q) => q.eq("apiReportId", args.apiReportId))
      .first();

    if (existing) {
      await ctx.db.patch(existing._id, {
        latitude: args.latitude,
        longitude: args.longitude,
        location: args.location,
        description: args.description,
        category: args.category,
        createdAt: args.createdAt ?? existing.createdAt,
        status: args.status ?? existing.status,
      });
      return existing._id;
    }

    return await ctx.db.insert("safetyReports", {
      userId: identity?.subject ?? "api-sync",
      apiReportId: args.apiReportId,
      latitude: args.latitude,
      longitude: args.longitude,
      location: args.location,
      description: args.description,
      category: args.category,
      createdAt: args.createdAt ?? Date.now(),
      status: args.status ?? "synced",
    });
  },
});
