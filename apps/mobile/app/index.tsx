import { SafeAreaView, ScrollView, Text, View } from "react-native";

import { ArchitectureOverview } from "../src/features/dashboard/ArchitectureOverview";
import { MapPreview } from "../src/features/map/MapPreview";

export default function HomeScreen() {
  return (
    <SafeAreaView className="flex-1 bg-slate-950">
      <ScrollView
        className="flex-1"
        contentContainerStyle={{ paddingBottom: 48 }}
        showsVerticalScrollIndicator={false}
      >
        <View className="gap-6 px-6 pb-10 pt-8">
          <View className="gap-3">
            <Text className="text-xs font-semibold uppercase tracking-[3px] text-cyan-300">
              AfterHours / Mobile Client
            </Text>
            <Text className="text-4xl font-black leading-tight text-white">
              Safe route planning with realtime trip signals.
            </Text>
            <Text className="max-w-xl text-base leading-7 text-slate-300">
              Expo, NativeWind, Clerk, Convex and Mapbox are all scaffolded so the
              frontend lot can actually get moving instead of arguing about folder names.
            </Text>
          </View>

          <MapPreview />
          <ArchitectureOverview />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

