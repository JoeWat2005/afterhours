import { mutation, query } from "./_generated/server";

export const listRecentJourneys = query({
  args: {},
  handler: async (ctx) => {
    return ctx.db.query("journeys").order("desc").take(10);
  }
});

export const createJourneyDraft = mutation({
  args: {},
  handler: async (ctx) => {
    return ctx.db.insert("journeys", {
      createdAt: Date.now(),
      status: "draft"
    });
  }
});

