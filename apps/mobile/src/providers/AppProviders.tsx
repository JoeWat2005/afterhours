import type { PropsWithChildren } from "react";

import { ClerkProvider, useAuth } from "@clerk/expo";
import { ConvexProvider, ConvexReactClient } from "convex/react";
import { ConvexProviderWithClerk } from "convex/react-clerk";

import { tokenCache } from "../lib/clerk-token-cache";
import { env } from "../lib/env";
import { UiPreferencesProvider } from "./UIPreferences";

const convexClient = env.convexUrl ? new ConvexReactClient(env.convexUrl) : null;

export function AppProviders({ children }: PropsWithChildren) {
  const content = (() => {
    if (!env.clerkPublishableKey && !convexClient) {
      return children;
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
  })();

  return <UiPreferencesProvider>{content}</UiPreferencesProvider>;
}