import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import { useAuth } from "@clerk/expo";
import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";
import * as Location from "expo-location";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import {
  BIRMINGHAM_DEFAULT_CENTER,
  apiRequest,
  formatDistanceMetres,
  geocodePlace,
  logPrototypeEvent,
  type Coordinates,
  type JourneyResponse,
  type RankedRoute,
  type RoutePlanRequest,
  type RoutePlanResponse,
} from "../../src/lib/api";
import { useRouteSession } from "../../src/features/route/routeSession";
import { useUiPreferences } from "../../src/providers/UIPreferences";

function formatDuration(seconds: number) {
  const minutes = Math.max(1, Math.round(seconds / 60));
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return remainder === 0 ? `${hours} hr` : `${hours} hr ${remainder} min`;
}

function getSelectedRoute(
  selectedRouteId: string | null,
  rankedRoutes: RankedRoute[],
) {
  if (!selectedRouteId) return null;
  return rankedRoutes.find((route) => route.candidate_id === selectedRouteId) ?? null;
}

function toRadians(value: number) {
  return (value * Math.PI) / 180;
}

function distanceMetres(
  a: { latitude: number; longitude: number },
  b: { latitude: number; longitude: number },
) {
  const earthRadius = 6_371_000;
  const dLat = toRadians(b.latitude - a.latitude);
  const dLon = toRadians(b.longitude - a.longitude);
  const lat1 = toRadians(a.latitude);
  const lat2 = toRadians(b.latitude);
  const sinLat = Math.sin(dLat / 2);
  const sinLon = Math.sin(dLon / 2);
  const haversine =
    sinLat * sinLat + Math.cos(lat1) * Math.cos(lat2) * sinLon * sinLon;
  return 2 * earthRadius * Math.asin(Math.sqrt(haversine));
}

const MAX_LOCAL_WALK_DISTANCE_METRES = 50_000;

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

export default function RouteScreen() {
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{ destination?: string }>();
  const { highContrast, routeOptions, lowDataMode } = useUiPreferences();
  const { getToken } = useAuth();
  const { startSession } = useRouteSession();

  const [originLabel, setOriginLabel] = useState("Current location");
  const [destinationText, setDestinationText] = useState(params.destination ?? "");

  // pick up destination from search bar on the map tab
  useEffect(() => {
    if (params.destination) {
      setDestinationText(params.destination);
    }
  }, [params.destination]);
  const [planning, setPlanning] = useState(false);
  const [startingWalk, setStartingWalk] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<RoutePlanResponse | null>(null);
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);
  const [resolvedOrigin, setResolvedOrigin] = useState<Coordinates | null>(null);
  const [resolvedDestination, setResolvedDestination] = useState<Coordinates | null>(null);
  const [journeyId, setJourneyId] = useState<string | null>(null);

  const selectedRoute = useMemo(
    () => getSelectedRoute(selectedRouteId, plan?.ranked_routes ?? []),
    [plan?.ranked_routes, selectedRouteId],
  );

  const theme = {
    screenBg: highContrast ? "bg-white" : "bg-[#020617]",
    cardBg: highContrast ? "bg-slate-100" : "bg-slate-900/40",
    cardBorder: highContrast ? "border-slate-300" : "border-cyan-500/20",
    textPrimary: highContrast ? "text-slate-950" : "text-white",
    textSecondary: highContrast ? "text-slate-500" : "text-slate-400",
    inputBg: highContrast ? "bg-white" : "bg-slate-900",
    accentBg: highContrast ? "bg-slate-900" : "bg-cyan-500",
    accentText: "text-white",
  };

  async function resolveOriginFromDevice(): Promise<Coordinates> {
    const permission = await Location.requestForegroundPermissionsAsync();
    if (permission.status !== "granted") {
      logPrototypeEvent("route_origin_permission_denied", {
        status: permission.status,
      });
      return {
        ...BIRMINGHAM_DEFAULT_CENTER,
        label: "Birmingham (location denied)",
      };
    }

    try {
      const current = await Location.getCurrentPositionAsync({});
      return {
        latitude: current.coords.latitude,
        longitude: current.coords.longitude,
        label: "Current location",
      };
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Current location unavailable.";
      logPrototypeEvent("route_origin_unavailable", { error: message });
    }

    try {
      const lastKnown = await Location.getLastKnownPositionAsync();
      if (lastKnown) {
        return {
          latitude: lastKnown.coords.latitude,
          longitude: lastKnown.coords.longitude,
          label: "Last known location",
        };
      }
    } catch {
      // fall through to default
    }

    return {
      ...BIRMINGHAM_DEFAULT_CENTER,
      label: "Birmingham (couldn't get location)",
    };
  }

  async function planRoute() {
    if (planning) return;
    setPlanning(true);
    setError(null);
    setJourneyId(null);

    try {
      const originCandidate = await resolveOriginFromDevice();
      const destinationResults = await geocodePlace(destinationText, {
        limit: 6,
        proximity: {
          latitude: originCandidate.latitude,
          longitude: originCandidate.longitude,
        },
      });

      const destinationCandidate = destinationResults
        .map((candidate) => ({
          candidate,
          distance: distanceMetres(originCandidate, candidate),
        }))
        .sort((a, b) => a.distance - b.distance)
        .map(({ candidate }) => candidate)[0];

      if (!destinationCandidate) {
        throw new Error("Could not resolve destination.");
      }

      const beelineDistanceMetres = distanceMetres(originCandidate, destinationCandidate);
      if (beelineDistanceMetres > MAX_LOCAL_WALK_DISTANCE_METRES) {
        throw new Error(
          "Destination is too far from your current location for a walking route. Try a closer destination.",
        );
      }

      const routeToggles = buildRoutePlanningToggles(routeOptions);
      const payloadBody: RoutePlanRequest = {
        origin: {
          latitude: originCandidate.latitude,
          longitude: originCandidate.longitude,
          label: originCandidate.label,
        },
        destination: {
          latitude: destinationCandidate.latitude,
          longitude: destinationCandidate.longitude,
          label: destinationCandidate.label,
        },
        depart_at: new Date().toISOString(),
        alternatives: lowDataMode ? 1 : 3,
        ...routeToggles,
      };

      const payload = await apiRequest<RoutePlanResponse>("/routes/plan", getToken, {
        method: "POST",
        requireAuth: false,
        body: payloadBody,
      });

      setPlan(payload);
      setSelectedRouteId(payload.selected_route_id);
      setResolvedOrigin({
        latitude: originCandidate.latitude,
        longitude: originCandidate.longitude,
        label: originCandidate.label,
      });
      setOriginLabel(
        `${originCandidate.label ?? "Current location"} (${originCandidate.latitude.toFixed(5)}, ${originCandidate.longitude.toFixed(5)})`,
      );
      setResolvedDestination({
        latitude: destinationCandidate.latitude,
        longitude: destinationCandidate.longitude,
        label: destinationCandidate.label,
      });
    } catch (requestError) {
      const message =
        requestError instanceof Error ? requestError.message : "Failed to plan route.";
      logPrototypeEvent("route_plan_failed", {
        error: message,
      });
      setPlan(null);
      setSelectedRouteId(null);
      setError(message);
    } finally {
      setPlanning(false);
    }
  }

  async function startWalk() {
    if (!plan || !selectedRoute || !resolvedOrigin || !resolvedDestination) {
      return;
    }
    if (startingWalk) return;

    setStartingWalk(true);
    setError(null);
    try {
      let persistedJourneyId = journeyId;
      if (!persistedJourneyId) {
        try {
          const persistedJourney = await apiRequest<JourneyResponse>("/journeys", getToken, {
            method: "POST",
            body: {
              origin_label: resolvedOrigin.label ?? "Current location",
              destination_label: resolvedDestination.label ?? destinationText,
              selected_route_id: selectedRoute.candidate_id,
              ranked_routes: plan.ranked_routes,
            },
          });
          persistedJourneyId = persistedJourney.id;
          setJourneyId(persistedJourney.id);
        } catch (journeyError) {
          const message =
            journeyError instanceof Error
              ? journeyError.message
              : "Could not save journey.";
          logPrototypeEvent("journey_persist_failed", {
            error: message,
          });
        }
      }

      startSession({
        journeyId: persistedJourneyId,
        origin: resolvedOrigin,
        destination: resolvedDestination,
        selectedRouteId: selectedRoute.candidate_id,
        rankedRoutes: plan.ranked_routes,
      });
      router.push("/(tabs)");
    } catch (startError) {
      const message =
        startError instanceof Error ? startError.message : "Failed to start walk.";
      setError(message);
    } finally {
      setStartingWalk(false);
    }
  }

  return (
    <View className={`flex-1 ${theme.screenBg}`} style={{ paddingTop: insets.top }}>
      <ScrollView contentContainerStyle={{ paddingBottom: 120 }} className="px-6">
        <View className="mt-5 mb-5">
          <Text className={`text-2xl font-bold ${theme.textPrimary}`}>Plan safe route</Text>
          <Text className={`mt-1 ${theme.textSecondary}`}>
            Choose a route, then start live walk mode.
          </Text>
        </View>

        <Text className={`text-xs font-bold uppercase mb-2 ${theme.textSecondary}`}>From</Text>
        <View className={`rounded-2xl border px-4 py-4 ${theme.cardBg} ${theme.cardBorder}`}>
          <Text className={theme.textPrimary}>{originLabel}</Text>
          <Text className={`mt-1 text-xs ${theme.textSecondary}`}>
            Origin always uses emulator/device location when planning.
          </Text>
        </View>

        <Text className={`text-xs font-bold uppercase mt-4 mb-2 ${theme.textSecondary}`}>To</Text>
        <View className={`rounded-2xl border px-4 py-3 ${theme.inputBg} ${theme.cardBorder}`}>
          <TextInput
            value={destinationText}
            onChangeText={setDestinationText}
            placeholder="Destination"
            placeholderTextColor={highContrast ? "#64748b" : "#475569"}
            className={theme.textPrimary}
          />
        </View>

        <Pressable
          onPress={planRoute}
          disabled={planning}
          className={`mt-5 rounded-2xl py-4 items-center ${theme.accentBg}`}
        >
          {planning ? (
            <ActivityIndicator color="#ffffff" />
          ) : (
            <Text className={`font-bold ${theme.accentText}`}>Find routes</Text>
          )}
        </Pressable>

        {error ? (
          <View
            className={`mt-4 rounded-2xl border p-4 ${
              highContrast
                ? "border-red-300 bg-red-100"
                : "border-red-500/40 bg-red-500/10"
            }`}
          >
            <Text className={highContrast ? "text-red-800" : "text-red-200"}>{error}</Text>
          </View>
        ) : null}

        {plan ? (
          <View className="mt-6">
            <Text className={`text-sm font-bold uppercase mb-3 ${theme.textSecondary}`}>
              Ranked routes
            </Text>

            {plan.ranked_routes.map((route) => {
              const isSelected = route.candidate_id === selectedRouteId;
              return (
                <Pressable
                  key={route.candidate_id}
                  onPress={() => setSelectedRouteId(route.candidate_id)}
                  className={`rounded-2xl border p-4 mb-3 ${
                    isSelected
                      ? highContrast
                        ? "border-slate-900 bg-slate-200"
                        : "border-cyan-400/60 bg-cyan-500/10"
                      : `${theme.cardBg} ${theme.cardBorder}`
                  }`}
                >
                  <View className="flex-row items-center justify-between">
                    <Text className={`font-semibold ${theme.textPrimary}`}>
                      #{route.rank} {route.label ?? route.candidate_id}
                    </Text>
                    <View className="flex-row items-center">
                      <Ionicons
                        name={isSelected ? "checkmark-circle" : "ellipse-outline"}
                        size={16}
                        color={highContrast ? "#0f172a" : "#22d3ee"}
                      />
                      <Text className={`ml-2 text-xs font-bold ${theme.textPrimary}`}>
                        {Math.round(route.score)}%
                      </Text>
                    </View>
                  </View>
                  <Text className={`text-xs mt-1 ${theme.textSecondary}`}>
                    {formatDistanceMetres(route.distance_metres)} |{" "}
                    {formatDuration(route.duration_seconds)}
                  </Text>
                  <Text className={`text-xs mt-1 ${theme.textSecondary}`}>
                    {route.explanation.summary}
                  </Text>
                </Pressable>
              );
            })}

            <Pressable
              onPress={startWalk}
              disabled={!selectedRoute || startingWalk}
              className={`mt-3 rounded-2xl py-4 items-center ${
                selectedRoute ? theme.accentBg : "bg-slate-400"
              }`}
            >
              {startingWalk ? (
                <ActivityIndicator color="#ffffff" />
              ) : (
                <Text className={`font-bold ${theme.accentText}`}>Start walk</Text>
              )}
            </Pressable>
            {journeyId ? (
              <Text className={`text-xs mt-2 ${theme.textSecondary}`}>
                Journey saved ({journeyId.slice(0, 8)}...)
              </Text>
            ) : null}
          </View>
        ) : null}
      </ScrollView>
    </View>
  );
}
