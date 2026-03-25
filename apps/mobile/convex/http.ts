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
        clerkId: id, //what if id doubled?
        email: email_addresses[0]?.email_address ?? "",
        name: `${first_name ?? ""} ${last_name ?? ""}`.trim() || "User unknown", //user unkown is for missing names
      });
    } else {
      console.log("Unhanled event:", payload.type); //stops from always 200
    }

    return new Response(null, { status: 200 }); //this only ever returns HTTP 200
  }),
});

export default http;
