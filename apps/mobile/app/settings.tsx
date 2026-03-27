import { router } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Pressable, SafeAreaView, ScrollView, Switch, Text, View } from "react-native";

import { useUiPreferences } from "../src/providers/UIPreferences";

function SettingRow({
  icon,
  title,
  description,
  value,
  onValueChange,
  highContrast,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  description: string;
  value: boolean;
  onValueChange: (value: boolean) => void;
  highContrast: boolean;
}) {
  return (
    <View
      className={`mb-3 flex-row items-center rounded-3xl border px-4 py-4 ${
        highContrast ? "border-black/10 bg-white" : "border-white/10 bg-slate-900"
      }`}
    >
      <View
        className={`mr-4 h-12 w-12 items-center justify-center rounded-full ${
          highContrast ? "bg-slate-200" : "bg-slate-800"
        }`}
      >
        <Ionicons name={icon} size={22} color={highContrast ? "#0369a1" : "#67e8f9"} />
      </View>

      <View className="flex-1 pr-4">
        <Text className={`text-base font-semibold ${highContrast ? "text-slate-950" : "text-white"}`}>
          {title}
        </Text>
        <Text className={`mt-1 text-sm leading-6 ${highContrast ? "text-slate-700" : "text-slate-400"}`}>
          {description}
        </Text>
      </View>

      <Switch value={value} onValueChange={onValueChange} />
    </View>
  );
}

export default function SettingsScreen() {
  const { highContrast, setHighContrast } = useUiPreferences();

  return (
    <SafeAreaView className={`flex-1 ${highContrast ? "bg-slate-100" : "bg-slate-950"}`}>
      <ScrollView contentContainerStyle={{ paddingBottom: 36 }} showsVerticalScrollIndicator={false}>
        <View className="px-6 pt-6">
          <View className="mb-6 flex-row items-center justify-between">
            <Pressable
              onPress={() => router.back()}
              className={`rounded-full border px-4 py-2 ${
                highContrast ? "border-black/15 bg-white" : "border-slate-700 bg-slate-900"
              }`}
            >
              <Text className={`font-semibold ${highContrast ? "text-slate-950" : "text-white"}`}>Back</Text>
            </Pressable>

            <View
              className={`h-14 w-14 items-center justify-center rounded-full ${
                highContrast ? "bg-sky-600" : "bg-cyan-500"
              }`}
            >
              <Ionicons name="settings-outline" size={24} color="white" />
            </View>
          </View>

          <Text className={`text-3xl font-black ${highContrast ? "text-slate-950" : "text-white"}`}>
            Settings
          </Text>
          <Text className={`mt-3 text-base leading-7 ${highContrast ? "text-slate-700" : "text-slate-300"}`}>
            Placeholder controls for accessibility, route behaviour, and alerts.
          </Text>

          <View className={`mt-6 rounded-3xl border p-4 ${highContrast ? "border-black/10 bg-slate-50" : "border-cyan-400/15 bg-slate-900/80"}`}>
            <Text className={`text-xs font-bold uppercase tracking-[2px] ${highContrast ? "text-sky-700" : "text-cyan-300"}`}>
              Accessibility
            </Text>

            <View className="mt-4">
              <SettingRow
                icon="contrast-outline"
                title="High contrast mode"
                description="Increase contrast across the map and interface."
                value={highContrast}
                onValueChange={setHighContrast}
                highContrast={highContrast}
              />
              <SettingRow
                icon="walk-outline"
                title="Accessible routes"
                description="Placeholder toggle for accessibility-aware route selection."
                value={true}
                onValueChange={() => {}}
                highContrast={highContrast}
              />
              <SettingRow
                icon="navigate-outline"
                title="Landmark guidance"
                description="Placeholder toggle for landmark-based guidance."
                value={true}
                onValueChange={() => {}}
                highContrast={highContrast}
              />
            </View>
          </View>

          <View className={`mt-4 rounded-3xl border p-4 ${highContrast ? "border-black/10 bg-slate-50" : "border-cyan-400/15 bg-slate-900/80"}`}>
            <Text className={`text-xs font-bold uppercase tracking-[2px] ${highContrast ? "text-sky-700" : "text-cyan-300"}`}>
              Alerts and data
            </Text>

            <View className="mt-4">
              <SettingRow
                icon="notifications-outline"
                title="Leave now alerts"
                description="Placeholder toggle for late-night transport reminders."
                value={true}
                onValueChange={() => {}}
                highContrast={highContrast}
              />
              <SettingRow
                icon="cellular-outline"
                title="Low data mode"
                description="Placeholder toggle for route caching and reduced data use."
                value={false}
                onValueChange={() => {}}
                highContrast={highContrast}
              />
            </View>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}