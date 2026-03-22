import { Link } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { MapPreview } from "../src/features/map/MapPreview";
import { useUiPreferences } from "../src/providers/UIPreferences";

function FilterChip({
  active,
  icon,
  label,
  onPress,
}: {
  active: boolean;
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      className={`mr-2 flex-row items-center rounded-full px-4 py-2 ${
        active
          ? "border border-cyan-300/40 bg-cyan-300/20"
          : "border border-white/10 bg-slate-950/82"
      }`}
    >
      <Ionicons
        name={icon}
        size={16}
        color={active ? "#67e8f9" : "#cbd5e1"}
        style={{ marginRight: 8 }}
      />
      <Text className={`text-sm font-semibold ${active ? "text-cyan-100" : "text-white"}`}>
        {label}
      </Text>
    </Pressable>
  );
}

export default function HomeScreen() {
  const insets = useSafeAreaInsets();
  const { highContrast } = useUiPreferences();
  const { isLoaded, isSignedIn } = useAuth();

  const [destination, setDestination] = useState("");
  const [safePlacesEnabled, setSafePlacesEnabled] = useState(true);
  const [transportEnabled, setTransportEnabled] = useState(false);
  const [accessibleEnabled, setAccessibleEnabled] = useState(true);
  const [submittingReport, setSubmittingReport] = useState(false);

  const reports = useQuery(
    api.reports.listReports,
    isLoaded && isSignedIn ? {} : "skip"
  );
  const createReport = useMutation(api.reports.createReport);

  const panelBg = highContrast ? "bg-white/96" : "bg-slate-950/84";
  const panelBorder = highContrast ? "border-black/20" : "border-cyan-400/15";
  const textPrimary = highContrast ? "text-slate-950" : "text-white";
  const textSecondary = highContrast ? "text-slate-700" : "text-slate-300";
  const badgeBg = highContrast ? "bg-white/96" : "bg-slate-950/84";
  const badgeBorder = highContrast ? "border-black/15" : "border-cyan-400/20";

  if (!isLoaded || !isSignedIn) {
    return null;
  }

  return (
    <View className="flex-1 bg-slate-950">
      <View className="absolute inset-0">
        <MapPreview />
      </View>

      <View
        className="absolute left-4 right-4 z-20"
        style={{ top: insets.top + 8 }}
      >
        <View className="flex-row items-start justify-between">
          <View className={`rounded-full border px-4 py-2 ${badgeBg} ${badgeBorder}`}>
            <Text
              className={`text-xs font-bold uppercase tracking-[2.5px] ${
                highContrast ? "text-sky-700" : "text-cyan-300"
              }`}
            >
              Safer route prototype
            </Text>
            <Text className={`mt-1 text-sm ${textSecondary}`}>
              {reports ? `${reports.length} live reports nearby` : "Loading nearby reports..."}
            </Text>
          </View>

          <View className="ml-3 flex-row">
            <Link href="/profile" asChild>
              <Pressable
                className={`mr-3 h-14 w-14 items-center justify-center rounded-full border shadow-lg ${
                  highContrast
                    ? "border-black/15 bg-white"
                    : "border-cyan-400/20 bg-slate-950/84"
                }`}
              >
                <Ionicons
                  name="person-outline"
                  size={24}
                  color={highContrast ? "#0f172a" : "white"}
                />
              </Pressable>
            </Link>

            <Link href="/settings" asChild>
              <Pressable
                className={`h-14 w-14 items-center justify-center rounded-full border shadow-lg ${
                  highContrast
                    ? "border-black/15 bg-white"
                    : "border-cyan-400/20 bg-slate-950/84"
                }`}
              >
                <Ionicons
                  name="settings-outline"
                  size={24}
                  color={highContrast ? "#0f172a" : "white"}
                />
              </Pressable>
            </Link>
          </View>
        </View>
      </View>

      <View
        className="absolute left-4 right-24 z-20"
        style={{ top: insets.top + 76 }}
      >
        <View className={`rounded-[26px] border px-4 py-4 shadow-xl ${panelBg} ${panelBorder}`}>
          <Text
            className={`text-[11px] font-bold uppercase tracking-[2.5px] ${
              highContrast ? "text-sky-700" : "text-cyan-300"
            }`}
          >
            Route filters
          </Text>

          <View className="mt-3 flex-row flex-wrap">
            <FilterChip
              active={safePlacesEnabled}
              icon="shield-checkmark-outline"
              label="Nearby safe places"
              onPress={() => setSafePlacesEnabled((v) => !v)}
            />
            <FilterChip
              active={transportEnabled}
              icon="bus-outline"
              label="Transport tonight"
              onPress={() => setTransportEnabled((v) => !v)}
            />
            <FilterChip
              active={accessibleEnabled}
              icon="walk-outline"
              label="Accessibility"
              onPress={() => setAccessibleEnabled((v) => !v)}
            />
          </View>

          <Text className={`mt-3 text-sm ${textSecondary}`}>
            Placeholder filters for map layers and route preferences.
          </Text>
        </View>
      </View>

      <View
        className="absolute left-4 right-4 z-20"
        style={{ bottom: Math.max(insets.bottom, 16) + 85 }}
      >
        <View className={`rounded-[28px] border px-4 py-4 shadow-2xl ${panelBg} ${panelBorder}`}>
          <View className="flex-row items-center">
            <View
              className={`h-11 w-11 items-center justify-center rounded-full ${
                highContrast ? "bg-slate-200" : "bg-slate-800/80"
              }`}
            >
              <Ionicons
                name="search-outline"
                size={20}
                color={highContrast ? "#0f172a" : "#cbd5e1"}
              />
            </View>
            <View 
              className="absolute left-4 right-4" 
              style={{ bottom: insets.bottom + 90 }} 
            ></View>
            <TextInput
              value={destination}
              onChangeText={setDestination}
              placeholder="Enter address"
              placeholderTextColor={highContrast ? "#475569" : "#94a3b8"}
              className={`ml-3 flex-1 text-base ${textPrimary}`}
              returnKeyType="search"
            />

            <Pressable
              className={`h-11 w-11 items-center justify-center rounded-full ${
                highContrast ? "bg-sky-600" : "bg-cyan-400"
              }`}
            >
              <Ionicons
                name="arrow-forward"
                size={18}
                color={highContrast ? "#0f172a" : "white"}
              />
            </Pressable>
          </View>

          <View className="mt-4 flex-row items-center justify-between">
            <Text className={`text-sm ${textSecondary}`}>
              Signed in and ready to query protected data.
            </Text>

            <Pressable
              onPress={async () => {
                try {
                  setSubmittingReport(true);
                  await createReport({
                    location: destination.trim() || "City Centre",
                    description: "Prototype report from mobile client",
                    category: "lighting",
                  });
                } catch (err) {
                  console.error("Failed to create report", err);
                } finally {
                  setSubmittingReport(false);
                }
              }}
              className={`min-h-[56px] min-w-[56px] flex-row items-center justify-center rounded-full border px-5 shadow-xl ${
                highContrast
                  ? "border-black/15 bg-sky-600"
                  : "border-cyan-400/30 bg-cyan-500"
              }`}
            >
              <Ionicons
                name="warning-outline"
                size={20}
                color={highContrast ? "white" : "#082f49"}
              />
              <Text className={`ml-2 font-bold ${highContrast ? "text-white" : "text-slate-950"}`}>
                {submittingReport ? "Sending..." : "Report"}
              </Text>
            </Pressable>
          </View>
        </View>
      </View>
    </View>
  );
}