import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

async function getAuth(ctx: any) {
  const identity = await ctx.auth.getUserIdentity();
  if (!identity) throw new Error("Unauthenticated");
  return identity;
};

export const listRecentJourneys = query({
  args: {},
  handler: async (ctx) => {
    const identity = await getAuth(ctx);

    return await ctx.db.query("journeys").withIndex("by_user", (q: any) => q.eq("userId", identity.subject)).order("desc").take(10);
  }
});

export const createJourney = mutation({ 
  args: {
    start: v.string(),
    destination: v.string()
  },

  handler: async (ctx, args) => {
    const identity = await getAuth(ctx);

    
    return ctx.db.insert("journeys", {
      userId: identity.subject,
      start: args.start,
      destination: args.destination,
      createdAt: Date.now(),
      status: "draft"
    })
  }
})

export const editJourney = mutation({
    args: {
      journeyId: v.id("journeys"),
      start: v.optional(v.string()),
      destination: v.optional(v.string())
    },

    handler: async (ctx, args) => {
      const identity = await getAuth(ctx);
      const journey = await ctx.db.get(args.journeyId);
      if (!journey) throw new Error("Journey not found");
      if (journey.userId !== identity.subject) throw new Error("Unauthenticated");

      const { journeyId, ...fields} = args;
      await ctx.db.patch(journeyId, fields);
    }
});



