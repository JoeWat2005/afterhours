import React, { useEffect, useMemo, useState } from "react";
import { FlatList, Pressable, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import * as Location from "expo-location";
import { router } from "expo-router";
import { useAuth } from "@clerk/expo";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import {
  BIRMINGHAM_DEFAULT_CENTER,
  apiRequest,
  formatDistanceMetres,
  type NearbyServicesResponse,
  type ServiceCategory,
} from "../../src/lib/api";
// Previous flow reference:
// import { useRouteSession } from "../../src/features/route/routeSession";
import { useUiPreferences } from "../../src/providers/UIPreferences";

type CategoryOption = {
  label: string;
  value: ServiceCategory | "all";
};

const CATEGORY_OPTIONS: CategoryOption[] = [
  { label: "All", value: "all" },
  { label: "Hospital", value: "hospital" },
  { label: "Police", value: "police" },
  { label: "Fire", value: "fire_station" },
  { label: "Ambulance", value: "ambulance" },
];

export default function ServicesScreen() {
  const insets = useSafeAreaInsets();
  const { getToken } = useAuth();
  // Previous flow reference:
  // const { setMapFocusTarget } = useRouteSession();
  const { highContrast } = useUiPreferences();
  const [selectedCategory, setSelectedCategory] = useState<ServiceCategory | "all">(
    "all",
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [locationLabel, setLocationLabel] = useState("Birmingham default");
  const [services, setServices] = useState<NearbyServicesResponse["items"]>([]);
  const [position, setPosition] = useState(BIRMINGHAM_DEFAULT_CENTER);

  const theme = {
    screenBg: highContrast ? "bg-white" : "bg-[#020617]",
    cardBg: highContrast ? "bg-slate-100" : "bg-slate-900/40",
    cardBorder: highContrast ? "border-slate-300" : "border-cyan-500/20",
    textPrimary: highContrast ? "text-slate-950" : "text-white",
    textSecondary: highContrast ? "text-slate-500" : "text-slate-400",
    accentBg: highContrast ? "bg-slate-900" : "bg-cyan-500",
  };

  async function resolveUserLocation() {
    const permission = await Location.requestForegroundPermissionsAsync();
    if (permission.status !== "granted") {
      setLocationLabel("Birmingham default (permission denied)");
      setPosition(BIRMINGHAM_DEFAULT_CENTER);
      return BIRMINGHAM_DEFAULT_CENTER;
    }

    try {
      const current = await Location.getCurrentPositionAsync({});
      const resolved = {
        latitude: current.coords.latitude,
        longitude: current.coords.longitude,
        label: "Your location",
      };
      setLocationLabel("Your current location");
      setPosition(resolved);
      return resolved;
    } catch {
      setLocationLabel("Birmingham default (location unavailable)");
      setPosition(BIRMINGHAM_DEFAULT_CENTER);
      return BIRMINGHAM_DEFAULT_CENTER;
    }
  }

  async function loadServices() {
    setLoading(true);
    setError(null);
    try {
      const center = await resolveUserLocation();
      const response = await apiRequest<NearbyServicesResponse>("/services/nearby", getToken, {
        query: {
          latitude: center.latitude,
          longitude: center.longitude,
          category: selectedCategory === "all" ? undefined : selectedCategory,
          radius_metres: 8_000,
          limit: 30,
        },
      });
      setServices(response.items);
      if (!response.items.length) {
        setError("No services found in this radius. Try another category.");
      }
    } catch (loadError) {
      const message =
        loadError instanceof Error ? loadError.message : "Failed to load services.";
      setServices([]);
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadServices();
  }, [selectedCategory]);

  const listHeader = useMemo(
    () => (
      <View className="mb-4">
        <Text className={`text-2xl font-bold ${theme.textPrimary}`}>Nearby services</Text>
        <Text className={`text-xs mt-1 ${theme.textSecondary}`}>
          Source: backend `/v1/services/nearby` | {locationLabel}
        </Text>

        <View className="flex-row mt-3 mb-2">
          {CATEGORY_OPTIONS.map((option) => {
            const active = option.value === selectedCategory;
            return (
              <Pressable
                key={option.value}
                onPress={() => setSelectedCategory(option.value)}
                className={`mr-2 rounded-full border px-3 py-2 ${
                  active
                    ? highContrast
                      ? "bg-slate-900 border-slate-900"
                      : "bg-cyan-500 border-cyan-500"
                    : `${theme.cardBg} ${theme.cardBorder}`
                }`}
              >
                <Text
                  className={`text-xs font-bold ${
                    active ? "text-white" : theme.textPrimary
                  }`}
                >
                  {option.label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <Pressable
          onPress={loadServices}
          className={`self-start mt-1 rounded-xl px-4 py-2 ${theme.accentBg}`}
        >
          <Text className="text-white font-bold">Refresh</Text>
        </Pressable>
      </View>
    ),
    [
      highContrast,
      locationLabel,
      selectedCategory,
      theme.accentBg,
      theme.cardBg,
      theme.cardBorder,
      theme.textPrimary,
      theme.textSecondary,
    ],
  );

  return (
    <View className={`flex-1 ${theme.screenBg}`} style={{ paddingTop: insets.top }}>
      <FlatList
        data={services}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ paddingHorizontal: 20, paddingTop: 16, paddingBottom: 120 }}
        ListHeaderComponent={listHeader}
        ListEmptyComponent={
          <View className={`rounded-2xl border p-4 ${theme.cardBg} ${theme.cardBorder}`}>
            <Text className={`${theme.textPrimary} font-semibold`}>
              {loading ? "Loading nearby services..." : "No services available"}
            </Text>
            <Text className={`mt-1 text-xs ${theme.textSecondary}`}>
              {error ?? "Try refreshing or changing category."}
            </Text>
          </View>
        }
        renderItem={({ item }) => (
          <View className={`rounded-2xl border p-4 mb-3 ${theme.cardBg} ${theme.cardBorder}`}>
            <View className="flex-row items-start justify-between">
              <View className="flex-1 pr-3">
                <Text className={`font-semibold ${theme.textPrimary}`}>{item.name}</Text>
                <Text className={`text-xs mt-1 ${theme.textSecondary}`}>
                  {item.address ?? "Address unavailable"}
                </Text>
                <Text className={`text-xs mt-1 ${theme.textSecondary}`}>
                  {item.category.replace("_", " ")} |{" "}
                  {formatDistanceMetres(item.distance_metres)}
                </Text>
              </View>
              <Ionicons
                name="medkit-outline"
                size={18}
                color={highContrast ? "#0f172a" : "#22d3ee"}
              />
            </View>

            <Pressable
              onPress={() => {
                // Previous map-focus flow (kept for reference):
                // setMapFocusTarget({
                //   latitude: item.latitude,
                //   longitude: item.longitude,
                //   label: item.name,
                // });
                // router.push("/(tabs)");

                const destinationQuery = item.address
                  ? `${item.name}, ${item.address}`
                  : item.name;

                router.push({
                  pathname: "/(tabs)/route",
                  params: { destination: destinationQuery },
                });
              }}
              className="mt-3 self-start rounded-xl bg-slate-900 px-3 py-2"
            >
              <Text className="text-white text-xs font-bold">Get route</Text>
            </Pressable>
          </View>
        )}
      />

      {error && !loading ? (
        <View className="absolute left-4 right-4 bottom-24 rounded-xl bg-amber-500 px-4 py-3">
          <Text className="text-slate-950 text-xs font-semibold">{error}</Text>
        </View>
      ) : null}
      <View className="absolute right-4 bottom-24 rounded-xl bg-slate-900/80 px-3 py-2">
        <Text className="text-[10px] text-slate-200">
          at {position.latitude.toFixed(4)}, {position.longitude.toFixed(4)}
        </Text>
      </View>
    </View>
  );
}
