import { useEffect, useState } from "react";
import { Text, View } from "react-native";
import Mapbox from "@rnmapbox/maps";
import * as Location from "expo-location";

import { env } from "../../lib/env";
import { useUiPreferences } from "../../providers/UIPreferences";

Mapbox.setAccessToken(env.mapboxAccessToken ?? "");

export function MapPreview() {
  const mapEnabled = Boolean(process.env.EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN);
  const { highContrast } = useUiPreferences();
  const [userLocation, setUserLocation] = useState<[number, number] | null>(null);

  useEffect(() => {
    (async () => {
      const permission = await Location.requestForegroundPermissionsAsync();
      if (permission.status !== "granted") return;
      try {
        const position = await Location.getCurrentPositionAsync({});
        setUserLocation([position.coords.longitude, position.coords.latitude]);
      } catch {
        const last = await Location.getLastKnownPositionAsync();
        if (last) {
          setUserLocation([last.coords.longitude, last.coords.latitude]);
        }
      }
    })();
  }, []);

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
          centerCoordinate={userLocation ?? [-1.89357, 52.48306]}
          zoomLevel={14}
        />
        {userLocation ? (
          <Mapbox.PointAnnotation id="user-location" coordinate={userLocation}>
            <View className="h-4 w-4 rounded-full bg-blue-500 border-2 border-white" />
          </Mapbox.PointAnnotation>
        ) : null}
      </Mapbox.MapView>
    </View>
  );
}