import type { PropsWithChildren } from "react";

import { useAuth } from "@clerk/expo";
import { ConvexProvider, ConvexReactClient } from "convex/react";
import { ConvexProviderWithClerk } from "convex/react-clerk";

import { RouteSessionProvider } from "../features/route/routeSession";
import { env } from "../lib/env";
import { UiPreferencesProvider } from "./UIPreferences";

const convexClient = env.convexUrl
  ? new ConvexReactClient(env.convexUrl)
  : null;

export function AppProviders({ children }: PropsWithChildren) {
  let content = children;

  if (convexClient) {
    content = (
      <ConvexProviderWithClerk client={convexClient} useAuth={useAuth}>
        {children}
      </ConvexProviderWithClerk>
    );
  }

  if (!env.clerkPublishableKey && convexClient) {
    content = <ConvexProvider client={convexClient}>{children}</ConvexProvider>;
  }

  return (
    <UiPreferencesProvider>
      <RouteSessionProvider>{content}</RouteSessionProvider>
    </UiPreferencesProvider>
  );
}
