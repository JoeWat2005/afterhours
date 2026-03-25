import React, { useState } from "react";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useAuth } from "@clerk/expo";
import { useMutation } from "convex/react";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "../../convex/_generated/api";
import {
  apiRequest,
  geocodePlace,
  logPrototypeEvent,
  type SafetyReportResponse,
} from "../../src/lib/api";
import { mapUiIssueToCategories } from "../../src/features/reports/categories";
import { useUiPreferences } from "../../src/providers/UIPreferences";

const ISSUE_OPTIONS = [
  "Crime",
  "Break-in / Burglary",
  "Harassment",
  "Unsafe Area",
  "Poor Lighting",
  "Road Hazard / Potholes",
  "Anti-social Behaviour",
  "Other",
];
const ISSUE_PLACEHOLDER = "Select type...";

type ValidationResponse = {
  accepted: boolean;
  moderation_flags: string[];
};

function parseCoordinate(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  if (!Number.isFinite(parsed)) return null;
  return parsed;
}

export default function ReportScreen() {
  const insets = useSafeAreaInsets();
  const { highContrast } = useUiPreferences();
  const { getToken } = useAuth();
  const createRealtimeReport = useMutation(api.reports.createReport);

  const [issueType, setIssueType] = useState(ISSUE_PLACEHOLDER);
  const [description, setDescription] = useState("");
  const [area, setArea] = useState("");
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [dropdownVisible, setDropdownVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [resolvingLocation, setResolvingLocation] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const theme = {
    screenBg: highContrast ? "bg-white" : "bg-[#020617]",
    cardBg: highContrast ? "bg-slate-100" : "bg-slate-900/50",
    cardBorder: highContrast ? "border-slate-300" : "border-cyan-500/20",
    inputBg: highContrast ? "bg-white" : "bg-slate-900",
    textPrimary: highContrast ? "text-slate-950" : "text-white",
    textSecondary: highContrast ? "text-slate-500" : "text-slate-400",
    accentBg: highContrast ? "bg-slate-900" : "bg-cyan-500",
  };

  async function resolveCoordinates() {
    const parsedLatitude = parseCoordinate(latitude);
    const parsedLongitude = parseCoordinate(longitude);
    if (parsedLatitude !== null && parsedLongitude !== null) {
      return {
        latitude: parsedLatitude,
        longitude: parsedLongitude,
        label:
          area.trim() ||
          `${parsedLatitude.toFixed(5)}, ${parsedLongitude.toFixed(5)}`,
      };
    }

    const trimmedArea = area.trim();
    if (!trimmedArea) {
      throw new Error("Add area or coordinates before submitting.");
    }

    setResolvingLocation(true);
    try {
      const [match] = await geocodePlace(trimmedArea, { limit: 1 });
      if (!match) {
        throw new Error("Could not resolve area coordinates.");
      }
      setLatitude(match.latitude.toFixed(6));
      setLongitude(match.longitude.toFixed(6));
      return {
        latitude: match.latitude,
        longitude: match.longitude,
        label: match.label,
      };
    } finally {
      setResolvingLocation(false);
    }
  }

  async function handleSubmit() {
    if (submitting) return;
    setError(null);
    setFeedback(null);

    if (issueType === ISSUE_PLACEHOLDER) {
      setError("Select an issue type.");
      return;
    }
    if (description.trim().length < 12) {
      setError("Description must be at least 12 characters.");
      return;
    }

    setSubmitting(true);
    try {
      const coords = await resolveCoordinates();
      const mappedCategory = mapUiIssueToCategories(issueType);
      const summary = `${issueType} near ${area.trim() || "selected location"}`.slice(
        0,
        280,
      );

      const validation = await apiRequest<ValidationResponse>(
        "/routes/reports/validate",
        getToken,
        {
          method: "POST",
          requireAuth: false,
          body: {
            category: mappedCategory.canonical,
            summary,
            description: description.trim(),
            latitude: coords.latitude,
            longitude: coords.longitude,
          },
        },
      );
      if (!validation.accepted) {
        throw new Error(
          `Report blocked: ${validation.moderation_flags.join(", ") || "unknown reason"}`,
        );
      }

      const saved = await apiRequest<SafetyReportResponse>("/reports", getToken, {
        method: "POST",
        body: {
          category: mappedCategory.canonical,
          summary,
          details: description.trim(),
          latitude: coords.latitude,
          longitude: coords.longitude,
        },
      });

      try {
        await createRealtimeReport({
          apiReportId: saved.id,
          latitude: saved.latitude,
          longitude: saved.longitude,
          category: mappedCategory.convex,
          description: saved.summary,
          location: `${coords.label} (${saved.latitude.toFixed(5)}, ${saved.longitude.toFixed(5)})`,
        });
      } catch (mirrorError) {
        const message =
          mirrorError instanceof Error
            ? mirrorError.message
            : "Convex realtime mirror failed.";
        logPrototypeEvent("report_realtime_mirror_failed", { error: message, id: saved.id });
      }

      setDescription("");
      setArea("");
      setFeedback("Report submitted.");
      router.push("/(tabs)/report_list");
    } catch (submitError) {
      const message =
        submitError instanceof Error ? submitError.message : "Failed to submit report.";
      logPrototypeEvent("report_submit_failed", { error: message });
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <View className={`flex-1 ${theme.screenBg}`} style={{ paddingTop: insets.top }}>
      <ScrollView className="px-6" contentContainerStyle={{ paddingBottom: 110 }}>
        <View className="mt-4 mb-5">
          <Text className={`text-2xl font-bold ${theme.textPrimary}`}>Report safety issue</Text>
          <Text className={`mt-1 text-sm ${theme.textSecondary}`}>
            Writes to backend and mirrors to Convex for realtime updates.
          </Text>
        </View>

        <Text className={`text-xs font-bold uppercase mb-2 ${theme.textSecondary}`}>Issue type</Text>
        <Pressable
          onPress={() => setDropdownVisible(true)}
          className={`rounded-2xl border px-4 py-4 ${theme.inputBg} ${theme.cardBorder}`}
        >
          <Text
            className={
              issueType === ISSUE_PLACEHOLDER ? theme.textSecondary : theme.textPrimary
            }
          >
            {issueType}
          </Text>
        </Pressable>

        <Text className={`text-xs font-bold uppercase mt-4 mb-2 ${theme.textSecondary}`}>Description</Text>
        <View className={`rounded-2xl border px-4 py-3 ${theme.inputBg} ${theme.cardBorder}`}>
          <TextInput
            value={description}
            onChangeText={setDescription}
            multiline
            placeholder="Describe what happened"
            placeholderTextColor={highContrast ? "#64748b" : "#475569"}
            className={theme.textPrimary}
            style={{ minHeight: 100, textAlignVertical: "top" }}
          />
        </View>

        <Text className={`text-xs font-bold uppercase mt-4 mb-2 ${theme.textSecondary}`}>Area</Text>
        <View className={`rounded-2xl border px-4 py-3 ${theme.inputBg} ${theme.cardBorder}`}>
          <TextInput
            value={area}
            onChangeText={setArea}
            placeholder="Street or area"
            placeholderTextColor={highContrast ? "#64748b" : "#475569"}
            className={theme.textPrimary}
          />
        </View>

        <Text className={`text-xs font-bold uppercase mt-4 mb-2 ${theme.textSecondary}`}>
          Coordinates (optional)
        </Text>
        <View className="flex-row">
          <View className={`flex-1 mr-2 rounded-2xl border px-4 py-3 ${theme.inputBg} ${theme.cardBorder}`}>
            <TextInput
              value={latitude}
              onChangeText={setLatitude}
              placeholder="Latitude"
              keyboardType="numbers-and-punctuation"
              placeholderTextColor={highContrast ? "#64748b" : "#475569"}
              className={theme.textPrimary}
            />
          </View>
          <View className={`flex-1 ml-2 rounded-2xl border px-4 py-3 ${theme.inputBg} ${theme.cardBorder}`}>
            <TextInput
              value={longitude}
              onChangeText={setLongitude}
              placeholder="Longitude"
              keyboardType="numbers-and-punctuation"
              placeholderTextColor={highContrast ? "#64748b" : "#475569"}
              className={theme.textPrimary}
            />
          </View>
        </View>

        <Pressable
          onPress={async () => {
            setError(null);
            setFeedback(null);
            try {
              const coords = await resolveCoordinates();
              setFeedback(
                `Coordinates resolved to ${coords.latitude.toFixed(5)}, ${coords.longitude.toFixed(5)}`,
              );
            } catch (resolveError) {
              const message =
                resolveError instanceof Error
                  ? resolveError.message
                  : "Could not resolve coordinates.";
              setError(message);
            }
          }}
          disabled={resolvingLocation || submitting}
          className={`mt-4 rounded-2xl border px-4 py-3 items-center ${theme.cardBg} ${theme.cardBorder}`}
        >
          {resolvingLocation ? (
            <ActivityIndicator color={highContrast ? "#0f172a" : "#22d3ee"} />
          ) : (
            <Text className={`font-semibold ${theme.textPrimary}`}>Resolve from area</Text>
          )}
        </Pressable>

        {error ? (
          <View
            className={`mt-4 rounded-2xl border p-4 ${
              highContrast
                ? "border-red-300 bg-red-100"
                : "border-red-500/40 bg-red-500/10"
            }`}
          >
            <Text className={highContrast ? "text-red-800" : "text-red-200"}>{error}</Text>
          </View>
        ) : null}

        {feedback ? (
          <View
            className={`mt-4 rounded-2xl border p-4 ${
              highContrast
                ? "border-emerald-300 bg-emerald-100"
                : "border-emerald-500/40 bg-emerald-500/10"
            }`}
          >
            <Text className={highContrast ? "text-emerald-800" : "text-emerald-200"}>
              {feedback}
            </Text>
          </View>
        ) : null}

        <Pressable
          onPress={handleSubmit}
          disabled={submitting || resolvingLocation}
          className={`mt-5 rounded-2xl px-4 py-4 items-center ${theme.accentBg}`}
        >
          {submitting ? (
            <ActivityIndicator color="#ffffff" />
          ) : (
            <Text className="text-white font-bold">Submit report</Text>
          )}
        </Pressable>
      </ScrollView>

      <Modal
        visible={dropdownVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setDropdownVisible(false)}
      >
        <Pressable
          className="flex-1 bg-black/60 justify-center px-6"
          onPress={() => setDropdownVisible(false)}
        >
          <View className={`rounded-3xl border ${theme.cardBg} ${theme.cardBorder}`}>
            <Text className={`px-4 py-4 font-bold border-b ${theme.cardBorder} ${theme.textPrimary}`}>
              Select issue type
            </Text>
            {ISSUE_OPTIONS.map((option) => (
              <Pressable
                key={option}
                onPress={() => {
                  setIssueType(option);
                  setDropdownVisible(false);
                }}
                className="px-4 py-4 flex-row items-center justify-between"
              >
                <Text className={theme.textPrimary}>{option}</Text>
                {issueType === option ? (
                  <Ionicons
                    name="checkmark-circle"
                    size={18}
                    color={highContrast ? "#0f172a" : "#22d3ee"}
                  />
                ) : null}
              </Pressable>
            ))}
          </View>
        </Pressable>
      </Modal>
    </View>
  );
}
