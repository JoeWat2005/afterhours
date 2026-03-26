import React, { useEffect, useMemo, useRef, useState } from "react";
import { Pressable, ScrollView, Text, TextInput, View } from "react-native";
import Animated, { FadeIn, FadeOut, LinearTransition } from "react-native-reanimated";
import { Ionicons } from "@expo/vector-icons";
import { Link, router } from "expo-router";
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
} from "../../src/lib/api";
import {
  computeRouteProgress,
  flattenGeometryCoordinates,
} from "../../src/features/route/progress";
import { useRouteSession } from "../../src/features/route/routeSession";
import { useConvexTokenAvailability } from "../../src/lib/convexAuth";
import { useUiPreferences } from "../../src/providers/UIPreferences";
import { env } from "../../src/lib/env";

Mapbox.setAccessToken(process.env.EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN ?? "");

const DEFAULT_CENTER: [number, number] = [
  BIRMINGHAM_DEFAULT_CENTER.longitude,
  BIRMINGHAM_DEFAULT_CENTER.latitude,
];
const OFF_ROUTE_THRESHOLD_METRES = 45;
const OFF_ROUTE_SAMPLE_LIMIT = 3;
const HEATMAP_RADIUS_METRES = 2500;
const HEATMAP_CELL_SIZE_METRES = 180;

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
  const { highContrast, routeOptions, lowDataMode } = useUiPreferences();
  const { getToken, isLoaded, isSignedIn } = useAuth();
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
  const [searchText, setSearchText] = useState("");
  const [suggestions, setSuggestions] = useState<GeocodeResult[]>([]);
  const searchTimerRef = useRef<number | null>(null);
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

  // report mode
  const [reportMode, setReportMode] = useState(false);
  const [reportIssue, setReportIssue] = useState<string | null>(null);
  const [reportDescription, setReportDescription] = useState("");
  const [reportLocation, setReportLocation] = useState<Coordinates | null>(null);
  const [reportPickingLocation, setReportPickingLocation] = useState(false);
  const [reportSubmitting, setReportSubmitting] = useState(false);

  function openReportMode() {
    setReportMode(true);
    setReportIssue(null);
    setReportDescription("");
    setReportLocation(null);
    setReportPickingLocation(false);
  }

  function closeReportMode() {
    setReportMode(false);
    setReportPickingLocation(false);
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

    setPlanningRoute(true);
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
          alternatives: lowDataMode ? 1 : 3,
          ...routeToggles,
        },
      });
      setRoutePreview({ plan, origin, destination });
      setSelectedPreviewId(plan.selected_route_id);

      mapCameraRef.current?.fitBounds(
        [destination.longitude, destination.latitude],
        [origin.longitude, origin.latitude],
        [80, 80, 300, 80],
        500,
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Route planning failed";
      setPlanError(msg);
      showToast(msg);
      logPrototypeEvent("route_preview_failed", { error: msg });
    } finally {
      setPlanningRoute(false);
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

      startSession({
        journeyId: journeyId ?? null,
        origin: routePreview.origin,
        destination: routePreview.destination,
        selectedRouteId: previewRoute.candidate_id,
        rankedRoutes: routePreview.plan.ranked_routes,
      });
      setRoutePreview(null);
    } catch {
      // handled by session
    } finally {
      setStartingWalk(false);
    }
  }

  function cancelRoutePreview() {
    setRoutePreview(null);
    setSelectedPreviewId(null);
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
    if (syncingReports || !isLoaded || !isSignedIn) return;
    setSyncingReports(true);
    try {
      const center =
        currentLocation ?? session?.lastLocation ?? BIRMINGHAM_DEFAULT_CENTER;
      const nearby = await apiRequest<NearbyReportsResponse>("/reports/nearby", getToken, {
        query: {
          latitude: center.latitude,
          longitude: center.longitude,
          radius_metres: 2500,
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
    if (!heatmapEnabled || syncingHeatmap || !isLoaded || !isSignedIn) return;
    setHeatmapError(null);
    setSyncingHeatmap(true);
    try {
      const center =
        currentLocation ?? session?.lastLocation ?? BIRMINGHAM_DEFAULT_CENTER;
      const payload = await apiRequest<HeatmapResponse>("/heatmap", getToken, {
        query: {
          latitude: center.latitude,
          longitude: center.longitude,
          radius_metres: HEATMAP_RADIUS_METRES,
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

  function handleMapIdle(state: { properties: { center: number[] } }) {
    const [lng, lat] = state.properties.center;
    if (lng === undefined || lat === undefined) return;
    void reverseGeocode(lat, lng).then(setAreaName);
  }

  useEffect(() => {
    if (!session || !currentLocation || session.status !== "active") return;
    if (routeCoordinates.length < 2) return;

    const progress = computeRouteProgress(
      currentLocation,
      routeCoordinates,
      session.activeRoute.duration_seconds,
      session.activeRoute.navigation?.steps ?? [],
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
      const newCount = session.offRouteSamples + 1;
      incrementOffRouteSamples();
      if (newCount >= OFF_ROUTE_SAMPLE_LIMIT && !session.rerouting) {
        void rerouteFromCurrentPosition(currentLocation);
      }
    } else {
      resetOffRouteSamples();
    }

    if (progress.remainingDistanceMetres <= 20) {
      setWalkStatus("completed");
      clearSession();
    }
  }, [
    clearSession,
    currentLocation,
    incrementOffRouteSamples,
    resetOffRouteSamples,
    routeCoordinates,
    session,
    setWalkStatus,
    updateProgress,
  ]);

  useEffect(() => {
    if (!mapFocusTarget) return;
    mapCameraRef.current?.setCamera({
      centerCoordinate: [mapFocusTarget.longitude, mapFocusTarget.latitude],
      zoomLevel: 14,
      animationDuration: 700,
    });
    setMapFocusTarget(null); //should i change the timing?
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
    session?.lastLocation,
    convexEnabled,
    heatmapEnabled,
  ]);

  const currentStepInstruction =
    session?.activeRoute.navigation?.steps?.[session.currentStepIndex]?.instruction ??
    "Follow the selected route";

  const mapEnabled = Boolean(process.env.EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN);

  return (
    <View className="flex-1 bg-slate-950">
      {mapEnabled ? (
        <Mapbox.MapView
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
                    10, 60,
                    13, 80,
                    16, 100,
                    18, 120,
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
                    10, 0.8,
                    14, 1.2,
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
                    10, 0.7,
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
                  lineColor: highContrast ? "#0f172a" : "#22d3ee",
                  lineWidth: 5,
                  lineOpacity: 0.9,
                }}
              />
            </Mapbox.ShapeSource>
          ) : null}

          {showReportPins ? (
            <Mapbox.ShapeSource id="reports-source" shape={reportFeatures}>
              <Mapbox.CircleLayer
                id="report-points"
                style={{
                  circleRadius: 5,
                  circleColor: highContrast ? "#b91c1c" : "#f43f5e",
                  circleStrokeColor: "#ffffff",
                  circleStrokeWidth: 1,
                  circleOpacity: 0.85,
                }}
              />
            </Mapbox.ShapeSource>
          ) : null}

          {showCrimePins ? (
            <Mapbox.ShapeSource id="crime-pins-source" shape={crimePinFeatures}>
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
              <Mapbox.PointAnnotation
                id="origin-marker"
                coordinate={[session.origin.longitude, session.origin.latitude]}
              >
                <View className="h-3 w-3 rounded-full bg-emerald-500" />
              </Mapbox.PointAnnotation>
              <Mapbox.PointAnnotation
                id="destination-marker"
                coordinate={[session.destination.longitude, session.destination.latitude]}
              >
                <View className="h-3 w-3 rounded-full bg-rose-500" />
              </Mapbox.PointAnnotation>
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
                          ? (highContrast ? "#0f172a" : "#22d3ee")
                          : (highContrast ? "#94a3b8" : "#64748b"),
                        lineWidth: isSelected ? 5 : 3,
                        lineOpacity: isSelected ? 0.9 : 0.4,
                      }}
                    />
                  </Mapbox.ShapeSource>
                );
              })}
              {routePreview ? (
                <>
                  <Mapbox.PointAnnotation
                    id="preview-origin"
                    coordinate={[routePreview.origin.longitude, routePreview.origin.latitude]}
                  >
                    <View className="h-3 w-3 rounded-full bg-emerald-500 border border-white" />
                  </Mapbox.PointAnnotation>
                  <Mapbox.PointAnnotation
                    id="preview-destination"
                    coordinate={[routePreview.destination.longitude, routePreview.destination.latitude]}
                  >
                    <View className="h-3 w-3 rounded-full bg-rose-500 border border-white" />
                  </Mapbox.PointAnnotation>
                </>
              ) : null}
            </>
          ) : null}

          {currentLocation ? (
            <Mapbox.PointAnnotation
              id="current-marker"
              coordinate={[currentLocation.longitude, currentLocation.latitude]}
            >
              <View className="h-4 w-4 rounded-full bg-blue-500 border border-white" />
            </Mapbox.PointAnnotation>
          ) : null}

          {reportMode && reportLocation ? (
            <Mapbox.PointAnnotation
              id="report-pin"
              coordinate={[reportLocation.longitude, reportLocation.latitude]}
            >
              <View className="h-4 w-4 rounded-full bg-amber-500 border-2 border-white" />
            </Mapbox.PointAnnotation>
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
            className={`h-10 w-10 items-center justify-center rounded-full mb-2 ${
              heatmapEnabled
                ? "bg-cyan-500"
                : highContrast ? "bg-white/90" : "bg-slate-900/70"
            }`}
          >
            <Ionicons
              name="flame"
              size={20}
              color={heatmapEnabled ? "#ffffff" : highContrast ? "#64748b" : "#94a3b8"}
            />
          </Pressable>
          <Pressable
            onPress={() => setShowCrimePins((prev) => !prev)}
            className={`h-10 w-10 items-center justify-center rounded-full mb-2 ${
              showCrimePins
                ? "bg-blue-500"
                : highContrast ? "bg-white/90" : "bg-slate-900/70"
            }`}
          >
            <Ionicons
              name="shield-outline"
              size={18}
              color={showCrimePins ? "#ffffff" : highContrast ? "#64748b" : "#94a3b8"}
            />
          </Pressable>
          <Pressable
            onPress={() => setShowReportPins((prev) => !prev)}
            className={`h-10 w-10 items-center justify-center rounded-full ${
              showReportPins
                ? "bg-rose-500"
                : highContrast ? "bg-white/90" : "bg-slate-900/70"
            }`}
          >
            <Ionicons
              name="flag-outline"
              size={18}
              color={showReportPins ? "#ffffff" : highContrast ? "#64748b" : "#94a3b8"}
            />
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

      <Animated.View
        layout={LinearTransition.duration(250)}
        className={`absolute left-0 right-0 bottom-0 rounded-t-3xl border-t px-5 pt-4 ${theme.bottomPanel}`}
        style={{ paddingBottom: Math.max(insets.bottom, 16) }}
      >
        {permissionState === "denied" ? (
          <Text className="text-xs text-amber-300 mb-2">
            Location denied. Route can still be viewed, but live progress is disabled.
          </Text>
        ) : null}
        {locationError ? (
          <Text className="text-xs text-red-300 mb-2">{locationError}</Text>
        ) : null}

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
                <Text className="text-white font-bold">End walk</Text>
              </Pressable>
            </View>
          </>
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
                  </Pressable>
                );
              })}
            </ScrollView>

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
                  {startingWalk ? "Starting..." : "Start walk"}
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
                value={searchText}
                onChangeText={handleSearchChange}
                placeholder="Search for a destination"
                placeholderTextColor={highContrast ? "#94a3b8" : "#64748b"}
                className={theme.primaryText}
                returnKeyType="search"
              />
            </View>
            {planningRoute ? (
              <Text className={`text-xs mt-2 ${theme.secondaryText}`}>Finding safest route...</Text>
            ) : null}
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
        {!session && !routePreview && !reportMode ? (
          <View className="flex-row justify-between mt-3">
            <Pressable
              onPress={() => router.push("/(tabs)/services")}
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
              onPress={() => router.push("/(tabs)/route")}
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
              onPress={() => router.push("/(tabs)/report_list")}
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
