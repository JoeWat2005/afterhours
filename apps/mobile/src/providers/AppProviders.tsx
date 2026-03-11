import type { PropsWithChildren } from "react";

import { ClerkProvider, useAuth } from "@clerk/expo";
import { ConvexProvider, ConvexReactClient } from "convex/react";
import { ConvexProviderWithClerk } from "convex/react-clerk";

import { env } from "../lib/env";
import { tokenCache } from "../lib/clerk-token-cache";

const convexClient = env.convexUrl ? new ConvexReactClient(env.convexUrl) : null;

export function AppProviders({ children }: PropsWithChildren) {
  if (!env.clerkPublishableKey && !convexClient) {
    return <>{children}</>;
  }

  if (env.clerkPublishableKey && convexClient) {
    return (
      <ClerkProvider publishableKey={env.clerkPublishableKey} tokenCache={tokenCache}>
        <ConvexProviderWithClerk client={convexClient} useAuth={useAuth}>
          {children}
        </ConvexProviderWithClerk>
      </ClerkProvider>
    );
  }

  if (env.clerkPublishableKey) {
    return (
      <ClerkProvider publishableKey={env.clerkPublishableKey} tokenCache={tokenCache}>
        {children}
      </ClerkProvider>
    );
  }

  return <ConvexProvider client={convexClient!}>{children}</ConvexProvider>;
}
