import React, { useEffect, useMemo, useState } from "react";
import { FlatList, Pressable, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import * as Location from "expo-location";
import { useAuth } from "@clerk/expo";
import { useQuery, useMutation } from "convex/react";
import { useIsFocused } from "@react-navigation/native";
import { router } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "../../convex/_generated/api";
import { mapCanonicalToConvexCategory } from "../../src/features/reports/categories";
import {
  BIRMINGHAM_DEFAULT_CENTER,
  apiRequest,
  logPrototypeEvent,
  type NearbyReportsResponse,
} from "../../src/lib/api";
import { useConvexTokenAvailability } from "../../src/lib/convexAuth";
import { useRouteSession } from "../../src/features/route/routeSession";
import { useUiPreferences } from "../../src/providers/UIPreferences";
import { env } from "../../src/lib/env";

function formatCategory(value: string) {
  return value
    .split(/[\s_-]+/)
    .map((token) => token.charAt(0).toUpperCase() + token.slice(1))
    .join(" ");
}

type ReportItem = {
  id: string;
  apiReportId: string | undefined;
  type: string;
  description: string;
  location: string;
  latitude: number | null;
  longitude: number | null;
  date: string;
  severity: "HIGH" | "MEDIUM";
};

export default function ReportsListScreen() {
  const insets = useSafeAreaInsets();
  const isFocused = useIsFocused();
  const { highContrast } = useUiPreferences();
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const { hasConvexToken, checked: convexTokenChecked } = useConvexTokenAvailability();
  const convexEnabled = Boolean(env.convexUrl);
  const reports = useQuery(
    api.reports.listReports,
    isLoaded && isSignedIn && convexEnabled ? {} : "skip",
  );
  const upsertReport = useMutation(api.reports.upsertReportFromApi);
  const { setMapFocusTarget } = useRouteSession();
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [backendReports, setBackendReports] = useState<NearbyReportsResponse["items"]>([]);

  const theme = {
    screenBg: highContrast ? "bg-white" : "bg-[#020617]",
    cardBg: highContrast ? "bg-slate-100" : "bg-slate-900/40",
    cardBorder: highContrast ? "border-slate-300" : "border-cyan-500/10",
    textPrimary: highContrast ? "text-slate-950" : "text-white",
    textSecondary: highContrast ? "text-slate-500" : "text-slate-400",
  };

  const reportItems = useMemo<ReportItem[]>(() => {
    if (convexEnabled && reports) {
      return reports.map((report) => ({
        id: String(report._id),
        apiReportId: report.apiReportId,
        type: formatCategory(report.category),
        description: report.description ?? "No description provided",
        location: report.location,
        latitude:
          typeof report.latitude === "number" ? report.latitude : null,
        longitude:
          typeof report.longitude === "number" ? report.longitude : null,
        date: new Date(report.createdAt).toLocaleString("en-GB"),
        severity:
          report.category === "crime" || report.category === "sketchy"
            ? "HIGH"
            : "MEDIUM",
      }));
    }

    return backendReports.map((report) => ({
      id: report.id,
      apiReportId: report.id,
      type: formatCategory(report.category),
      description: report.summary ?? "No description provided",
      location: `${report.latitude.toFixed(5)}, ${report.longitude.toFixed(5)}`,
      latitude: report.latitude,
      longitude: report.longitude,
      date: new Date(report.created_at).toLocaleString("en-GB"),
      severity:
        report.category === "assault" ||
        report.category === "robbery" ||
        report.category === "harassment" ||
        report.category === "theft" ||
        report.category === "suspicious activity"
          ? "HIGH"
          : "MEDIUM",
    }));
  }, [backendReports, convexEnabled, reports]);

  async function resolveSyncCenter() {
    const permission = await Location.requestForegroundPermissionsAsync();
    if (permission.status !== "granted") {
      return BIRMINGHAM_DEFAULT_CENTER;
    }
    try {
      const current = await Location.getCurrentPositionAsync({});
      return {
        latitude: current.coords.latitude,
        longitude: current.coords.longitude,
        label: "Current location",
      };
    } catch {
      return BIRMINGHAM_DEFAULT_CENTER;
    }
  }

  async function reconcileFromBackend() {
    if (!isLoaded || !isSignedIn || syncing) return;
    setSyncError(null);
    setSyncing(true);
    try {
      const center = await resolveSyncCenter();
      const nearby = await apiRequest<NearbyReportsResponse>("/reports/nearby", getToken, {
        query: {
          latitude: center.latitude,
          longitude: center.longitude,
          radius_metres: 2500,
          limit: 50,
        },
      });
      setBackendReports(nearby.items);
      if (!convexEnabled) {
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
          logPrototypeEvent("reports_convex_sync_failed", {
            error: message,
            id: report.id,
          });
        }
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to sync nearby reports.";
      setSyncError(message);
    } finally {
      setSyncing(false);
    }
  }

  useEffect(() => {
    if (!isFocused) return;
    void reconcileFromBackend();
  }, [isFocused, isLoaded, isSignedIn, convexEnabled]);

  const header = useMemo(
    () => (
      <View className="mb-5">
        <Text className={`text-2xl font-bold ${theme.textPrimary}`}>Safety reports</Text>
        <Text className={`text-xs mt-1 ${theme.textSecondary}`}>
          {!convexEnabled
            ? "Backend reports mode (Convex URL unavailable)"
            : !convexTokenChecked
              ? "Connecting to Convex..."
              : hasConvexToken
                ? "Realtime from Convex (authenticated) + backend reconciliation"
                : "Realtime from Convex (anonymous mode) + backend reconciliation"}
        </Text>
        <Pressable
          onPress={reconcileFromBackend}
          className="self-start mt-3 rounded-xl bg-cyan-500 px-3 py-2"
        >
          <Text className="text-slate-950 font-bold text-xs">
            {syncing ? "Syncing..." : "Sync now"}
          </Text>
        </Pressable>
        {syncError ? (
          <Text className="mt-2 text-xs text-red-300">{syncError}</Text>
        ) : null}
      </View>
    ),
    [
      convexTokenChecked,
      convexEnabled,
      hasConvexToken,
      syncError,
      syncing,
      theme.textPrimary,
      theme.textSecondary,
    ],
  );

  return (
    <View className={`flex-1 ${theme.screenBg}`} style={{ paddingTop: insets.top }}>
      <FlatList
        data={reportItems}
        keyExtractor={(item) => item.id}
        ListHeaderComponent={header}
        contentContainerStyle={{ paddingHorizontal: 20, paddingTop: 16, paddingBottom: 120 }}
        ListEmptyComponent={
          <View className={`rounded-2xl border p-4 ${theme.cardBg} ${theme.cardBorder}`}>
            <Text className={`font-semibold ${theme.textPrimary}`}>No reports yet</Text>
            <Text className={`text-xs mt-1 ${theme.textSecondary}`}>
              Submit from the Report tab to see realtime updates here.
            </Text>
          </View>
        }
        renderItem={({ item }) => (
          <View className={`rounded-2xl border p-4 mb-3 ${theme.cardBg} ${theme.cardBorder}`}>
            <View className="flex-row justify-between items-start">
              <Text className={`font-semibold ${theme.textPrimary}`}>{item.type}</Text>
              <View
                className={`rounded-full px-2 py-1 ${
                  item.severity === "HIGH" ? "bg-rose-500/20" : "bg-amber-500/20"
                }`}
              >
                <Text
                  className={`text-[10px] font-bold ${
                    item.severity === "HIGH" ? "text-rose-400" : "text-amber-300"
                  }`}
                >
                  {item.severity}
                </Text>
              </View>
            </View>
            <Text className={`text-sm mt-1 ${theme.textPrimary}`}>{item.description}</Text>
            <Text className={`text-xs mt-1 ${theme.textSecondary}`}>{item.location}</Text>
            <Text className={`text-xs mt-1 ${theme.textSecondary}`}>{item.date}</Text>
            {item.apiReportId ? (
              <Text className={`text-[10px] mt-1 ${theme.textSecondary}`}>
                backend id: {item.apiReportId}
              </Text>
            ) : null}

            {item.latitude !== null && item.longitude !== null ? (
              <Pressable
                onPress={() =>
                  {
                    setMapFocusTarget({
                      latitude: item.latitude as number,
                      longitude: item.longitude as number,
                      label: item.type,
                    });
                    router.push("/(tabs)");
                  }
                }
                className="mt-3 self-start rounded-xl bg-slate-900 px-3 py-2 flex-row items-center"
              >
                <Ionicons name="map-outline" size={14} color="#ffffff" />
                <Text className="ml-2 text-xs text-white font-bold">Focus on map</Text>
              </Pressable>
            ) : null}
          </View>
        )}
      />
    </View>
  );
}
