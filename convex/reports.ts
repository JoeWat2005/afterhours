import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

async function getAuth(ctx: any) {
  const identity = await ctx.auth.getUserIdentity();
  if (!identity) throw new Error("Unauthenticated");
  return identity;
}

export const listReports = query({
  args: {},
  handler: async (ctx) => {
    await getAuth (ctx);
    return ctx.db.query("safetyReports").order("desc").take(25);
  }
});

export const createReport = mutation({
  args: {
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
    const identity = await getAuth(ctx);

    return ctx.db.insert("safetyReports", {
      userId: identity.subject,
      location: args.location,
      category: args.category,
      description: args.description,
      createdAt: Date.now(),
      status: "pending-review"
    });
  }
});

