import { router } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Pressable, ScrollView, Switch, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import {
  useUiPreferences,
  type RouteAccessibilityChoices,
  type RouteWaitingAreaChoices,
} from "../src/providers/UIPreferences";

const ACCESSIBILITY_SETTINGS: Array<{
  icon: keyof typeof Ionicons.glyphMap;
  key: keyof RouteAccessibilityChoices;
  title: string;
  description: string;
}> = [
  {
    icon: "remove-circle-outline",
    key: "avoid_stairs",
    title: "Avoid stairs",
    description: "Hard requirement for routes without stairs.",
  },
  {
    icon: "walk-outline",
    key: "step_free_access",
    title: "Step-free access",
    description: "Prioritise routes with step-free coverage.",
  },
  {
    icon: "arrow-up-circle-outline",
    key: "lifts_available",
    title: "Lifts available",
    description: "Prefer routes with lift coverage.",
  },
  {
    icon: "triangle-outline",
    key: "ramps_available",
    title: "Ramps available",
    description: "Prefer routes with ramp coverage.",
  },
  {
    icon: "swap-vertical-outline",
    key: "escalators_available",
    title: "Escalators available",
    description: "Prefer routes with escalator coverage.",
  },
];

const WAITING_AREA_SETTINGS: Array<{
  icon: keyof typeof Ionicons.glyphMap;
  key: keyof RouteWaitingAreaChoices;
  title: string;
  description: string;
}> = [
  {
    icon: "shield-checkmark-outline",
    key: "safe_waiting_areas",
    title: "Safe waiting areas",
    description: "Prioritise routes with nearby safe places.",
  },
  {
    icon: "sunny-outline",
    key: "well_lit_waiting_areas",
    title: "Well-lit waiting",
    description: "Prefer waiting points with better lighting.",
  },
  {
    icon: "wifi-outline",
    key: "wifi_nearby",
    title: "Wi-Fi nearby",
    description: "Prefer routes near Wi-Fi access points.",
  },
  {
    icon: "people-outline",
    key: "staffed_venues_nearby",
    title: "Staffed venues",
    description: "Prefer nearby staffed locations.",
  },
  {
    icon: "storefront-outline",
    key: "open_venues_nearby",
    title: "Open venues",
    description: "Prefer routes near open venues.",
  },
  {
    icon: "compass-outline",
    key: "safe_areas_nearby",
    title: "Safe-area coverage",
    description: "Prefer waiting areas that overlap safer zones.",
  },
];

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
  const {
    highContrast,
    setHighContrast,
    routeOptions,
    setAccessibilityOption,
    setWaitingAreaOption,
    leaveNowAlerts,
    setLeaveNowAlerts,
    lowDataMode,
    setLowDataMode,
  } = useUiPreferences();

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
            Route options map directly to backend route requirements and preferences.
          </Text>

          <View className={`mt-6 rounded-3xl border p-4 ${highContrast ? "border-black/10 bg-slate-50" : "border-cyan-400/15 bg-slate-900/80"}`}>
            <Text className={`text-xs font-bold uppercase tracking-[2px] ${highContrast ? "text-sky-700" : "text-cyan-300"}`}>
              Interface
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
            </View>
          </View>

          <View className={`mt-4 rounded-3xl border p-4 ${highContrast ? "border-black/10 bg-slate-50" : "border-cyan-400/15 bg-slate-900/80"}`}>
            <Text className={`text-xs font-bold uppercase tracking-[2px] ${highContrast ? "text-sky-700" : "text-cyan-300"}`}>
              Route Accessibility
            </Text>
            <Text className={`mt-2 text-xs ${highContrast ? "text-slate-700" : "text-slate-400"}`}>
              Sent as `requirements.accessibility` and `preferences.accessibility`.
            </Text>

            <View className="mt-4">
              {ACCESSIBILITY_SETTINGS.map((setting) => (
                <SettingRow
                  key={setting.key}
                  icon={setting.icon}
                  title={setting.title}
                  description={setting.description}
                  value={routeOptions.accessibility[setting.key]}
                  onValueChange={(value) => setAccessibilityOption(setting.key, value)}
                  highContrast={highContrast}
                />
              ))}
            </View>
          </View>

          <View className={`mt-4 rounded-3xl border p-4 ${highContrast ? "border-black/10 bg-slate-50" : "border-cyan-400/15 bg-slate-900/80"}`}>
            <Text className={`text-xs font-bold uppercase tracking-[2px] ${highContrast ? "text-sky-700" : "text-cyan-300"}`}>
              Waiting Areas
            </Text>
            <Text className={`mt-2 text-xs ${highContrast ? "text-slate-700" : "text-slate-400"}`}>
              Sent as `requirements.waiting_areas` and `preferences.waiting_areas`.
            </Text>

            <View className="mt-4">
              {WAITING_AREA_SETTINGS.map((setting) => (
                <SettingRow
                  key={setting.key}
                  icon={setting.icon}
                  title={setting.title}
                  description={setting.description}
                  value={routeOptions.waiting_areas[setting.key]}
                  onValueChange={(value) => setWaitingAreaOption(setting.key, value)}
                  highContrast={highContrast}
                />
              ))}
            </View>
          </View>

          <View className={`mt-4 rounded-3xl border p-4 ${highContrast ? "border-black/10 bg-slate-50" : "border-cyan-400/15 bg-slate-900/80"}`}>
            <Text className={`text-xs font-bold uppercase tracking-[2px] ${highContrast ? "text-sky-700" : "text-cyan-300"}`}>
              Alerts and Data
            </Text>

            <View className="mt-4">
              <SettingRow
                icon="notifications-outline"
                title="Leave now alerts"
                description="Enable transport reminder behaviours in the app."
                value={leaveNowAlerts}
                onValueChange={setLeaveNowAlerts}
                highContrast={highContrast}
              />
              <SettingRow
                icon="cellular-outline"
                title="Low data mode"
                description="Request fewer route alternatives to reduce network usage."
                value={lowDataMode}
                onValueChange={setLowDataMode}
                highContrast={highContrast}
              />
            </View>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
