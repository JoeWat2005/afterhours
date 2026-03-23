import React from "react";
import { View, Text, FlatList, Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useUiPreferences } from "../../src/providers/UIPreferences";

export default function ReportsListScreen() {
  const insets = useSafeAreaInsets();
  const { highContrast } = useUiPreferences();

  const theme = {
    screenBg: highContrast ? "bg-white" : "bg-[#020617]",
    cardBg: highContrast ? "bg-slate-100" : "bg-slate-900/40",
    cardBorder: highContrast ? "border-slate-300" : "border-cyan-500/10",
    textPrimary: highContrast ? "text-slate-950" : "text-white",
    textSecondary: highContrast ? "text-slate-500" : "text-slate-400",
    headerBg: highContrast ? "bg-slate-200" : "bg-slate-800",
  };

  const mockReports = [
    { id: "1", type: "Crime", desc: "Theft from vehicle, Colmore Row", area: "Colmore Row, B3", date: "20/03/2026", severity: "HIGH" },
    { id: "2", type: "Crime", desc: "Assault outside bar", area: "Broad Street, B1", date: "19/03/2026", severity: "HIGH" },
    { id: "3", type: "Break-in", desc: "Residential break-in overnight", area: "Jennens Road, B4", date: "18/03/2026", severity: "HIGH" },
    { id: "4", type: "Poor Lighting", desc: "Four street lights out near station", area: "New Street, B2", date: "17/03/2026", severity: "MEDIUM" },
    { id: "5", type: "Crime", desc: "Phone snatching near Bullring", area: "Corporation Street, B2", date: "16/03/2026", severity: "HIGH" },
  ];

  return (
    <View className={`flex-1 ${theme.screenBg}`} style={{ paddingTop: insets.top }}>
      {/* Brand Header */}
      <View className={`flex-row items-center justify-between px-6 py-4 border-b ${theme.cardBorder}`}>
        <View className="flex-row items-center">
          <View className={`${theme.headerBg} p-2 rounded-xl mr-3`}>
            <Ionicons name="location" size={18} color={highContrast ? "#0f172a" : "#22d3ee"} />
          </View>
          <View>
            <Text className={`text-xl font-bold ${theme.textPrimary}`}>AfterHours</Text>
            <Text className={`text-[10px] font-bold uppercase tracking-[2px] ${theme.textSecondary}`}>UK Safety Map</Text>
          </View>
        </View>
        <View className="flex-row gap-2">
          {["HC", "Aa", "Heat"].map((btn) => (
            <View key={btn} className={`${theme.headerBg} px-3 py-1 rounded-md`}>
              <Text className={`${highContrast ? "text-slate-900" : "text-white"} text-xs font-bold`}>{btn}</Text>
            </View>
          ))}
        </View>
      </View>

      <FlatList
        data={mockReports}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ paddingHorizontal: 24, paddingTop: 24, paddingBottom: 100 }}
        ListHeaderComponent={() => (
          <View className="mb-6">
            <Text className={`text-2xl font-bold ${theme.textPrimary}`}>Safety Reports</Text>
            <Text className={theme.textSecondary}>Tap a report to view on map</Text>
          </View>
        )}
        renderItem={({ item }) => (
          <Pressable 
            className={`p-5 rounded-3xl border mb-4 ${theme.cardBg} ${theme.cardBorder} flex-row justify-between`}
          >
            <View className="flex-1 pr-4">
              <Text className={`text-lg font-bold mb-1 ${theme.textPrimary}`}>{item.type}</Text>
              <Text className={`text-sm mb-1 ${theme.textPrimary}`}>{item.desc}</Text>
              <Text className={`text-xs ${theme.textSecondary}`}>{item.area}</Text>
              <Text className={`text-xs mt-1 ${theme.textSecondary}`}>{item.date}</Text>
            </View>

            {/* Severity Badge */}
            <View>
              <View className={`px-3 py-1 rounded-full border ${
                item.severity === "HIGH" ? "bg-rose-500/10 border-rose-500/30" : "bg-amber-500/10 border-amber-500/30"
              }`}>
                <Text className={`text-[10px] font-black ${
                  item.severity === "HIGH" ? "text-rose-500" : "text-amber-500"
                }`}>
                  {item.severity}
                </Text>
              </View>
            </View>
          </Pressable>
        )}
      />
    </View>
  );
}