import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

async function getAuth(ctx: { auth: { getUserIdentity: () => Promise<unknown> } }) {
  const identity = await ctx.auth.getUserIdentity();
  if (!identity) throw new Error("Unauthenticated");
  return identity as { subject: string };
}

export const createUser = mutation({
  args: {
    clerkId: v.string(),
    name: v.string(),
    email: v.string(),
  },

  handler: async (ctx, args) => {
    const exist = await ctx.db
      .query("users")
      .withIndex("by_clerk_id", (q) => q.eq("clerkId", args.clerkId))
      .first();

    if (exist) return exist._id;

    return ctx.db.insert("users", {
      clerkId: args.clerkId,
      name: args.name,
      email: args.email,
    });
  },
});

export const getUser = query({
  args: {},
  handler: async (ctx) => {
    const identity = await getAuth(ctx);

    return ctx.db
      .query("users")
      .withIndex("by_clerk_id", (q) => q.eq("clerkId", identity.subject))
      .first();
  },
});
