import { router } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useEffect, useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAuth, useClerk, useUser } from "@clerk/expo";

import { apiRequest } from "../src/lib/api";
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
  const { signOut } = useClerk();
  const { user } = useUser();
  const { getToken } = useAuth();
  const [loggingOut, setLoggingOut] = useState(false);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profile, setProfile] = useState<{
    id: string;
    clerk_user_id: string;
    display_name: string | null;
    created_at: string;
  } | null>(null);

  useEffect(() => {
    let active = true;
    async function loadProfile() {
      setLoadingProfile(true);
      setProfileError(null);
      try {
        const payload = await apiRequest<{
          id: string;
          clerk_user_id: string;
          display_name: string | null;
          created_at: string;
        }>("/users/me", getToken);
        if (active) {
          setProfile(payload);
        }
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Failed to load profile.";
        if (active) {
          setProfileError(message);
        }
      } finally {
        if (active) {
          setLoadingProfile(false);
        }
      }
    }
    loadProfile();
    return () => {
      active = false;
    };
  }, [getToken]);

  const displayName =
    profile?.display_name?.trim() ||
    user?.fullName ||
    user?.primaryEmailAddress?.emailAddress ||
    "AfterHours User";

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
              {displayName}
            </Text>
            <Text className={`mt-2 text-base ${highContrast ? "text-slate-700" : "text-slate-300"}`}>
              {loadingProfile
                ? "Loading profile..."
                : profileError
                  ? profileError
                  : `Joined ${new Date(profile?.created_at ?? Date.now()).toLocaleDateString("en-GB")}`}
            </Text>
          </View>

          <View className="mt-6">
            <Pressable
              onPress={async () => {
                try {
                  setLoggingOut(true);
                  await signOut();
                } catch (err) {
                  console.error("Sign out failed", err);
                } finally {
                  setLoggingOut(false);
                }
              }}
              className={`items-center rounded-2xl border px-4 py-4 ${
                highContrast
                  ? "border-black/15 bg-red-600"
                  : "border-red-400/30 bg-red-500"
              }`}
            >
              <Text className={`font-bold text-base ${highContrast ? "text-white" : "text-slate-950"}`}>
                {loggingOut ? "Signing out..." : "Sign out"}
              </Text>
            </Pressable>
          </View>

          <View className="mt-4">
            <InfoBlock
              title="Account ID"
              body={profile?.id ?? "No account id loaded yet."}
              highContrast={highContrast}
            />
            <InfoBlock
              title="Clerk Subject"
              body={profile?.clerk_user_id ?? "No Clerk subject loaded yet."}
              highContrast={highContrast}
            />
            <InfoBlock
              title="Alerts"
              body="Leave-now reminders and transport preferences are still local placeholders."
              highContrast={highContrast}
            />
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
