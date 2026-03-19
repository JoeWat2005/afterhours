import { Text, View } from "react-native";
import Mapbox from "@rnmapbox/maps";

import { env } from "../../lib/env";
import { useUiPreferences } from "../../providers/UIPreferences";

Mapbox.setAccessToken(env.mapboxAccessToken ?? "");

const DEFAULT_VIEW_STATE = {
  centerCoordinate: [-1.89357, 52.48306] as [number, number],
  zoomLevel: 12,
};

const CITY_BOUNDS = {
  ne: [-1.7088, 52.5310] as [number, number],
  sw: [-2.0336, 52.3810] as [number, number],
};

export function MapPreview() {
  const mapEnabled = Boolean(env.mapboxAccessToken);
  const { highContrast } = useUiPreferences();

  if (!mapEnabled) {
    return (
      <View className="flex-1 items-center justify-center bg-slate-950 px-6">
        <Text className="text-center text-base font-medium text-slate-200">
          Add `EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN` to start rendering the map.
        </Text>
      </View>
    );
  }

  return (
    <View className="flex-1 bg-slate-950">
      <Mapbox.MapView
        style={{ flex: 1 }}
        styleURL={highContrast ? Mapbox.StyleURL.Light : Mapbox.StyleURL.Dark}
        scaleBarEnabled={false}
        compassEnabled={false}
        logoEnabled={true}
        attributionEnabled={true}
      >
        <Mapbox.Camera
          centerCoordinate={DEFAULT_VIEW_STATE.centerCoordinate}
          zoomLevel={DEFAULT_VIEW_STATE.zoomLevel}
          maxBounds={CITY_BOUNDS}
        />
      </Mapbox.MapView>
    </View>
  );
}