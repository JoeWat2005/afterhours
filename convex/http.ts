import { httpRouter } from "convex/server";
import { httpAction } from "./_generated/server";
import { api } from "./_generated/api";

const http = httpRouter();

http.route({
  path: "/clerk-webhook",
  method: "POST",
  handler: httpAction(async (ctx, req) => {
    const payload = await req.json();

    if (payload.type === "user.created") {
      const { id, email_addresses, first_name, last_name } = payload.data;

      await ctx.runMutation(api.users.createUser, {
        clerkId: id,
        email: email_addresses[0]?.email_address ?? "",
        name: `${first_name ?? ""} ${last_name ?? ""}`.trim(),
      });
    }

    return new Response(null, { status: 200 });
  }),
});

export default http;

