import { Text, View, Pressable } from "react-native";
import { Link } from "expo-router";

import Mapbox from "@rnmapbox/maps";

import { SectionCard } from "../../components/ui/SectionCard";
import { env } from "../../lib/env";

Mapbox.setAccessToken(env.mapboxAccessToken ?? "");

const DEFAULT_VIEW_STATE = {
  centerCoordinate: [-1.89357, 52.48306] as [number, number],
  zoomLevel: 12
};

const CITY_BOUNDS = {
  ne: [-1.7088, 52.5310] as [number, number], 
  sw: [-2.0336, 52.3810] as [number, number]  
};

export function MapPreview() {
  const mapEnabled = Boolean(env.mapboxAccessToken);

  return (
    <SectionCard
      eyebrow="Route intelligence"
      title="Mapbox route canvas"
      description="Map screen starter with token gating, so the app doesn’t instantly fall over if the env file isn’t sorted yet."
      aside={
        <View className="rounded-full border border-white/10 bg-white/10 px-3 py-1">
          <Text className="text-xs font-semibold text-white">
            {mapEnabled ? "Map ready" : "Token missing"}
          </Text>
        </View>
      }
    >
      <View className="gap-3">
        <View className="h-72 overflow-hidden rounded-[24px] border border-white/10 bg-slate-900">
          {mapEnabled ? (
            <Mapbox.MapView style={{ flex: 1 }} styleURL={Mapbox.StyleURL.Dark}>
              <Mapbox.Camera
                centerCoordinate={DEFAULT_VIEW_STATE.centerCoordinate}
                zoomLevel={DEFAULT_VIEW_STATE.zoomLevel}
                maxBounds={CITY_BOUNDS}
              />
            </Mapbox.MapView>
          ) : (
            <View className="flex-1 items-center justify-center px-6">
              <Text className="text-center text-base font-medium text-slate-200">
                Add `EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN` to start rendering the map.
              </Text>
            </View>
          )}
        </View>
        <Text className="text-sm leading-6 text-slate-400">
          Mapbox needs a development build instead of plain Expo Go because it uses
          native modules.
        </Text>
      </View>
    </SectionCard>
  );
}

