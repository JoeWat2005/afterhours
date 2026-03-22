import type { PropsWithChildren } from "react";

import { ClerkProvider, useAuth } from "@clerk/expo";
import { tokenCache } from "@clerk/expo/token-cache";
import { ConvexProvider, ConvexReactClient } from "convex/react";
import { ConvexProviderWithClerk } from "convex/react-clerk";

import { env } from "../lib/env";
import { UiPreferencesProvider } from "./UIPreferences";

const convexClient = env.convexUrl ? new ConvexReactClient(env.convexUrl) : null;

export function AppProviders({ children }: PropsWithChildren) {
  let content = children;

  if (env.clerkPublishableKey && convexClient) {
    content = (
      <ClerkProvider publishableKey={env.clerkPublishableKey} tokenCache={tokenCache}>
        <ConvexProviderWithClerk client={convexClient} useAuth={useAuth}>
          {children}
        </ConvexProviderWithClerk>
      </ClerkProvider>
    );
  } else if (env.clerkPublishableKey) {
    content = (
      <ClerkProvider publishableKey={env.clerkPublishableKey} tokenCache={tokenCache}>
        {children}
      </ClerkProvider>
    );
  } else if (convexClient) {
    content = <ConvexProvider client={convexClient}>{children}</ConvexProvider>;
  }

  return <UiPreferencesProvider>{content}</UiPreferencesProvider>;
}