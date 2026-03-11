export const MOBILE_FEATURE_MODULES = [
  "React Native shell",
  "TypeScript features",
  "Mapbox route canvas",
  "NativeWind styling",
  "Clerk auth session",
  "Convex realtime sync"
] as const;

export const SAFETY_PIPELINE_STEPS = [
  "Capture location intent and route filters in the mobile client.",
  "Sync live journey state and optimistic updates through Convex.",
  "Issue Clerk auth claims for API access.",
  "Score route candidates in the FastAPI orchestration layer.",
  "Persist reports, heatmaps and notifications via worker jobs."
] as const;

export const MOBILITY_FILTERS = [
  "well lit",
  "step free",
  "night bus nearby",
  "avoid isolated parks",
  "camera coverage"
] as const;

export type MobilityFilter = (typeof MOBILITY_FILTERS)[number];

