type OptionalString = string | undefined;

function readEnv(name: string): OptionalString {
  const value = process.env[name];
  return value && value.length > 0 ? value : undefined;
}

export const env = {
  apiBaseUrl: readEnv("EXPO_PUBLIC_API_BASE_URL"),
  clerkPublishableKey: readEnv("EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY"),
  convexUrl: readEnv("EXPO_PUBLIC_CONVEX_URL"),
  mapboxAccessToken: readEnv("EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN")
};
