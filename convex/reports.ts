import { mutation, query } from "./_generated/server";

export const listReports = query({
  args: {},
  handler: async (ctx) => {
    return ctx.db.query("safetyReports").order("desc").take(25);
  }
});

export const createReport = mutation({
  args: {},
  handler: async (ctx) => {
    return ctx.db.insert("safetyReports", {
      createdAt: Date.now(),
      status: "pending-review"
    });
  }
});

