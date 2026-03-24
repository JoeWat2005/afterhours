import React, { useState } from "react";
import { View, Text, TextInput, Pressable, ScrollView, FlatList } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useUiPreferences } from "../../src/providers/UIPreferences";

export default function ServicesScreen() {
  const insets = useSafeAreaInsets();
  const { highContrast } = useUiPreferences();
  const [selectedCategory, setSelectedCategory] = useState("Fire Station");

  const categories = ["All", "Hospital", "Police", "Fire Station", "Ambulance"];

  const theme = {
    screenBg: highContrast ? "bg-white" : "bg-[#020617]",
    cardBg: highContrast ? "bg-slate-100" : "bg-slate-900/40",
    cardBorder: highContrast ? "border-slate-300" : "border-cyan-500/20",
    textPrimary: highContrast ? "text-slate-950" : "text-white",
    textSecondary: highContrast ? "text-slate-500" : "text-slate-400",
    inputBg: highContrast ? "bg-white" : "bg-slate-900",
  };
// Example for display
  const emergencyServices = [
    {
      id: "1",
      name: "Birmingham Central Fire",
      provider: "West Midlands Fire Service",
      phone: "0121 380 6999",
      distance: "4.5 km",
      type: "FIRE"
    },
    {
      id: "2",
      name: "Highgate Fire Station",
      provider: "South Birmingham fire cover",
      phone: "0121 380 6999",
      distance: "2.9 km",
      type: "FIRE"
    }
  ];

  return (
    <View className={`flex-1 ${theme.screenBg}`} style={{ paddingTop: insets.top }}>
      {/* Brand Header */}
      <View className={`flex-row items-center justify-between px-6 py-4 border-b ${theme.cardBorder}`}>
        <View className="flex-row items-center">
          <View className={`${highContrast ? "bg-slate-200" : "bg-slate-800"} p-2 rounded-xl mr-3`}>
            <Ionicons name="location" size={18} color={highContrast ? "#0f172a" : "#22d3ee"} />
          </View>
          <View>
            <Text className={`text-xl font-bold ${theme.textPrimary}`}>AfterHours</Text>
            <Text className={`text-[10px] font-bold uppercase tracking-[2px] ${theme.textSecondary}`}>UK Safety Map</Text>
          </View>
        </View>
        <View className="flex-row gap-2">
          {["HC", "Aa", "Heat"].map((btn) => (
            <View key={btn} className={`${highContrast ? "bg-slate-200" : "bg-slate-800"} px-3 py-1 rounded-md border ${theme.cardBorder}`}>
              <Text className={`${highContrast ? "text-slate-900" : "text-white"} text-xs font-bold`}>{btn}</Text>
            </View>
          ))}
          <Ionicons name="move" size={20} color={theme.textSecondary} style={{ marginLeft: 4 }} />
        </View>
      </View>

      <View className="px-6 pt-6 flex-1">
        <Text className={`text-3xl font-bold mb-4 ${theme.textPrimary}`}>Emergency Services</Text>

        {/* Search Bar */}
        <View className={`p-4 rounded-xl border ${theme.inputBg} ${theme.cardBorder} mb-4 flex-row items-center`}>
          <TextInput 
            placeholder="Search services..." 
            placeholderTextColor={highContrast ? "#94a3b8" : "#475569"}
            className={`flex-1 text-base ${theme.textPrimary}`}
          />
        </View>

        {/* Category Filters */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} className="flex-row mb-6 max-h-10">
          {categories.map((cat) => (
            <Pressable
              key={cat}
              onPress={() => setSelectedCategory(cat)}
              className={`px-4 py-2 rounded-full border mr-2 items-center justify-center ${
                selectedCategory === cat 
                  ? (highContrast ? "bg-slate-900 border-slate-900" : "bg-slate-700 border-slate-600") 
                  : `bg-transparent ${theme.cardBorder}`
              }`}
            >
              <Text className={`text-xs font-bold ${selectedCategory === cat ? "text-white" : theme.textPrimary}`}>
                {cat}
              </Text>
            </Pressable>
          ))}
        </ScrollView>

        {/* Service Cards */}
        <FlatList
          data={emergencyServices}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <Pressable className={`p-5 rounded-3xl border mb-4 ${theme.cardBg} ${theme.cardBorder} flex-row justify-between items-center`}>
              <View className="flex-row items-center flex-1">
                <View className="bg-rose-100 p-2 rounded-lg mr-4 items-center justify-center">
                   <Text className="text-rose-600 font-black text-[10px] uppercase">{item.type}</Text>
                </View>
                <View className="flex-1">
                  <Text className={`font-bold text-base ${theme.textPrimary}`}>{item.name}</Text>
                  <Text className={`text-xs ${theme.textSecondary}`}>{item.provider}</Text>
                  <Text className={`text-sm font-bold mt-1 ${theme.textPrimary}`}>{item.phone}</Text>
                </View>
              </View>
              <Text className={`font-bold text-sm ${theme.textPrimary}`}>{item.distance}</Text>
            </Pressable>
          )}
          contentContainerStyle={{ paddingBottom: 100 }}
        />
      </View>
    </View>
  );
}