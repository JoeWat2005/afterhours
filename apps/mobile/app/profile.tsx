import { router } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Pressable, SafeAreaView, ScrollView, Text, View } from "react-native";

import { useUiPreferences } from "../src/providers/UIPreferences";

function InfoBlock({
  title,
  body,
  highContrast,
}: {
  title: string;
  body: string;
  highContrast: boolean;
}) {
  return (
    <View
      className={`mb-3 rounded-3xl border px-4 py-4 ${
        highContrast ? "border-black/10 bg-white" : "border-white/10 bg-slate-900"
      }`}
    >
      <Text className={`text-base font-semibold ${highContrast ? "text-slate-950" : "text-white"}`}>
        {title}
      </Text>
      <Text className={`mt-2 text-sm leading-6 ${highContrast ? "text-slate-700" : "text-slate-400"}`}>
        {body}
      </Text>
    </View>
  );
}

export default function ProfileScreen() {
  const { highContrast } = useUiPreferences();

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
              <Ionicons name="person-outline" size={24} color="white" />
            </View>
          </View>

          <View
            className={`rounded-[32px] border p-5 ${
              highContrast ? "border-black/10 bg-white" : "border-cyan-400/15 bg-slate-900/90"
            }`}
          >
            <Text className={`text-xs font-bold uppercase tracking-[2px] ${highContrast ? "text-sky-700" : "text-cyan-300"}`}>
              Profile
            </Text>
            <Text className={`mt-2 text-3xl font-black ${highContrast ? "text-slate-950" : "text-white"}`}>
              Placeholder user
            </Text>
            <Text className={`mt-2 text-base ${highContrast ? "text-slate-700" : "text-slate-300"}`}>
              Placeholder profile and saved preferences.
            </Text>
          </View>

          <View className="mt-4">
            <InfoBlock
              title="Saved safe places"
              body="Placeholder list for bookmarked waiting areas, staffed buildings, and WiFi-enabled spaces."
              highContrast={highContrast}
            />
            <InfoBlock
              title="Reporting status"
              body="Placeholder summary for verified reporting eligibility and hourly submission limits."
              highContrast={highContrast}
            />
            <InfoBlock
              title="Alerts"
              body="Placeholder summary for leave-now reminders and transport preferences."
              highContrast={highContrast}
            />
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}