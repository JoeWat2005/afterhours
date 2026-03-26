import React, { useEffect, useMemo, useRef, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Link, router } from "expo-router";
import { useAuth } from "@clerk/expo";
import { useIsFocused } from "@react-navigation/native";
import { useMutation, useQuery } from "convex/react";
import * as Location from "expo-location";
import Mapbox from "@rnmapbox/maps";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "../../convex/_generated/api";
import { mapCanonicalToConvexCategory } from "../../src/features/reports/categories";
import {
  BIRMINGHAM_DEFAULT_CENTER,
  apiRequest,
  formatDistanceMetres,
  logPrototypeEvent,
  type Coordinates,
  type HeatmapResponse,
  type NearbyReportsResponse,
  type RoutePlanResponse,
  type RoutePlanRequest,
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

const CITY_BOUNDS = {
  ne: [-1.7088, 52.531] as [number, number],
  sw: [-2.0336, 52.381] as [number, number],
};
const DEFAULT_CENTER: [number, number] = [
  BIRMINGHAM_DEFAULT_CENTER.longitude,
  BIRMINGHAM_DEFAULT_CENTER.latitude,
];
const OFF_ROUTE_THRESHOLD_METRES = 45;
const OFF_ROUTE_SAMPLE_LIMIT = 3;
const HEATMAP_RADIUS_METRES = 2500;
const HEATMAP_CELL_SIZE_METRES = 180;

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
  } = useRouteSession();

  const [permissionState, setPermissionState] = useState<PermissionState>("idle");
  const [currentLocation, setCurrentLocation] = useState<Coordinates | null>(null);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [syncingReports, setSyncingReports] = useState(false);
  const [syncingHeatmap, setSyncingHeatmap] = useState(false);
  const [apiReports, setApiReports] = useState<NearbyReportsResponse["items"]>([]);
  const [heatmapEnabled, setHeatmapEnabled] = useState(true);
  const [heatmapError, setHeatmapError] = useState<string | null>(null);
  const [heatmapData, setHeatmapData] = useState<HeatmapResponse | null>(null);
  const mapCameraRef = useRef<Mapbox.Camera>(null);
  const reportSyncTimerRef = useRef<number | null>(null);
  const heatmapSyncTimerRef = useRef<number | null>(null);
  const locationWatcherRef = useRef<Location.LocationSubscription | null>(null);

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
          id: item.cell_id,
          risk_score: item.risk_score,
          source_count: item.source_count,
        },
        geometry: {
          type: "Polygon" as const,
          coordinates: [[
            [item.bounds.min_longitude, item.bounds.min_latitude],
            [item.bounds.max_longitude, item.bounds.min_latitude],
            [item.bounds.max_longitude, item.bounds.max_latitude],
            [item.bounds.min_longitude, item.bounds.max_latitude],
            [item.bounds.min_longitude, item.bounds.min_latitude],
          ]],
        },
      })),
    };
  }, [heatmapData]);

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
        >
          <Mapbox.Camera
            ref={mapCameraRef}
            zoomLevel={12}
            centerCoordinate={
              currentLocation
                ? [currentLocation.longitude, currentLocation.latitude]
                : DEFAULT_CENTER
            }
            maxBounds={CITY_BOUNDS}
          />

          {heatmapEnabled ? (
            <Mapbox.ShapeSource id="heatmap-source" shape={heatmapFeatures}>
              <Mapbox.FillLayer
                id="heatmap-layer"
                style={{
                  fillColor: [
                    "interpolate",
                    ["linear"],
                    ["get", "risk_score"],
                    0,
                    highContrast ? "#84cc16" : "#22c55e",
                    3,
                    highContrast ? "#f59e0b" : "#f59e0b",
                    8,
                    highContrast ? "#dc2626" : "#ef4444",
                  ] as unknown as string,
                  fillOpacity: 0.28,
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

          {currentLocation ? (
            <Mapbox.PointAnnotation
              id="current-marker"
              coordinate={[currentLocation.longitude, currentLocation.latitude]}
            >
              <View className="h-4 w-4 rounded-full bg-blue-500 border border-white" />
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
        className={`absolute left-4 right-4 rounded-2xl border px-4 py-3 ${theme.topPanel}`}
        style={{ top: insets.top + 8 }}
      >
        <View className="flex-row items-center justify-between">
          <View>
            <Text className={`font-bold ${theme.primaryText}`}>AfterHours live walk</Text>
            <Text className={`text-xs ${theme.secondaryText}`}>
              {!convexEnabled
                ? `${apiReports.length} reports (API only)`
                : !convexTokenChecked
                  ? "Connecting to Convex..."
                  : hasConvexToken
                    ? reports
                      ? `${reports.length} realtime reports (authenticated)`
                      : "Loading realtime reports..."
                    : `${apiReports.length} reports (Convex anonymous)`}
            </Text>
          </View>
          <View className="flex-row">
            <Link href="/profile" asChild>
              <Pressable className="mr-2 h-10 w-10 items-center justify-center rounded-full bg-slate-800/40">
                <Ionicons name="person-outline" size={19} color="white" />
              </Pressable>
            </Link>
            <Link href="/settings" asChild>
              <Pressable className="h-10 w-10 items-center justify-center rounded-full bg-slate-800/40">
                <Ionicons name="settings-outline" size={19} color="white" />
              </Pressable>
            </Link>
          </View>
        </View>
        <View className="flex-row mt-2">
          <Pressable
            onPress={() => setHeatmapEnabled((previous) => !previous)}
            className="rounded-full bg-slate-800/40 px-3 py-1 mr-2"
          >
            <Text className="text-xs text-white font-semibold">
              {heatmapEnabled ? "Heatmap: on" : "Heatmap: off"}
            </Text>
          </Pressable>
          <Pressable
            onPress={() => void syncHeatmap()}
            className="rounded-full bg-slate-800/40 px-3 py-1"
          >
            <Text className="text-xs text-white font-semibold">
              {syncingHeatmap ? "Heatmap syncing..." : "Refresh heatmap"}
            </Text>
          </Pressable>
        </View>
      </View>

      <View
        className={`absolute left-4 right-4 rounded-3xl border px-4 py-4 ${theme.bottomPanel}`}
        style={{ bottom: Math.max(insets.bottom, 14) + 84 }}
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
        ) : (
          <>
            <Text className={`font-bold ${theme.primaryText}`}>No active walk</Text>
            <Text className={`text-xs mt-1 ${theme.secondaryText}`}>
              Plan a route from the Route tab and tap Start walk.
            </Text>
            <Pressable
              onPress={() => router.push("/(tabs)/route")}
              className="mt-3 rounded-xl bg-cyan-500 px-4 py-2 self-start"
            >
              <Text className="font-bold text-slate-950">Plan route</Text>
            </Pressable>
          </>
        )}
        <Text className={`text-[10px] mt-3 ${theme.secondaryText}`}>
          {syncingReports
            ? "Syncing nearby reports..."
            : convexEnabled
              ? hasConvexToken
                ? "Realtime sync active (authenticated)"
                : "Realtime sync active (anonymous)"
              : "API sync active (Convex unavailable)"}
        </Text>
        {heatmapError ? (
          <Text className="text-[10px] mt-1 text-red-300">{heatmapError}</Text>
        ) : (
          <Text className={`text-[10px] mt-1 ${theme.secondaryText}`}>
            {heatmapEnabled
              ? syncingHeatmap
                ? "Heatmap syncing..."
                : heatmapData?.items?.length
                  ? `${heatmapData.items.length} heatmap cells loaded`
                  : "Heatmap active (no cells in current radius)"
              : "Heatmap hidden"}
          </Text>
        )}
      </View>
    </View>
  );
}
