import React, { useEffect, useMemo, useRef, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Switch, Text, TextInput, View } from "react-native";
import Animated, {
  FadeIn,
  FadeOut,
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withTiming,
} from "react-native-reanimated";
import { Ionicons } from "@expo/vector-icons";
import { Link } from "expo-router";
import { useAuth } from "@clerk/expo";
import { useIsFocused } from "@react-navigation/native";
import { useMutation, useQuery } from "convex/react";
import * as Location from "expo-location";
import Mapbox from "@rnmapbox/maps";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "../../convex/_generated/api";
import { mapCanonicalToConvexCategory, mapUiIssueToCategories } from "../../src/features/reports/categories";
import {
  BIRMINGHAM_DEFAULT_CENTER,
  apiRequest,
  formatDistanceMetres,
  logPrototypeEvent,
  geocodePlace,
  reverseGeocode,
  type GeocodeResult,
  type Coordinates,
  type HeatmapResponse,
  type NearbyReportsResponse,
  type RoutePlanResponse,
  type RoutePlanRequest,
  type SafetyReportResponse,
  type NearbyServicesResponse,
  type NearbyService,
  type RouteOverlayItem,
  type RouteOverlaysResponse,
  type ServiceCategory,
} from "../../src/lib/api";
import {
  computeRouteProgress,
  flattenGeometryCoordinates,
} from "../../src/features/route/progress";
import { useRouteSession } from "../../src/features/route/routeSession";
import { useConvexTokenAvailability } from "../../src/lib/convexAuth";
import {
  useUiPreferences,
  type RouteAccessibilityChoices,
  type RouteWaitingAreaChoices,
} from "../../src/providers/UIPreferences";
import { env } from "../../src/lib/env";
import { useDemoMode } from "../../src/lib/demoMode";

Mapbox.setAccessToken(process.env.EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN ?? "");

const DEFAULT_CENTER: [number, number] = [
  BIRMINGHAM_DEFAULT_CENTER.longitude,
  BIRMINGHAM_DEFAULT_CENTER.latitude,
];
const OFF_ROUTE_THRESHOLD_METRES = 45;
const OFF_ROUTE_SAMPLE_LIMIT = 3;
const HEATMAP_RADIUS_METRES = 2500;
const HEATMAP_CELL_SIZE_METRES = 180;

const SERVICE_CATEGORIES: { label: string; value: ServiceCategory | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Hospital", value: "hospital" },
  { label: "Police", value: "police" },
  { label: "Fire", value: "fire_station" },
  { label: "Ambulance", value: "ambulance" },
];

const SERVICE_ICONS: Record<string, string> = {
  hospital: "medkit",
  police: "shield-checkmark",
  fire_station: "flame",
  ambulance: "car",
};

const ISSUE_OPTIONS = [
  "Crime",
  "Break-in / Burglary",
  "Harassment",
  "Unsafe Area",
  "Poor Lighting",
  "Road Hazard / Potholes",
  "Anti-social Behaviour",
  "Other",
];

type PermissionState = "idle" | "granted" | "denied";

function buildRoutePlanningToggles(
  routeOptions: NonNullable<RoutePlanRequest["requirements"]>,
): Pick<RoutePlanRequest, "requirements" | "preferences"> {
  return {
    requirements: {
      accessibility: { ...routeOptions.accessibility },
      waiting_areas: { ...routeOptions.waiting_areas },
    },
    preferences: {
      accessibility: { ...routeOptions.accessibility },
      waiting_areas: { ...routeOptions.waiting_areas },
    },
  };
}

export default function HomeScreen() {
  const insets = useSafeAreaInsets();
  const isFocused = useIsFocused();
  const {
    highContrast,
    setHighContrast,
    routeOptions,
    setAccessibilityOption,
    setWaitingAreaOption,
    leaveNowAlerts,
    setLeaveNowAlerts,
    lowDataMode,
    setLowDataMode,
  } = useUiPreferences();
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const { demoMode } = useDemoMode();
  const authed = isSignedIn || demoMode;
  const { hasConvexToken, checked: convexTokenChecked } = useConvexTokenAvailability();
  const convexEnabled = Boolean(env.convexUrl);
  const upsertReport = useMutation(api.reports.upsertReportFromApi);
  const createRealtimeReport = useMutation(api.reports.createReport);
  const reports = useQuery(
    api.reports.listReports,
    isLoaded && isSignedIn && convexEnabled && hasConvexToken ? {} : "skip",
  );
  const {
    session,
    mapFocusTarget,
    setMapFocusTarget,
    setWalkStatus,
    clearSession,
    updateProgress,
    incrementOffRouteSamples,
    resetOffRouteSamples,
    replaceActiveRoute,
    setRerouting,
    startSession,
  } = useRouteSession();

  // ref so the progress effect can read session without depending on it
  const sessionRef = useRef(session);
  sessionRef.current = session;

  const [permissionState, setPermissionState] = useState<PermissionState>("idle");
  const [currentLocation, setCurrentLocation] = useState<Coordinates | null>(null);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [syncingReports, setSyncingReports] = useState(false);
  const [syncingHeatmap, setSyncingHeatmap] = useState(false);
  const [apiReports, setApiReports] = useState<NearbyReportsResponse["items"]>([]);
  const [heatmapEnabled, setHeatmapEnabled] = useState(true);
  const [showCrimePins, setShowCrimePins] = useState(false);
  const [showReportPins, setShowReportPins] = useState(true);
  const [heatmapError, setHeatmapError] = useState<string | null>(null);
  const [heatmapData, setHeatmapData] = useState<HeatmapResponse | null>(null);
  const mapCameraRef = useRef<Mapbox.Camera>(null);
  const reportSyncTimerRef = useRef<number | null>(null);
  const heatmapSyncTimerRef = useRef<number | null>(null);
  const locationWatcherRef = useRef<Location.LocationSubscription | null>(null);
  const [areaName, setAreaName] = useState("Locating...");
  const [mapCenter, setMapCenter] = useState<{ latitude: number; longitude: number } | null>(null);
  const [mapZoom, setMapZoom] = useState(14);

  // bottom sheet slide animation
  const sheetTranslate = useSharedValue(0);
  const sheetStyle = useAnimatedStyle(() => ({
    transform: [{ translateY: sheetTranslate.value }],
  }));

  function transitionSheet(callback: () => void) {
    // slide out, swap content while off screen, slide back in
    sheetTranslate.value = withTiming(500, { duration: 200 });
    setTimeout(() => {
      callback();
      sheetTranslate.value = withDelay(200, withTiming(0, { duration: 250 }));
    }, 220);
  }

  // always request both walking and transit, let the scoring decide
  const transportMode = "walking_transit" as const;
  const [searchText, setSearchText] = useState("");
  const [suggestions, setSuggestions] = useState<GeocodeResult[]>([]);
  const searchTimerRef = useRef<number | null>(null);
  const searchInputRef = useRef<TextInput>(null);
  const [routeOverlays, setRouteOverlays] = useState<RouteOverlayItem[]>([]);
  const [routePreview, setRoutePreview] = useState<{
    plan: RoutePlanResponse;
    origin: Coordinates;
    destination: Coordinates;
  } | null>(null);
  const [planningRoute, setPlanningRoute] = useState(false);
  const [planError, setPlanError] = useState<string | null>(null);
  const [startingWalk, setStartingWalk] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const toastTimerRef = useRef<number | null>(null);

  function showToast(msg: string) {
    setToast(msg);
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => setToast(null), 4000) as unknown as number;
  }

  // selected report detail popup
  const [selectedReport, setSelectedReport] = useState<{
    category: string;
    summary: string;
    created_at: string;
    latitude: number;
    longitude: number;
  } | null>(null);

  // report mode
  const [reportMode, setReportMode] = useState(false);
  const [reportIssue, setReportIssue] = useState<string | null>(null);
  const [reportDescription, setReportDescription] = useState("");
  const [reportLocation, setReportLocation] = useState<Coordinates | null>(null);
  const [reportPickingLocation, setReportPickingLocation] = useState(false);
  const [reportSubmitting, setReportSubmitting] = useState(false);

  // services mode
  const [servicesMode, setServicesMode] = useState(false);
  const [serviceCategory, setServiceCategory] = useState<ServiceCategory | "all">("all");
  const [servicesList, setServicesList] = useState<NearbyService[]>([]);
  const [servicesLoading, setServicesLoading] = useState(false);
  const [expandedSettingsGroup, setExpandedSettingsGroup] = useState<"accessibility" | "comfort" | "general" | null>(null);

  // reports list mode
  const [reportsListMode, setReportsListMode] = useState(false);
  const [reportsListItems, setReportsListItems] = useState<SafetyReportResponse[]>([]);
  const [reportsListLoading, setReportsListLoading] = useState(false);

  function openReportsListMode() {
    transitionSheet(() => {
      setReportsListMode(true);
      void loadReportsList();
    });
  }

  function closeReportsListMode() {
    transitionSheet(() => {
      setReportsListMode(false);
      setReportsListItems([]);
    });
  }

  async function loadReportsList() {
    setReportsListLoading(true);
    try {
      const center = mapCenter ?? currentLocation ?? BIRMINGHAM_DEFAULT_CENTER;
      const response = await apiRequest<NearbyReportsResponse>("/reports/nearby", getToken, {
        query: {
          latitude: center.latitude,
          longitude: center.longitude,
          radius_metres: 5000,
          limit: 30,
        },
      });
      setReportsListItems(response.items);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Couldn't load reports";
      showToast(msg);
    } finally {
      setReportsListLoading(false);
    }
  }

  function openServicesMode() {
    transitionSheet(() => {
      setServicesMode(true);
      void loadServices("all");
    });
  }

  function closeServicesMode() {
    transitionSheet(() => {
      setServicesMode(false);
      setServicesList([]);
    });
  }

  async function loadServices(category: ServiceCategory | "all") {
    setServiceCategory(category);
    setServicesLoading(true);
    try {
      const center = mapCenter ?? currentLocation ?? BIRMINGHAM_DEFAULT_CENTER;
      const response = await apiRequest<NearbyServicesResponse>("/services/nearby", getToken, {
        query: {
          latitude: center.latitude,
          longitude: center.longitude,
          category: category === "all" ? undefined : category,
          radius_metres: 8000,
          limit: 20,
        },
      });
      setServicesList(response.items);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Couldn't load services";
      showToast(msg);
    } finally {
      setServicesLoading(false);
    }
  }

  function openReportMode() {
    transitionSheet(() => {
      setReportMode(true);
      setReportIssue(null);
      setReportDescription("");
      setReportLocation(null);
      setReportPickingLocation(false);
    });
  }

  function closeReportMode() {
    transitionSheet(() => {
      setReportMode(false);
      setReportPickingLocation(false);
    });
  }

  function handleMapPress(event: { geometry: { coordinates: [number, number] } }) {
    if (!reportPickingLocation) return;
    const [lng, lat] = event.geometry.coordinates;
    setReportLocation({ latitude: lat, longitude: lng });
    setReportPickingLocation(false);
  }

  async function submitReport() {
    if (reportSubmitting) return;
    if (!reportIssue) {
      showToast("Pick an issue type");
      return;
    }
    if (reportDescription.trim().length < 12) {
      showToast("Description needs to be a bit longer");
      return;
    }

    const coords = reportLocation ?? currentLocation;
    if (!coords) {
      showToast("Still getting your location, try again");
      return;
    }

    setReportSubmitting(true);
    try {
      const mapped = mapUiIssueToCategories(reportIssue);
      const summary = `${reportIssue} near ${areaName}`.slice(0, 280);

      const saved = await apiRequest<SafetyReportResponse>("/reports", getToken, {
        method: "POST",
        body: {
          category: mapped.canonical,
          summary,
          details: reportDescription.trim(),
          latitude: coords.latitude,
          longitude: coords.longitude,
        },
      });

      try {
        await createRealtimeReport({
          apiReportId: saved.id,
          latitude: saved.latitude,
          longitude: saved.longitude,
          category: mapped.convex,
          description: saved.summary,
          location: `${areaName} (${saved.latitude.toFixed(5)}, ${saved.longitude.toFixed(5)})`,
        });
      } catch {
        // convex mirror is optional
      }

      showToast("Report submitted, cheers");
      closeReportMode();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to submit report";
      showToast(msg);
    } finally {
      setReportSubmitting(false);
    }
  }

  const [selectedPreviewId, setSelectedPreviewId] = useState<string | null>(null);

  const previewRoute = routePreview
    ? routePreview.plan.ranked_routes.find(
        (r) => r.candidate_id === (selectedPreviewId ?? routePreview.plan.selected_route_id),
      ) ?? routePreview.plan.ranked_routes[0]
    : null;

  const previewRouteShapes = useMemo(() => {
    if (!routePreview) return [];
    return routePreview.plan.ranked_routes
      .filter((r) => r.geometry_geojson)
      .map((r) => ({
        id: r.candidate_id,
        shape: {
          type: "Feature" as const,
          properties: {},
          geometry: r.geometry_geojson!,
        },
      }));
  }, [routePreview]);

  const selectedStepSegments = useMemo(() => {
    if (!previewRoute?.navigation?.steps) return [];
    return previewRoute.navigation.steps
      .filter((s: any) => s.geometry_geojson)
      .map((s: any) => ({
        id: `step-${s.step_index}`,
        mode: s.mode ?? "walking",
        line: s.line,
        shape: {
          type: "Feature" as const,
          properties: { mode: s.mode ?? "walking" },
          geometry: s.geometry_geojson,
        },
      }));
  }, [previewRoute]);

  function handleSearchChange(text: string) {
    setSearchText(text);
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    if (!text.trim()) {
      setSuggestions([]);
      return;
    }
    searchTimerRef.current = setTimeout(async () => {
      const results = await geocodePlace(text, {
        proximity: currentLocation ?? undefined,
        limit: 5,
      });
      setSuggestions(results);
    }, 400) as unknown as number;
  }

  async function handleSuggestionPress(suggestion: GeocodeResult) {
    setSearchText("");
    setSuggestions([]);
    setPlanError(null);
    if (!currentLocation) {
      setPlanError("Still getting your location, try again");
      return;
    }

    // animate to loading state
    transitionSheet(() => setPlanningRoute(true));

    try {
      const origin: Coordinates = {
        latitude: currentLocation.latitude,
        longitude: currentLocation.longitude,
        label: "Current location",
      };
      const destination: Coordinates = {
        latitude: suggestion.latitude,
        longitude: suggestion.longitude,
        label: suggestion.label,
      };
      const routeToggles = buildRoutePlanningToggles(routeOptions);
      const plan = await apiRequest<RoutePlanResponse>("/routes/plan", getToken, {
        method: "POST",
        requireAuth: false,
        body: {
          origin,
          destination,
          depart_at: new Date().toISOString(),
          transport_mode: transportMode,
          alternatives: lowDataMode ? 1 : 3,
          ...routeToggles,
        },
      });

      // animate to preview state
      transitionSheet(() => {
        setRoutePreview({ plan, origin, destination });
        setSelectedPreviewId(plan.selected_route_id);
        setPlanningRoute(false);
      });

      // fetch overlays along the selected route in the background
      const selectedRoute = plan.ranked_routes.find(r => r.candidate_id === plan.selected_route_id);
      if (selectedRoute?.geometry_geojson) {
        apiRequest<RouteOverlaysResponse>("/routes/overlays", getToken, {
          method: "POST",
          requireAuth: false,
          body: {
            route_geometry_geojson: selectedRoute.geometry_geojson,
            include: ["transit", "reports", "services"],
            near_route_radius_metres: 300,
          },
        }).then(res => {
          logPrototypeEvent("overlays_loaded", { count: res.items.length });
          setRouteOverlays(res.items);
        }).catch(err => {
          logPrototypeEvent("overlays_failed", { error: err instanceof Error ? err.message : "unknown" });
        });
      }

      mapCameraRef.current?.fitBounds(
        [destination.longitude, destination.latitude],
        [origin.longitude, origin.latitude],
        [80, 80, 300, 80],
        500,
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Route planning failed";
      transitionSheet(() => {
        setPlanningRoute(false);
        setPlanError(msg);
      });
      showToast(msg);
      logPrototypeEvent("route_preview_failed", { error: msg });
    }
  }

  async function handleStartWalk() {
    if (!routePreview || !previewRoute || startingWalk) return;
    setStartingWalk(true);
    try {
      let journeyId: string | undefined;
      try {
        const journey = await apiRequest<{ id: string }>("/journeys", getToken, {
          method: "POST",
          body: {
            origin_label: routePreview.origin.label ?? "Current location",
            destination_label: routePreview.destination.label ?? "Destination",
            selected_route_id: previewRoute.candidate_id,
            ranked_routes: routePreview.plan.ranked_routes,
          },
        });
        journeyId = journey.id;
      } catch {
        // journey save is optional
      }

      transitionSheet(() => {
        startSession({
          journeyId: journeyId ?? null,
          origin: routePreview.origin,
          destination: routePreview.destination,
          selectedRouteId: previewRoute.candidate_id,
          rankedRoutes: routePreview.plan.ranked_routes,
        });
        setRoutePreview(null);
      });
    } catch {
      // handled by session
    } finally {
      setStartingWalk(false);
    }
  }

  function cancelRoutePreview() {
    transitionSheet(() => {
      setRoutePreview(null);
      setSelectedPreviewId(null);
      setRouteOverlays([]);
    });
  }

  const theme = {
    topPanel: highContrast
      ? "bg-white border-black/20"
      : "bg-slate-950/85 border-cyan-500/20",
    bottomPanel: highContrast
      ? "bg-white border-black/20"
      : "bg-slate-950/90 border-cyan-500/25",
    primaryText: highContrast ? "text-slate-950" : "text-white",
    secondaryText: highContrast ? "text-slate-700" : "text-slate-300",
  };

  const routeCoordinates = useMemo(
    () => flattenGeometryCoordinates(session?.activeRoute.geometry_geojson ?? null),
    [session?.activeRoute.geometry_geojson],
  );

  const routeShape = useMemo(() => {
    if (!session?.activeRoute.geometry_geojson) return null;
    return {
      type: "Feature" as const,
      properties: {},
      geometry: session.activeRoute.geometry_geojson,
    };
  }, [session?.activeRoute.geometry_geojson]);

  const reportFeatures = useMemo(() => {
    if (convexEnabled && reports) {
      return {
        type: "FeatureCollection" as const,
        features: reports
          .filter(
            (report) =>
              typeof report.latitude === "number" &&
              typeof report.longitude === "number",
          )
          .map((report) => ({
            type: "Feature" as const,
            properties: {
              id: report._id,
              category: report.category,
              summary: report.description ?? "",
              created_at: new Date(report.createdAt).toISOString(),
            },
            geometry: {
              type: "Point" as const,
              coordinates: [report.longitude as number, report.latitude as number],
            },
          })),
      };
    }

    if (!apiReports.length) {
      return {
        type: "FeatureCollection" as const,
        features: [],
      };
    }
    return {
      type: "FeatureCollection" as const,
      features: apiReports
        .map((report) => ({
          type: "Feature" as const,
          properties: {
            id: report.id,
            category: report.category,
            summary: report.summary ?? "",
            created_at: report.created_at,
          },
          geometry: {
            type: "Point" as const,
            coordinates: [report.longitude, report.latitude],
          },
        })),
    };
  }, [apiReports, convexEnabled, reports]);

  const heatmapFeatures = useMemo(() => {
    if (!heatmapData?.items?.length) {
      return {
        type: "FeatureCollection" as const,
        features: [],
      };
    }

    return {
      type: "FeatureCollection" as const,
      features: heatmapData.items.map((item) => ({
        type: "Feature" as const,
        properties: {
          risk_score: item.risk_score,
          source_count: item.source_count,
        },
        geometry: {
          type: "Point" as const,
          coordinates: [item.center_longitude, item.center_latitude],
        },
      })),
    };
  }, [heatmapData]);

  const crimePinFeatures = useMemo(() => {
    if (!heatmapData?.crime_pins?.length) {
      return { type: "FeatureCollection" as const, features: [] };
    }
    return {
      type: "FeatureCollection" as const,
      features: heatmapData.crime_pins.map((pin) => ({
        type: "Feature" as const,
        properties: {
          category: pin.category,
          month: pin.month,
        },
        geometry: {
          type: "Point" as const,
          coordinates: [pin.longitude, pin.latitude],
        },
      })),
    };
  }, [heatmapData?.crime_pins]);

  const overlayFeatures = useMemo(() => {
    if (!routeOverlays.length) {
      return { type: "FeatureCollection" as const, features: [] };
    }
    return {
      type: "FeatureCollection" as const,
      features: routeOverlays.map((item) => ({
        type: "Feature" as const,
        properties: {
          overlay_type: item.overlay_type,
          subtype: item.subtype,
          name: item.name,
        },
        geometry: {
          type: "Point" as const,
          coordinates: [item.longitude, item.latitude],
        },
      })),
    };
  }, [routeOverlays]);

  async function startLocationTracking() {
    setLocationError(null);
    try {
      const permission = await Location.requestForegroundPermissionsAsync();
      if (permission.status !== "granted") {
        setPermissionState("denied");
        setLocationError("Location permission denied. Live walk fallback is map-only mode.");
        logPrototypeEvent("location_permission_failed", {
          status: permission.status,
        });
        return;
      }

      setPermissionState("granted");

      const lastKnown = await Location.getLastKnownPositionAsync();
      if (lastKnown) {
        setCurrentLocation({
          latitude: lastKnown.coords.latitude,
          longitude: lastKnown.coords.longitude,
        });
      } else {
        const current = await Location.getCurrentPositionAsync({});
        setCurrentLocation({
          latitude: current.coords.latitude,
          longitude: current.coords.longitude,
        });
      }

      if (locationWatcherRef.current) {
        locationWatcherRef.current.remove();
        locationWatcherRef.current = null;
      }

      locationWatcherRef.current = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.Balanced,
          timeInterval: 2500,
          distanceInterval: 3,
        },
        (position) => {
          setCurrentLocation({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          });
        },
      );
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Current location is unavailable. Make sure that location services are enabled.";
      setLocationError(message);
      logPrototypeEvent("location_tracking_failed", { error: message });
    }
  }

  async function syncNearbyReports() {
    if (syncingReports || (!isLoaded && !demoMode) || !authed) return;
    setSyncingReports(true);
    try {
      const center =
        mapCenter ?? currentLocation ?? session?.lastLocation ?? BIRMINGHAM_DEFAULT_CENTER;
      const nearby = await apiRequest<NearbyReportsResponse>("/reports/nearby", getToken, {
        query: {
          latitude: center.latitude,
          longitude: center.longitude,
          radius_metres: Math.round(Math.min(20000, 500000 / Math.pow(2, mapZoom))),
          limit: 50,
        },
      });
      setApiReports(nearby.items);
      if (!convexEnabled || !hasConvexToken) {
        return;
      }
      for (const report of nearby.items) {
        try {
          await upsertReport({
            apiReportId: report.id,
            latitude: report.latitude,
            longitude: report.longitude,
            location: `${report.latitude.toFixed(5)}, ${report.longitude.toFixed(5)}`,
            description: report.summary,
            category: mapCanonicalToConvexCategory(report.category),
            createdAt: new Date(report.created_at).getTime(),
            status: "synced",
          });
        } catch (mirrorError) {
          const message =
            mirrorError instanceof Error
              ? mirrorError.message
              : "Convex mirror update failed.";
          logPrototypeEvent("map_convex_sync_failed", { error: message, id: report.id });
        }
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "report sync failed";
      showToast("Reports: " + message);
      logPrototypeEvent("report_reconciliation_failed", { error: message });
    } finally {
      setSyncingReports(false);
    }
  }

  async function syncHeatmap() {
    if (!heatmapEnabled || syncingHeatmap || (!isLoaded && !demoMode) || !authed) return;
    setHeatmapError(null);
    setSyncingHeatmap(true);
    try {
      const center =
        mapCenter ?? currentLocation ?? session?.lastLocation ?? BIRMINGHAM_DEFAULT_CENTER;
      const payload = await apiRequest<HeatmapResponse>("/heatmap", getToken, {
        query: {
          latitude: center.latitude,
          longitude: center.longitude,
          radius_metres: Math.round(Math.min(8000, Math.max(1500, 40000000 / Math.pow(2, mapZoom)))),
          cell_size_metres: HEATMAP_CELL_SIZE_METRES,
          category: "all-crime",
        },
      });
      setHeatmapData(payload);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Heatmap sync failed";
      setHeatmapError(message);
      showToast("Heatmap: " + message);
      logPrototypeEvent("heatmap_sync_failed", { error: message });
    } finally {
      setSyncingHeatmap(false);
    }
  }

  async function rerouteFromCurrentPosition(location: Coordinates) {
    if (!session || session.rerouting) return;
    try {
      setRerouting(true);
      logPrototypeEvent("route_reroute_triggered", {
        location,
      });
      const routeToggles = buildRoutePlanningToggles(routeOptions);
      const reroute = await apiRequest<RoutePlanResponse>("/routes/plan", getToken, {
        method: "POST",
        requireAuth: false,
        body: {
          origin: {
            latitude: location.latitude,
            longitude: location.longitude,
            label: "Current location",
          },
          destination: {
            latitude: session.destination.latitude,
            longitude: session.destination.longitude,
            label: session.destination.label ?? "Destination",
          },
          depart_at: new Date().toISOString(),
          alternatives: lowDataMode ? 1 : 3,
          ...routeToggles,
        },
      });
      replaceActiveRoute({
        selectedRouteId: reroute.selected_route_id,
        rankedRoutes: reroute.ranked_routes,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "reroute failed";
      logPrototypeEvent("route_reroute_failed", {
        error: message,
      });
    } finally {
      setRerouting(false);
    }
  }

  useEffect(() => {
    void startLocationTracking();
    return () => {
      if (locationWatcherRef.current) {
        locationWatcherRef.current.remove();
        locationWatcherRef.current = null;
      }
    };
  }, []);

  const mapIdleTimerRef = useRef<number | null>(null);

  function handleMapIdle(state: { properties: { center: number[]; zoom: number } }) {
    const [lng, lat] = state.properties.center;
    if (lng === undefined || lat === undefined) return;
    setMapCenter({ latitude: lat, longitude: lng });
    if (state.properties.zoom) setMapZoom(state.properties.zoom);
    void reverseGeocode(lat, lng).then(setAreaName);

    // debounce the heavy API calls so quick panning doesn't spam
    if (mapIdleTimerRef.current) clearTimeout(mapIdleTimerRef.current);
    mapIdleTimerRef.current = setTimeout(() => {
      void syncNearbyReports();
      void syncHeatmap();
    }, 800) as unknown as number;
  }

  // read session from a ref so progress updates don't re-trigger this effect
  useEffect(() => {
    const s = sessionRef.current;
    if (!s || !currentLocation || s.status !== "active") return;
    if (routeCoordinates.length < 2) return;

    const progress = computeRouteProgress(
      currentLocation,
      routeCoordinates,
      s.activeRoute.duration_seconds,
      s.activeRoute.navigation?.steps ?? [],
    );

    updateProgress({
      progressRatio: progress.progressRatio,
      remainingDistanceMetres: progress.remainingDistanceMetres,
      remainingDurationSeconds: progress.remainingDurationSeconds,
      distanceFromRouteMetres: progress.distanceFromRouteMetres,
      currentStepIndex: progress.currentStepIndex,
      lastLocation: currentLocation,
    });

    if (progress.distanceFromRouteMetres > OFF_ROUTE_THRESHOLD_METRES) {
      const newCount = s.offRouteSamples + 1;
      incrementOffRouteSamples();
      if (newCount >= OFF_ROUTE_SAMPLE_LIMIT && !s.rerouting) {
        void rerouteFromCurrentPosition(currentLocation);
      }
    } else {
      resetOffRouteSamples();
    }

    if (progress.remainingDistanceMetres <= 20) {
      setWalkStatus("completed");
      clearSession();
    }
  // only re-run when the user's position changes or the route geometry changes
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentLocation, routeCoordinates]);

  useEffect(() => {
    if (!mapFocusTarget) return;
    mapCameraRef.current?.setCamera({
      centerCoordinate: [mapFocusTarget.longitude, mapFocusTarget.latitude],
      zoomLevel: 14,
      animationDuration: 700,
    });
    //.sleep()
    const sleep = setTimeout(() => {
      setMapFocusTarget(null);
    }, 750); //gives time to reload

    return () => clearTimeout(sleep);
  }, [mapFocusTarget, setMapFocusTarget]);

  useEffect(() => {
    if (!isFocused) return;
    void syncNearbyReports();
    void syncHeatmap();

    if (reportSyncTimerRef.current) {
      clearInterval(reportSyncTimerRef.current);
    }
    reportSyncTimerRef.current = setInterval(() => {
      void syncNearbyReports();
    }, 30_000) as unknown as number;

    if (heatmapSyncTimerRef.current) {
      clearInterval(heatmapSyncTimerRef.current);
    }
    heatmapSyncTimerRef.current = setInterval(() => {
      void syncHeatmap();
    }, 45_000) as unknown as number;

    return () => {
      if (reportSyncTimerRef.current) {
        clearInterval(reportSyncTimerRef.current);
        reportSyncTimerRef.current = null;
      }
      if (heatmapSyncTimerRef.current) {
        clearInterval(heatmapSyncTimerRef.current);
        heatmapSyncTimerRef.current = null;
      }
    };
  }, [
    isFocused,
    currentLocation,
    session?.lastLocation ?? null,
    convexEnabled,
    heatmapEnabled,
    authed,
  ]);

  const currentStepInstruction =
    session?.activeRoute.navigation?.steps?.[session.currentStepIndex]?.instruction ??
    "Follow the selected route";

  const mapEnabled = Boolean(process.env.EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN);

  return (
    <View className="flex-1 bg-slate-950">
      {mapEnabled ? (
        <Mapbox.MapView
          key={highContrast ? "light" : "dark"}
          style={{ flex: 1 }}
          styleURL={highContrast ? Mapbox.StyleURL.Light : Mapbox.StyleURL.Dark}
          scaleBarEnabled={false}
          compassEnabled={false}
          onMapIdle={handleMapIdle}
          onPress={(e: any) => handleMapPress(e)}
        >
          <Mapbox.Camera
            ref={mapCameraRef}
            zoomLevel={14}
            animationDuration={0}
            centerCoordinate={
              currentLocation
                ? [currentLocation.longitude, currentLocation.latitude]
                : DEFAULT_CENTER
            }
          />

          {heatmapEnabled ? (
            <Mapbox.ShapeSource id="heatmap-source" shape={heatmapFeatures}>
              <Mapbox.HeatmapLayer
                id="heatmap-layer"
                style={{
                  heatmapRadius: [
                    "interpolate", ["linear"], ["zoom"],
                    10, 10,
                    12, 30,
                    14, 60,
                    15, 90,
                    16, 120,
                    18, 160,
                  ] as unknown as number,
                  heatmapWeight: [
                    "interpolate", ["linear"], ["get", "risk_score"],
                    0, 0,
                    2, 0.2,
                    5, 0.5,
                    10, 1,
                  ] as unknown as number,
                  heatmapIntensity: [
                    "interpolate", ["linear"], ["zoom"],
                    10, 0.3,
                    12, 0.6,
                    14, 1,
                    16, 1.5,
                    18, 2,
                  ] as unknown as number,
                  heatmapColor: (highContrast
                    ? [
                        "interpolate", ["linear"], ["heatmap-density"],
                        0, "rgba(0,0,0,0)",
                        0.15, "rgba(132,204,22,0.5)",
                        0.35, "rgba(245,158,11,0.7)",
                        0.6, "rgba(220,38,38,0.85)",
                        1.0, "rgba(153,27,27,0.95)",
                      ]
                    : [
                        "interpolate", ["linear"], ["heatmap-density"],
                        0, "rgba(0,0,0,0)",
                        0.1, "rgba(34,197,94,0.4)",
                        0.3, "rgba(250,204,21,0.6)",
                        0.5, "rgba(249,115,22,0.7)",
                        0.7, "rgba(239,68,68,0.8)",
                        1.0, "rgba(185,28,28,0.9)",
                      ]
                  ) as unknown as string,
                  heatmapOpacity: [
                    "interpolate", ["linear"], ["zoom"],
                    10, 0.3,
                    12, 0.5,
                    14, 0.65,
                    18, 0.4,
                  ] as unknown as number,
                }}
              />
            </Mapbox.ShapeSource>
          ) : null}

          {routeShape ? (
            <Mapbox.ShapeSource id="active-route-source" shape={routeShape}>
              <Mapbox.LineLayer
                id="active-route-line"
                style={{
                  lineColor: highContrast ? "#0891b2" : "#06b6d4",
                  lineWidth: 6,
                  lineOpacity: 0.9,
                  lineCap: "round" as const,
                  lineJoin: "round" as const,
                }}
              />
            </Mapbox.ShapeSource>
          ) : null}

          {showReportPins ? (
            <Mapbox.ShapeSource
              id="reports-source"
              shape={reportFeatures}
              onPress={(e: any) => {
                const feature = e?.features?.[0];
                if (!feature?.properties) return;
                const coords = feature.geometry?.coordinates;
                setSelectedReport({
                  category: feature.properties.category ?? "report",
                  summary: feature.properties.summary ?? "",
                  created_at: feature.properties.created_at ?? "",
                  latitude: coords?.[1] ?? 0,
                  longitude: coords?.[0] ?? 0,
                });
              }}
            >
              <Mapbox.CircleLayer
                id="report-points"
                style={{
                  circleRadius: 8,
                  circleColor: highContrast ? "#b91c1c" : "#f43f5e",
                  circleStrokeColor: "#ffffff",
                  circleStrokeWidth: 2,
                  circleOpacity: 0.9,
                }}
              />
            </Mapbox.ShapeSource>
          ) : null}

          {showCrimePins ? (
            <Mapbox.ShapeSource
              id="crime-pins-source"
              shape={crimePinFeatures}
              onPress={(e: any) => {
                const feature = e?.features?.[0];
                if (!feature?.properties) return;
                const coords = feature.geometry?.coordinates;
                setSelectedReport({
                  category: feature.properties.category ?? "crime",
                  summary: `Police recorded crime (${feature.properties.month ?? "unknown date"})`,
                  created_at: feature.properties.month ? `${feature.properties.month}-01T00:00:00Z` : "",
                  latitude: coords?.[1] ?? 0,
                  longitude: coords?.[0] ?? 0,
                });
              }}
            >
              <Mapbox.CircleLayer
                id="crime-pin-points"
                style={{
                  circleRadius: 4,
                  circleColor: highContrast ? "#1d4ed8" : "#60a5fa",
                  circleStrokeColor: "#ffffff",
                  circleStrokeWidth: 1,
                  circleOpacity: 0.8,
                }}
              />
            </Mapbox.ShapeSource>
          ) : null}

          {session ? (
            <>
              <Mapbox.MarkerView
                id="origin-marker"
                coordinate={[session.origin.longitude, session.origin.latitude]}
              >
                <View className="h-3 w-3 rounded-full bg-emerald-500" />
              </Mapbox.MarkerView>
              <Mapbox.MarkerView
                id="destination-marker"
                coordinate={[session.destination.longitude, session.destination.latitude]}
              >
                <View className="h-3 w-3 rounded-full bg-rose-500" />
              </Mapbox.MarkerView>
            </>
          ) : null}

          {!session && previewRouteShapes.length > 0 ? (
            <>
              {previewRouteShapes.map((route) => {
                const isSelected = route.id === (selectedPreviewId ?? routePreview?.plan.selected_route_id);
                return (
                  <Mapbox.ShapeSource key={route.id} id={`preview-${route.id}`} shape={route.shape}>
                    <Mapbox.LineLayer
                      id={`preview-line-${route.id}`}
                      style={{
                        lineColor: isSelected
                          ? (highContrast ? "#0891b2" : "#06b6d4")
                          : (highContrast ? "#94a3b8" : "#475569"),
                        lineWidth: isSelected ? 6 : 3,
                        lineOpacity: isSelected ? 0.9 : 0.3,
                        lineCap: "round" as const,
                        lineJoin: "round" as const,
                      }}
                    />
                  </Mapbox.ShapeSource>
                );
              })}
              {selectedStepSegments.length > 0 ? (
                selectedStepSegments.map((seg) => (
                  <Mapbox.ShapeSource key={seg.id} id={`seg-${seg.id}`} shape={seg.shape}>
                    <Mapbox.LineLayer
                      id={`seg-line-${seg.id}`}
                      style={{
                        lineColor: seg.mode === "transit" ? "#a855f7" : "#06b6d4",
                        lineWidth: 6,
                        lineOpacity: 0.9,
                        lineCap: "round" as const,
                        lineJoin: "round" as const,
                        lineDasharray: seg.mode === "walking" ? [1, 1.5] : undefined,
                      }}
                    />
                  </Mapbox.ShapeSource>
                ))
              ) : null}
              {routePreview ? (
                <>
                  <Mapbox.MarkerView
                    id="preview-origin"
                    coordinate={[routePreview.origin.longitude, routePreview.origin.latitude]}
                  >
                    <View className="h-3 w-3 rounded-full bg-emerald-500 border border-white" />
                  </Mapbox.MarkerView>
                  <Mapbox.MarkerView
                    id="preview-destination"
                    coordinate={[routePreview.destination.longitude, routePreview.destination.latitude]}
                  >
                    <View className="h-3 w-3 rounded-full bg-rose-500 border border-white" />
                  </Mapbox.MarkerView>
                </>
              ) : null}
            </>
          ) : null}

          {overlayFeatures.features.length > 0 ? (
            <Mapbox.ShapeSource id="overlay-source" shape={overlayFeatures}>
              <Mapbox.CircleLayer
                id="overlay-points"
                style={{
                  circleRadius: [
                    "interpolate", ["linear"], ["zoom"],
                    10, 3,
                    14, 5,
                    18, 8,
                  ] as unknown as number,
                  circleColor: [
                    "match", ["get", "overlay_type"],
                    "transit", "#818cf8",
                    "service", "#34d399",
                    "report", "#f87171",
                    "#94a3b8",
                  ] as unknown as string,
                  circleStrokeColor: "#ffffff",
                  circleStrokeWidth: 1,
                  circleOpacity: 0.85,
                }}
              />
            </Mapbox.ShapeSource>
          ) : null}

          {currentLocation ? (
            <Mapbox.MarkerView
              id="current-marker"
              coordinate={[currentLocation.longitude, currentLocation.latitude]}
            >
              <View
                style={{
                  width: 18,
                  height: 18,
                  borderRadius: 9,
                  backgroundColor: "#3b82f6",
                  borderWidth: 3,
                  borderColor: "#ffffff",
                  shadowColor: "#3b82f6",
                  shadowOffset: { width: 0, height: 0 },
                  shadowOpacity: 0.5,
                  shadowRadius: 8,
                }}
              />
            </Mapbox.MarkerView>
          ) : null}

          {reportMode && reportLocation ? (
            <Mapbox.MarkerView
              id="report-pin"
              coordinate={[reportLocation.longitude, reportLocation.latitude]}
            >
              <View className="h-4 w-4 rounded-full bg-amber-500 border-2 border-white" />
            </Mapbox.MarkerView>
          ) : null}
        </Mapbox.MapView>
      ) : (
        <View className="flex-1 items-center justify-center px-6">
          <Text className="text-slate-200 text-center">
            Add EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN to render the map.
          </Text>
        </View>
      )}

      <View
        className="absolute left-0 right-0"
        style={{ top: insets.top + 8 }}
      >
        <View className="items-center">
          <View
            className={`rounded-full px-5 py-2 ${
              highContrast ? "bg-white/90" : "bg-slate-900/70"
            }`}
          >
            <Text className={`text-sm font-medium ${theme.primaryText}`} numberOfLines={1}>
              {areaName}
            </Text>
          </View>
        </View>

        <View className="absolute left-4">
          <Pressable
            onPress={() => setHeatmapEnabled((prev) => !prev)}
            className={`flex-row items-center rounded-full pl-2 pr-3 py-1.5 mb-2 ${
              heatmapEnabled
                ? "bg-cyan-500"
                : highContrast ? "bg-white/90" : "bg-slate-900/70"
            }`}
          >
            <Ionicons name="flame" size={16} color={heatmapEnabled ? "#ffffff" : highContrast ? "#64748b" : "#94a3b8"} />
            <Text className={`text-[10px] font-semibold ml-1.5 ${heatmapEnabled ? "text-white" : theme.primaryText}`}>Heatmap</Text>
          </Pressable>
          <Pressable
            onPress={() => setShowCrimePins((prev) => !prev)}
            className={`flex-row items-center rounded-full pl-2 pr-3 py-1.5 mb-2 ${
              showCrimePins
                ? "bg-blue-500"
                : highContrast ? "bg-white/90" : "bg-slate-900/70"
            }`}
          >
            <Ionicons name="shield-outline" size={14} color={showCrimePins ? "#ffffff" : highContrast ? "#64748b" : "#94a3b8"} />
            <Text className={`text-[10px] font-semibold ml-1.5 ${showCrimePins ? "text-white" : theme.primaryText}`}>Crime</Text>
          </Pressable>
          <Pressable
            onPress={() => setShowReportPins((prev) => !prev)}
            className={`flex-row items-center rounded-full pl-2 pr-3 py-1.5 ${
              showReportPins
                ? "bg-rose-500"
                : highContrast ? "bg-white/90" : "bg-slate-900/70"
            }`}
          >
            <Ionicons name="flag-outline" size={14} color={showReportPins ? "#ffffff" : highContrast ? "#64748b" : "#94a3b8"} />
            <Text className={`text-[10px] font-semibold ml-1.5 ${showReportPins ? "text-white" : theme.primaryText}`}>Reports</Text>
          </Pressable>
        </View>

        <View className="absolute right-4 flex-row">
          <Link href="/profile" asChild>
            <Pressable className={`mr-2 h-10 w-10 items-center justify-center rounded-full ${
              highContrast ? "bg-white/90" : "bg-slate-900/70"
            }`}>
              <Ionicons name="person-outline" size={19} color={highContrast ? "#0f172a" : "#ffffff"} />
            </Pressable>
          </Link>
          <Link href="/settings" asChild>
            <Pressable className={`h-10 w-10 items-center justify-center rounded-full ${
              highContrast ? "bg-white/90" : "bg-slate-900/70"
            }`}>
              <Ionicons name="settings-outline" size={19} color={highContrast ? "#0f172a" : "#ffffff"} />
            </Pressable>
          </Link>
        </View>
      </View>

      {syncingHeatmap || syncingReports ? (
        <Animated.View
          entering={FadeIn.duration(150)}
          exiting={FadeOut.duration(150)}
          className={`absolute self-center rounded-full px-3 py-1.5 ${
            highContrast ? "bg-white/90" : "bg-slate-900/70"
          }`}
          style={{ top: insets.top + 48 }}
        >
          <Text className={`text-[10px] font-medium ${theme.primaryText}`}>
            {syncingHeatmap ? "Loading heatmap..." : "Syncing reports..."}
          </Text>
        </Animated.View>
      ) : null}

      {toast ? (
        <Animated.View
          entering={FadeIn.duration(200)}
          exiting={FadeOut.duration(200)}
          className="absolute left-4 right-4 rounded-xl bg-red-500/90 px-4 py-3"
          style={{ top: insets.top + 52 }}
        >
          <Text className="text-white text-xs font-semibold">{toast}</Text>
        </Animated.View>
      ) : null}

      {selectedReport ? (
        <Animated.View
          entering={FadeIn.duration(150)}
          exiting={FadeOut.duration(100)}
          className={`absolute left-4 right-4 rounded-xl border px-4 py-3 ${
            highContrast ? "bg-white border-slate-200" : "bg-slate-900/95 border-slate-700/40"
          }`}
          style={{ bottom: 270 }}
        >
          <View className="flex-row items-start justify-between">
            <View className="flex-1 mr-3">
              <Text className={`text-sm font-bold ${theme.primaryText}`}>
                {selectedReport.category.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
              </Text>
              {selectedReport.summary ? (
                <Text className={`text-xs mt-1 ${theme.secondaryText}`} numberOfLines={3}>
                  {selectedReport.summary}
                </Text>
              ) : null}
              {selectedReport.created_at ? (
                <Text className={`text-[10px] mt-1 ${theme.secondaryText}`}>
                  {new Date(selectedReport.created_at).toLocaleString("en-GB")}
                </Text>
              ) : null}
            </View>
            <Pressable onPress={() => setSelectedReport(null)} hitSlop={10}>
              <Ionicons name="close-circle" size={22} color={highContrast ? "#94a3b8" : "#64748b"} />
            </Pressable>
          </View>
        </Animated.View>
      ) : null}

      {routePreview || session ? (
        <View
          className={`absolute left-3 rounded-lg px-2.5 py-2 ${
            highContrast ? "bg-white/95" : "bg-slate-900/80"
          }`}
          style={{ bottom: 260 }}
        >
          <View className="flex-row items-center mb-1">
            <View className="h-2.5 w-2.5 rounded-full bg-blue-500 mr-1.5" />
            <Text className={`text-[9px] ${theme.primaryText}`}>You</Text>
          </View>
          <View className="flex-row items-center mb-1">
            <View className="h-2.5 w-2.5 rounded-full bg-[#818cf8] mr-1.5" />
            <Text className={`text-[9px] ${theme.primaryText}`}>Transit</Text>
          </View>
          <View className="flex-row items-center mb-1">
            <View className="h-2.5 w-2.5 rounded-full bg-[#34d399] mr-1.5" />
            <Text className={`text-[9px] ${theme.primaryText}`}>Services</Text>
          </View>
          <View className="flex-row items-center mb-1">
            <View className="h-2.5 w-2.5 rounded-full bg-[#f87171] mr-1.5" />
            <Text className={`text-[9px] ${theme.primaryText}`}>Reports</Text>
          </View>
          <View className="flex-row items-center mb-1">
            <View className="h-2.5 w-2.5 rounded-full bg-emerald-500 mr-1.5" />
            <Text className={`text-[9px] ${theme.primaryText}`}>Start</Text>
          </View>
          <View className="flex-row items-center">
            <View className="h-2.5 w-2.5 rounded-full bg-purple-500 mr-1.5" />
            <Text className={`text-[9px] ${theme.primaryText}`}>Bus/Train</Text>
          </View>
        </View>
      ) : null}

      {/* floating route settings groups */}
      {!reportPickingLocation ? (
        <View className="absolute right-3" style={{ bottom: 260 }}>
          {expandedSettingsGroup ? (
            <Animated.View
              entering={FadeIn.duration(150)}
              exiting={FadeOut.duration(100)}
              className={`rounded-xl border px-3 py-2 mb-2 ${
                highContrast ? "bg-white/95 border-slate-200" : "bg-slate-900/95 border-slate-700/40"
              }`}
              style={{ width: 220 }}
            >
              <View className="flex-row items-center justify-between mb-1.5">
                <Text className={`text-[11px] font-bold ${highContrast ? "text-slate-900" : "text-cyan-300"}`}>
                  {expandedSettingsGroup === "accessibility" ? "Accessibility"
                    : expandedSettingsGroup === "comfort" ? "Waiting areas"
                    : "General"}
                </Text>
                <Pressable onPress={() => setExpandedSettingsGroup(null)} hitSlop={8}>
                  <Ionicons name="close" size={16} color={highContrast ? "#64748b" : "#94a3b8"} />
                </Pressable>
              </View>

              {expandedSettingsGroup === "accessibility" ? (
                <>
                  {([
                    ["avoid_stairs", "Avoid stairs"],
                    ["step_free_access", "Step-free access"],
                    ["lifts_available", "Lifts"],
                    ["ramps_available", "Ramps"],
                    ["escalators_available", "Escalators"],
                  ] as [keyof RouteAccessibilityChoices, string][]).map(([key, label]) => (
                    <View key={key} className="flex-row items-center justify-between py-1">
                      <Text className={`text-[11px] ${theme.primaryText}`}>{label}</Text>
                      <Switch
                        value={routeOptions.accessibility[key]}
                        onValueChange={(v) => setAccessibilityOption(key, v)}
                        style={{ transform: [{ scale: 0.75 }] }}
                      />
                    </View>
                  ))}
                </>
              ) : expandedSettingsGroup === "comfort" ? (
                <>
                  {([
                    ["safe_waiting_areas", "Safe waiting"],
                    ["well_lit_waiting_areas", "Well lit"],
                    ["wifi_nearby", "Wi-Fi nearby"],
                    ["staffed_venues_nearby", "Staffed venues"],
                    ["open_venues_nearby", "Open venues"],
                    ["safe_areas_nearby", "Safe area coverage"],
                  ] as [keyof RouteWaitingAreaChoices, string][]).map(([key, label]) => (
                    <View key={key} className="flex-row items-center justify-between py-1">
                      <Text className={`text-[11px] ${theme.primaryText}`}>{label}</Text>
                      <Switch
                        value={routeOptions.waiting_areas[key]}
                        onValueChange={(v) => setWaitingAreaOption(key, v)}
                        style={{ transform: [{ scale: 0.75 }] }}
                      />
                    </View>
                  ))}
                </>
              ) : (
                <>
                  <View className="flex-row items-center justify-between py-1">
                    <Text className={`text-[11px] ${theme.primaryText}`}>High contrast</Text>
                    <Switch value={highContrast} onValueChange={setHighContrast} style={{ transform: [{ scale: 0.75 }] }} />
                  </View>
                  <View className="flex-row items-center justify-between py-1">
                    <Text className={`text-[11px] ${theme.primaryText}`}>Leave now alerts</Text>
                    <Switch value={leaveNowAlerts} onValueChange={setLeaveNowAlerts} style={{ transform: [{ scale: 0.75 }] }} />
                  </View>
                  <View className="flex-row items-center justify-between py-1">
                    <Text className={`text-[11px] ${theme.primaryText}`}>Low data mode</Text>
                    <Switch value={lowDataMode} onValueChange={setLowDataMode} style={{ transform: [{ scale: 0.75 }] }} />
                  </View>
                </>
              )}
            </Animated.View>
          ) : null}

          <View className="items-end">
            <Pressable
              onPress={() => setExpandedSettingsGroup(expandedSettingsGroup === "accessibility" ? null : "accessibility")}
              className={`flex-row items-center rounded-full pl-2 pr-3 py-1.5 mb-1.5 ${
                expandedSettingsGroup === "accessibility"
                  ? highContrast ? "bg-slate-900" : "bg-cyan-500"
                  : highContrast ? "bg-white/90" : "bg-slate-900/80"
              }`}
            >
              <Ionicons name="accessibility-outline" size={15} color={expandedSettingsGroup === "accessibility" ? "#ffffff" : highContrast ? "#0f172a" : "#94a3b8"} />
              <Text className={`text-[10px] font-semibold ml-1.5 ${expandedSettingsGroup === "accessibility" ? "text-white" : theme.primaryText}`}>Access</Text>
            </Pressable>
            <Pressable
              onPress={() => setExpandedSettingsGroup(expandedSettingsGroup === "comfort" ? null : "comfort")}
              className={`flex-row items-center rounded-full pl-2 pr-3 py-1.5 mb-1.5 ${
                expandedSettingsGroup === "comfort"
                  ? highContrast ? "bg-slate-900" : "bg-cyan-500"
                  : highContrast ? "bg-white/90" : "bg-slate-900/80"
              }`}
            >
              <Ionicons name="shield-checkmark-outline" size={15} color={expandedSettingsGroup === "comfort" ? "#ffffff" : highContrast ? "#0f172a" : "#94a3b8"} />
              <Text className={`text-[10px] font-semibold ml-1.5 ${expandedSettingsGroup === "comfort" ? "text-white" : theme.primaryText}`}>Comfort</Text>
            </Pressable>
            <Pressable
              onPress={() => setExpandedSettingsGroup(expandedSettingsGroup === "general" ? null : "general")}
              className={`flex-row items-center rounded-full pl-2 pr-3 py-1.5 ${
                expandedSettingsGroup === "general"
                  ? highContrast ? "bg-slate-900" : "bg-cyan-500"
                  : highContrast ? "bg-white/90" : "bg-slate-900/80"
              }`}
            >
              <Ionicons name="settings-outline" size={15} color={expandedSettingsGroup === "general" ? "#ffffff" : highContrast ? "#0f172a" : "#94a3b8"} />
              <Text className={`text-[10px] font-semibold ml-1.5 ${expandedSettingsGroup === "general" ? "text-white" : theme.primaryText}`}>General</Text>
            </Pressable>
          </View>
        </View>
      ) : null}

      <Animated.View
        style={[{ paddingBottom: Math.max(insets.bottom, 16) }, sheetStyle]}
        className={`absolute left-0 right-0 bottom-0 rounded-t-3xl border-t px-5 pt-4 ${theme.bottomPanel}`}
      >
        {permissionState === "denied" ? (
          <Text className="text-xs text-amber-300 mb-2">
            Location denied. Route can still be viewed, but live progress is disabled.
          </Text>
        ) : null}
        {locationError ? (
          <Text className="text-xs text-red-300 mb-2">{locationError}</Text>
        ) : null}

        <View>

        {session ? (
          <>
            <Text className={`font-bold ${theme.primaryText}`}>
              {session.activeRoute.label ?? "Active route"}
            </Text>
            <Text className={`text-xs mt-1 ${theme.secondaryText}`}>
              Step {session.currentStepIndex + 1}: {currentStepInstruction}
            </Text>
            <Text className={`text-xs mt-1 ${theme.secondaryText}`}>
              {formatDistanceMetres(session.remainingDistanceMetres)} remaining |{" "}
              {Math.ceil(session.remainingDurationSeconds / 60)} min | deviation{" "}
              {Math.round(session.distanceFromRouteMetres)} m
            </Text>
            <View className="flex-row mt-3">
              <Pressable
                onPress={() =>
                  setWalkStatus(session.status === "paused" ? "active" : "paused")
                }
                className="mr-2 rounded-xl bg-cyan-500 px-4 py-2"
              >
                <Text className="text-slate-950 font-bold">
                  {session.status === "paused" ? "Resume" : "Pause"}
                </Text>
              </Pressable>
              <Pressable
                onPress={() => clearSession()}
                className="rounded-xl bg-rose-500 px-4 py-2"
              >
                <Text className="text-white font-bold">End</Text>
              </Pressable>
            </View>
          </>
        ) : servicesMode ? (
          <ScrollView style={{ maxHeight: 400 }} contentContainerStyle={{ paddingBottom: 8 }} showsVerticalScrollIndicator={false}>
            <View className="flex-row items-center justify-between mb-3">
              <Text className={`font-bold ${theme.primaryText}`}>Nearby services</Text>
              <Pressable onPress={closeServicesMode}>
                <Ionicons name="close" size={22} color={highContrast ? "#0f172a" : "#94a3b8"} />
              </Pressable>
            </View>

            <View className="flex-row flex-wrap mb-3">
              {SERVICE_CATEGORIES.map((cat) => (
                <Pressable
                  key={cat.value}
                  onPress={() => loadServices(cat.value)}
                  className={`rounded-full border px-3 py-1.5 mr-2 mb-2 ${
                    serviceCategory === cat.value
                      ? highContrast ? "bg-slate-900 border-slate-900" : "bg-cyan-500 border-cyan-500"
                      : highContrast ? "bg-slate-100 border-slate-300" : "bg-slate-800/40 border-slate-700/40"
                  }`}
                >
                  <Text className={`text-xs font-semibold ${
                    serviceCategory === cat.value ? "text-white" : theme.primaryText
                  }`}>
                    {cat.label}
                  </Text>
                </Pressable>
              ))}
            </View>

            {servicesLoading ? (
              <Text className={`text-xs ${theme.secondaryText}`}>Loading...</Text>
            ) : servicesList.length === 0 ? (
              <Text className={`text-xs ${theme.secondaryText}`}>No services found nearby</Text>
            ) : (
              servicesList.map((item) => (
                <View
                  key={item.id}
                  className={`rounded-xl border px-3 py-2.5 mb-2 flex-row items-center ${
                    highContrast ? "border-slate-200 bg-slate-50" : "border-slate-700/30 bg-slate-800/30"
                  }`}
                >
                  <Ionicons
                    name={(SERVICE_ICONS[item.category] ?? "medkit") as any}
                    size={18}
                    color={highContrast ? "#0f172a" : "#22d3ee"}
                    style={{ marginRight: 10 }}
                  />
                  <View className="flex-1">
                    <Text className={`text-sm font-semibold ${theme.primaryText}`} numberOfLines={1}>
                      {item.name}
                    </Text>
                    <Text className={`text-[10px] ${theme.secondaryText}`}>
                      {item.category.replace("_", " ")} | {formatDistanceMetres(item.distance_metres)}
                    </Text>
                  </View>
                  <Pressable
                    onPress={() => {
                      closeServicesMode();
                      const dest = item.address ? `${item.name}, ${item.address}` : item.name;
                      void handleSuggestionPress({ label: dest, latitude: item.latitude, longitude: item.longitude });
                    }}
                    className={`rounded-lg px-2.5 py-1.5 ${highContrast ? "bg-slate-900" : "bg-cyan-500"}`}
                  >
                    <Text className="text-white text-[10px] font-bold">Route</Text>
                  </Pressable>
                </View>
              ))
            )}
          </ScrollView>
        ) : reportsListMode ? (
          <ScrollView style={{ maxHeight: 400 }} contentContainerStyle={{ paddingBottom: 8 }} showsVerticalScrollIndicator={false}>
            <View className="flex-row items-center justify-between mb-3">
              <Text className={`font-bold ${theme.primaryText}`}>Nearby reports</Text>
              <Pressable onPress={closeReportsListMode}>
                <Ionicons name="close" size={22} color={highContrast ? "#0f172a" : "#94a3b8"} />
              </Pressable>
            </View>

            {reportsListLoading ? (
              <Text className={`text-xs ${theme.secondaryText}`}>Loading...</Text>
            ) : reportsListItems.length === 0 ? (
              <Text className={`text-xs ${theme.secondaryText}`}>No reports found nearby</Text>
            ) : (
              reportsListItems.map((item) => {
                const isHigh =
                  item.category === "assault" || item.category === "robbery" ||
                  item.category === "harassment" || item.category === "theft" ||
                  item.category === "suspicious activity";
                return (
                  <Pressable
                    key={item.id}
                    onPress={() => {
                      setSelectedReport({
                        category: item.category,
                        summary: item.summary,
                        created_at: item.created_at,
                        latitude: item.latitude,
                        longitude: item.longitude,
                      });
                      setMapFocusTarget({ latitude: item.latitude, longitude: item.longitude });
                      closeReportsListMode();
                    }}
                    className={`rounded-xl border px-3 py-2.5 mb-2 ${
                      highContrast ? "border-slate-200 bg-slate-50" : "border-slate-700/30 bg-slate-800/30"
                    }`}
                  >
                    <View className="flex-row items-center justify-between">
                      <Text className={`text-sm font-semibold ${theme.primaryText}`} numberOfLines={1}>
                        {item.category.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                      </Text>
                      <View className={`rounded-full px-2 py-0.5 ${isHigh ? "bg-rose-500/20" : "bg-amber-500/20"}`}>
                        <Text className={`text-[9px] font-bold ${isHigh ? "text-rose-400" : "text-amber-300"}`}>
                          {isHigh ? "HIGH" : "MEDIUM"}
                        </Text>
                      </View>
                    </View>
                    <Text className={`text-xs mt-1 ${theme.secondaryText}`} numberOfLines={2}>{item.summary}</Text>
                    <Text className={`text-[10px] mt-1 ${theme.secondaryText}`}>
                      {new Date(item.created_at).toLocaleString("en-GB")}
                    </Text>
                  </Pressable>
                );
              })
            )}
          </ScrollView>
        ) : reportMode ? (
          <ScrollView style={{ maxHeight: 400 }} contentContainerStyle={{ paddingBottom: 8 }} showsVerticalScrollIndicator={false}>
            <View className="flex-row items-center justify-between mb-3">
              <Text className={`font-bold ${theme.primaryText}`}>Report an issue</Text>
              <Pressable onPress={closeReportMode}>
                <Ionicons name="close" size={22} color={highContrast ? "#0f172a" : "#94a3b8"} />
              </Pressable>
            </View>

            <Text className={`text-xs mb-2 ${theme.secondaryText}`}>What happened?</Text>
            <View className="flex-row flex-wrap mb-3">
              {ISSUE_OPTIONS.map((option) => (
                <Pressable
                  key={option}
                  onPress={() => setReportIssue(option)}
                  className={`rounded-full border px-3 py-1.5 mr-2 mb-2 ${
                    reportIssue === option
                      ? highContrast ? "bg-slate-900 border-slate-900" : "bg-cyan-500 border-cyan-500"
                      : highContrast ? "bg-slate-100 border-slate-300" : "bg-slate-800/40 border-slate-700/40"
                  }`}
                >
                  <Text className={`text-xs font-semibold ${
                    reportIssue === option ? "text-white" : theme.primaryText
                  }`}>
                    {option}
                  </Text>
                </Pressable>
              ))}
            </View>

            <Text className={`text-xs mb-2 ${theme.secondaryText}`}>Description</Text>
            <View
              className={`rounded-xl border px-3 py-2 mb-3 ${
                highContrast ? "bg-white border-slate-300" : "bg-slate-800/60 border-slate-700/40"
              }`}
            >
              <TextInput
                value={reportDescription}
                onChangeText={setReportDescription}
                placeholder="Please describe what happened"
                placeholderTextColor={highContrast ? "#94a3b8" : "#64748b"}
                className={theme.primaryText}
                multiline
                style={{ minHeight: 60, textAlignVertical: "top" }}
              />
            </View>

            <Text className={`text-xs mb-2 ${theme.secondaryText}`}>Location</Text>
            <View className="flex-row mb-3">
              <Pressable
                onPress={() => {
                  setReportLocation(null);
                  setReportPickingLocation(false);
                }}
                className={`flex-1 mr-2 rounded-xl py-2 items-center border ${
                  !reportLocation && !reportPickingLocation
                    ? highContrast ? "bg-slate-900 border-slate-900" : "bg-cyan-500 border-cyan-500"
                    : highContrast ? "bg-slate-100 border-slate-300" : "bg-slate-800/40 border-slate-700/40"
                }`}
              >
                <Text className={`text-xs font-semibold ${
                  !reportLocation && !reportPickingLocation ? "text-white" : theme.primaryText
                }`}>
                  My location
                </Text>
              </Pressable>
              <Pressable
                onPress={() => setReportPickingLocation(true)}
                className={`flex-1 ml-2 rounded-xl py-2 items-center border ${
                  reportPickingLocation || reportLocation
                    ? highContrast ? "bg-slate-900 border-slate-900" : "bg-cyan-500 border-cyan-500"
                    : highContrast ? "bg-slate-100 border-slate-300" : "bg-slate-800/40 border-slate-700/40"
                }`}
              >
                <Text className={`text-xs font-semibold ${
                  reportPickingLocation || reportLocation ? "text-white" : theme.primaryText
                }`}>
                  {reportPickingLocation ? "Tap the map..." : reportLocation ? "Map pin set" : "Pick on map"}
                </Text>
              </Pressable>
            </View>

            <Pressable
              onPress={submitReport}
              disabled={reportSubmitting}
              className={`rounded-xl py-3 items-center ${reportSubmitting ? "bg-slate-400" : highContrast ? "bg-slate-900" : "bg-cyan-500"}`}
            >
              <Text className="text-white font-bold">
                {reportSubmitting ? "Submitting..." : "Submit report"}
              </Text>
            </Pressable>
          </ScrollView>
        ) : planningRoute ? (
          <View className="items-center py-4">
            <ActivityIndicator size="large" color={highContrast ? "#0f172a" : "#22d3ee"} />
            <Text className={`font-bold mt-3 ${theme.primaryText}`}>Scoring your routes</Text>
            <Text className={`text-xs mt-1 ${theme.secondaryText}`}>
              Checking safety, lighting and accessibility...
            </Text>
          </View>
        ) : routePreview && previewRoute ? (
          <>
            <Text className={`font-bold ${theme.primaryText}`}>
              {routePreview.destination.label ?? "Destination"}
            </Text>

            <ScrollView horizontal showsHorizontalScrollIndicator={false} className="mt-2 -mx-1">
              {routePreview.plan.ranked_routes.map((route) => {
                const isSelected = route.candidate_id === (selectedPreviewId ?? routePreview.plan.selected_route_id);
                return (
                  <Pressable
                    key={route.candidate_id}
                    onPress={() => setSelectedPreviewId(route.candidate_id)}
                    className={`rounded-xl border px-3 py-2 mr-2 ${
                      isSelected
                        ? highContrast ? "border-slate-900 bg-slate-100" : "border-cyan-400/60 bg-cyan-500/10"
                        : highContrast ? "border-slate-200 bg-white" : "border-slate-700/40 bg-slate-800/40"
                    }`}
                    style={{ minWidth: 140 }}
                  >
                    <Text className={`text-xs font-bold ${theme.primaryText}`}>
                      {route.label ?? `Route ${route.rank}`}
                    </Text>
                    <Text className={`text-[10px] mt-0.5 ${theme.secondaryText}`}>
                      {formatDistanceMetres(route.distance_metres)} | {Math.max(1, Math.round(route.duration_seconds / 60))} min
                    </Text>
                    <Text className={`text-[10px] mt-0.5 ${theme.secondaryText}`}>
                      Safety: {Math.round(route.score)}%
                    </Text>
                    {route.navigation?.steps?.some((s: any) => s.mode === "transit") ? (
                      <Text className="text-[10px] mt-0.5 text-purple-400">
                        {route.navigation.steps
                          .filter((s: any) => s.line)
                          .map((s: any) => s.line)
                          .join(" → ")}
                      </Text>
                    ) : null}
                  </Pressable>
                );
              })}
            </ScrollView>

            {previewRoute.navigation?.steps?.length ? (
              <ScrollView style={{ maxHeight: 180 }} className="mt-2 -mx-1 px-1" showsVerticalScrollIndicator={false}>
                {previewRoute.navigation.steps.map((step: any, i: number) => {
                  const isTransit = step.mode === "transit";
                  const mins = Math.max(1, Math.round(step.duration_seconds / 60));
                  return (
                    <View key={i} className={`flex-row items-start py-1.5 ${
                      i > 0 ? `border-t ${highContrast ? "border-slate-200" : "border-slate-700/30"}` : ""
                    }`}>
                      <View className={`h-6 w-6 rounded-full items-center justify-center mt-0.5 ${
                        isTransit
                          ? "bg-purple-500/20"
                          : highContrast ? "bg-slate-200" : "bg-slate-800/60"
                      }`}>
                        <Ionicons
                          name={isTransit ? "bus" : "walk"}
                          size={13}
                          color={isTransit ? "#a855f7" : highContrast ? "#0f172a" : "#06b6d4"}
                        />
                      </View>
                      <View className="flex-1 ml-2">
                        <Text className={`text-xs font-semibold ${theme.primaryText}`}>
                          {isTransit && step.line
                            ? `${step.line} · ${mins} min`
                            : `Walk · ${formatDistanceMetres(step.distance_metres)} · ${mins} min`}
                        </Text>
                        {isTransit && step.from_stop && step.to_stop ? (
                          <Text className={`text-[10px] ${theme.secondaryText}`} numberOfLines={1}>
                            {step.from_stop} → {step.to_stop}
                          </Text>
                        ) : step.instruction ? (
                          <Text className={`text-[10px] ${theme.secondaryText}`} numberOfLines={1}>
                            {step.instruction}
                          </Text>
                        ) : null}
                        {isTransit && step.depart_at ? (
                          <Text className="text-[10px] text-purple-400">
                            Departs {new Date(step.depart_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                          </Text>
                        ) : null}
                      </View>
                    </View>
                  );
                })}
              </ScrollView>
            ) : null}

            {previewRoute.explanation?.summary ? (
              <Text className={`text-xs mt-2 ${theme.secondaryText}`} numberOfLines={2}>
                {previewRoute.explanation.summary}
              </Text>
            ) : null}
            <View className="flex-row mt-3">
              <Pressable
                onPress={handleStartWalk}
                disabled={startingWalk}
                className="mr-2 flex-1 rounded-xl bg-cyan-500 py-3 items-center"
              >
                <Text className="text-slate-950 font-bold">
                  {startingWalk ? "Starting..." : "Go"}
                </Text>
              </Pressable>
              <Pressable
                onPress={cancelRoutePreview}
                className="rounded-xl bg-slate-500 px-4 py-3 items-center"
              >
                <Text className="text-white font-bold">Cancel</Text>
              </Pressable>
            </View>
          </>
        ) : (
          <>
            <Text className={`font-bold mb-2 ${theme.primaryText}`}>Where are you heading?</Text>
            <View
              className={`rounded-xl border px-3 py-2 ${
                highContrast
                  ? "bg-white border-slate-300"
                  : "bg-slate-800/60 border-slate-700/40"
              }`}
            >
              <TextInput
                ref={searchInputRef}
                value={searchText}
                onChangeText={handleSearchChange}
                placeholder="Search for a destination"
                placeholderTextColor={highContrast ? "#94a3b8" : "#64748b"}
                className={theme.primaryText}
                returnKeyType="search"
              />
            </View>
            {planError ? (
              <Text className="text-xs mt-2 text-red-400">{planError}</Text>
            ) : null}
            {suggestions.length > 0 ? (
              <Animated.View
                entering={FadeIn.duration(200)}
                exiting={FadeOut.duration(150)}
                className="mt-2"
              >
                {suggestions.map((s, i) => (
                  <Pressable
                    key={`${s.latitude}-${s.longitude}-${i}`}
                    onPress={() => handleSuggestionPress(s)}
                    className={`rounded-lg px-3 py-2 mb-1 ${
                      highContrast ? "bg-slate-100" : "bg-slate-800/40"
                    }`}
                  >
                    <Text className={`text-sm ${theme.primaryText}`} numberOfLines={1}>
                      {s.label}
                    </Text>
                  </Pressable>
                ))}
              </Animated.View>
            ) : null}
          </>
        )}

        </View>

        {!session && !routePreview && !reportMode && !servicesMode && !reportsListMode && !planningRoute ? (
          <View className="flex-row justify-between mt-3">
            <Pressable
              onPress={openServicesMode}
              className="items-center flex-1"
            >
              <View className={`h-11 w-11 rounded-full items-center justify-center ${
                highContrast ? "bg-slate-100" : "bg-slate-800/60"
              }`}>
                <Ionicons name="medkit" size={20} color={highContrast ? "#0f172a" : "#22d3ee"} />
              </View>
              <Text className={`text-[10px] mt-1 ${theme.secondaryText}`}>Services</Text>
            </Pressable>
            <Pressable
              onPress={() => searchInputRef.current?.focus()}
              className="items-center flex-1"
            >
              <View className={`h-11 w-11 rounded-full items-center justify-center ${
                highContrast ? "bg-slate-100" : "bg-slate-800/60"
              }`}>
                <Ionicons name="navigate" size={20} color={highContrast ? "#0f172a" : "#22d3ee"} />
              </View>
              <Text className={`text-[10px] mt-1 ${theme.secondaryText}`}>Plan route</Text>
            </Pressable>
            <Pressable
              onPress={openReportMode}
              className="items-center flex-1"
            >
              <View className={`h-11 w-11 rounded-full items-center justify-center ${
                highContrast ? "bg-slate-100" : "bg-slate-800/60"
              }`}>
                <Ionicons name="warning" size={20} color={highContrast ? "#0f172a" : "#f59e0b"} />
              </View>
              <Text className={`text-[10px] mt-1 ${theme.secondaryText}`}>Report</Text>
            </Pressable>
            <Pressable
              onPress={openReportsListMode}
              className="items-center flex-1"
            >
              <View className={`h-11 w-11 rounded-full items-center justify-center ${
                highContrast ? "bg-slate-100" : "bg-slate-800/60"
              }`}>
                <Ionicons name="shield-checkmark" size={20} color={highContrast ? "#0f172a" : "#34d399"} />
              </View>
              <Text className={`text-[10px] mt-1 ${theme.secondaryText}`}>Reports</Text>
            </Pressable>
          </View>
        ) : null}
      </Animated.View>
    </View>
  );
}
