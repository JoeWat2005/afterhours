import { env } from "./env";

export type TokenGetter = () => Promise<string | null>;

export class ApiError extends Error {
  status: number;
  details: unknown;

  constructor(message: string, status: number, details: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

type QueryValue = string | number | boolean | null | undefined;

type RequestOptions = Omit<RequestInit, "body" | "headers"> & {
  body?: unknown;
  headers?: Record<string, string | undefined>;
  query?: Record<string, QueryValue>;
  requireAuth?: boolean;
};

function ensureApiBaseUrl() {
  if (!env.apiBaseUrl) {
    throw new Error("Missing EXPO_PUBLIC_API_BASE_URL");
  }
  return env.apiBaseUrl.replace(/\/+$/, "");
}

function buildPath(path: string) {
  if (path.startsWith("/v1/")) return path;
  if (path === "/v1") return path;
  return `/v1${path.startsWith("/") ? path : `/${path}`}`;
}

function buildUrl(path: string, query?: Record<string, QueryValue>) {
  const base = ensureApiBaseUrl();
  const url = new URL(`${base}${buildPath(path)}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === null) continue;
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function getAuthHeaders(
  getToken: TokenGetter,
  requireAuth: boolean,
) {
  if (!requireAuth) {
    return {};
  }
  const token = await getToken();
  if (!token) {
    throw new Error("Missing Clerk auth token");
  }
  return { Authorization: `Bearer ${token}` };
}

async function parseErrorPayload(response: Response) {
  try {
    return await response.json();
  } catch {
    try {
      return await response.text();
    } catch {
      return null;
    }
  }
}

async function parseResponseBody<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T;
  }
  const text = await response.text();
  if (!text) {
    return undefined as T;
  }
  try {
    return JSON.parse(text) as T;
  } catch {
    return text as T;
  }
}

export async function apiRequest<T>(
  path: string,
  getToken: TokenGetter,
  options: RequestOptions = {},
): Promise<T> {
  const {
    body,
    headers,
    query,
    requireAuth = true,
    method = "GET",
    ...rest
  } = options;

  const authHeaders = await getAuthHeaders(getToken, requireAuth);
  const requestHeaders = new Headers();
  requestHeaders.set("Content-Type", "application/json");
  for (const [key, value] of Object.entries(authHeaders)) {
    if (value) {
      requestHeaders.set(key, value);
    }
  }
  if (headers) {
    for (const [key, value] of Object.entries(headers)) {
      if (value !== undefined) {
        requestHeaders.set(key, value);
      }
    }
  }

  const response = await fetch(buildUrl(path, query), {
    ...rest,
    method,
    headers: requestHeaders,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!response.ok) {
    const details = await parseErrorPayload(response);
    const message =
      typeof details === "object" &&
      details &&
      "detail" in details &&
      typeof (details as { detail?: unknown }).detail === "string"
        ? (details as { detail: string }).detail
        : `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status, details);
  }

  return parseResponseBody<T>(response);
}

export type GeocodeResult = {
  label: string;
  latitude: number;
  longitude: number;
};

export async function geocodePlace(
  query: string,
  options?: {
    proximity?: { latitude: number; longitude: number };
    limit?: number;
    country?: string;
  },
): Promise<GeocodeResult[]> {
  const token = env.mapboxAccessToken;
  if (!token) return [];
  const cleaned = query.trim();
  if (!cleaned) return [];

  const encoded = encodeURIComponent(cleaned);
  const url = new URL(
    `https://api.mapbox.com/geocoding/v5/mapbox.places/${encoded}.json`,
  );
  url.searchParams.set("access_token", token);
  url.searchParams.set("autocomplete", "true");
  url.searchParams.set("limit", String(options?.limit ?? 5));
  url.searchParams.set("country", options?.country ?? "gb");
  if (options?.proximity) {
    url.searchParams.set(
      "proximity",
      `${options.proximity.longitude},${options.proximity.latitude}`,
    );
  }

  const response = await fetch(url.toString());
  if (!response.ok) return [];

  const payload = await response.json();
  return (payload.features ?? []).map((feature: any) => ({
    label: feature.place_name ?? cleaned,
    latitude: feature.center[1],
    longitude: feature.center[0],
  }));
}

export function formatDistanceMetres(metres: number) {
  if (!Number.isFinite(metres)) return "-";
  if (metres < 1000) return `${Math.round(metres)} m`;
  return `${(metres / 1000).toFixed(1)} km`;
}

export type Coordinates = {
  latitude: number;
  longitude: number;
  label?: string | null;
};

export type RouteNavigationStep = {
  step_index: number;
  distance_metres: number;
  duration_seconds: number;
  instruction: string | null;
  street_name: string | null;
  maneuver_type: string | null;
  maneuver_modifier: string | null;
  maneuver_location: Coordinates | null;
  geometry_geojson: GeoJSONGeometry | null;
};

export type RouteNavigationMetadata = {
  provider: string | null;
  steps: RouteNavigationStep[];
};

export type GeoJSONPosition = [number, number];
export type GeoJSONLineString = {
  type: "LineString";
  coordinates: GeoJSONPosition[];
};
export type GeoJSONMultiLineString = {
  type: "MultiLineString";
  coordinates: GeoJSONPosition[][];
};
export type GeoJSONGeometry = GeoJSONLineString | GeoJSONMultiLineString;

export type RankedRoute = {
  candidate_id: string;
  label: string | null;
  provider: string | null;
  rank: number;
  meets_requirements: boolean;
  unmet_requirements: string[];
  is_fallback: boolean;
  score: number;
  distance_metres: number;
  duration_seconds: number;
  geometry_geojson: GeoJSONGeometry | null;
  navigation: RouteNavigationMetadata | null;
  explanation: {
    summary: string;
    reasons: string[];
    warnings: string[];
  };
};

export type RouteAccessibilityChoices = {
  avoid_stairs: boolean;
  step_free_access: boolean;
  lifts_available: boolean;
  ramps_available: boolean;
  escalators_available: boolean;
};

export type RouteWaitingAreaChoices = {
  safe_waiting_areas: boolean;
  well_lit_waiting_areas: boolean;
  wifi_nearby: boolean;
  staffed_venues_nearby: boolean;
  open_venues_nearby: boolean;
  safe_areas_nearby: boolean;
};

export type RouteRequirements = {
  accessibility: RouteAccessibilityChoices;
  waiting_areas: RouteWaitingAreaChoices;
};

export type RoutePreferences = {
  accessibility: RouteAccessibilityChoices;
  waiting_areas: RouteWaitingAreaChoices;
};

export type RouteBiasMode =
  | "maximum_safety"
  | "balanced"
  | "most_efficiency";

export type RoutePlanRequest = {
  origin: Coordinates;
  destination: Coordinates;
  depart_at: string;
  bias_mode?: RouteBiasMode;
  requirements?: RouteRequirements;
  preferences?: RoutePreferences;
  alternatives: number;
};

export type RoutePlanResponse = {
  selected_route_id: string;
  ranked_routes: RankedRoute[];
  warnings: string[];
};

export type JourneyResponse = {
  id: string;
  user_id: string | null;
  origin_label: string;
  destination_label: string;
  score: number;
  route_geojson: GeoJSONGeometry;
  created_at: string;
};

export type CanonicalReportCategory =
  | "assault"
  | "robbery"
  | "harassment"
  | "theft"
  | "suspicious activity"
  | "poor lighting"
  | "unsafe crossing"
  | "hazard"
  | "other";

export type SafetyReportResponse = {
  id: string;
  user_id: string | null;
  category: CanonicalReportCategory;
  summary: string;
  details: string;
  latitude: number;
  longitude: number;
  created_at: string;
};

export type NearbyReportsResponse = {
  items: SafetyReportResponse[];
};

export type ServiceCategory =
  | "hospital"
  | "police"
  | "fire_station"
  | "ambulance";

export type NearbyService = {
  id: string;
  name: string;
  category: ServiceCategory;
  address: string | null;
  latitude: number;
  longitude: number;
  distance_metres: number;
  source: string;
};

export type NearbyServicesResponse = {
  items: NearbyService[];
};

export type HeatmapCellBounds = {
  min_latitude: number;
  min_longitude: number;
  max_latitude: number;
  max_longitude: number;
};

export type HeatmapCell = {
  cell_id: string;
  center_latitude: number;
  center_longitude: number;
  risk_score: number;
  source_count: number;
  bounds: HeatmapCellBounds;
};

export type CrimePin = {
  crime_id: string;
  category: string;
  month: string;
  latitude: number;
  longitude: number;
  location_label: string | null;
};

export type HeatmapResponse = {
  latitude: number;
  longitude: number;
  radius_metres: number;
  cell_size_metres: number;
  category: string;
  date: string | null;
  items: HeatmapCell[];
  crime_pins: CrimePin[];
};

export type AutocompleteResult = {
  placeId: string;
  description: string;
};

// hits google places autocomplete, returns top 5 suggestions
export async function placesAutocomplete(
  input: string,
  options?: {
    proximity?: { latitude: number; longitude: number };
    country?: string;
  },
): Promise<AutocompleteResult[]> {
  const key = env.googleMapsApiKey;
  if (!key) return [];
  const cleaned = input.trim();
  if (!cleaned) return [];

  const url = new URL("https://maps.googleapis.com/maps/api/place/autocomplete/json");
  url.searchParams.set("input", cleaned);
  url.searchParams.set("key", key);
  url.searchParams.set("components", `country:${options?.country ?? "gb"}`);
  if (options?.proximity) {
    url.searchParams.set(
      "location",
      `${options.proximity.latitude},${options.proximity.longitude}`,
    );
    url.searchParams.set("radius", "50000");
  }

  const response = await fetch(url.toString());
  if (!response.ok) return [];

  const payload = await response.json();
  return (payload.predictions ?? []).slice(0, 5).map((p: any) => ({
    placeId: p.place_id,
    description: p.description,
  }));
}

// reverse geocode coords to a place name via mapbox
export async function reverseGeocode(
  latitude: number,
  longitude: number,
): Promise<string> {
  const token = env.mapboxAccessToken;
  if (!token) return "Unknown area";

  const url = new URL(
    `https://api.mapbox.com/geocoding/v5/mapbox.places/${longitude},${latitude}.json`,
  );
  url.searchParams.set("access_token", token);
  url.searchParams.set("types", "neighborhood,locality,place");
  url.searchParams.set("limit", "1");

  try {
    const response = await fetch(url.toString());
    if (!response.ok) return "Unknown area";
    const payload = await response.json();
    const feature = payload.features?.[0];
    if (!feature) return "Unknown area";
    return feature.text ?? feature.place_name ?? "Unknown area";
  } catch {
    return "Unknown area";
  }
}

export const BIRMINGHAM_DEFAULT_CENTER: Coordinates = {
  latitude: 52.4862,
  longitude: -1.8904,
  label: "Birmingham",
};

export function logPrototypeEvent(event: string, details?: unknown) {
  if (details === undefined) {
    console.log(`[afterhours] ${event}`);
    return;
  }
  console.log(`[afterhours] ${event}`, details);
}
