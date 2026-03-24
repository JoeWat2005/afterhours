import React, { useState } from "react";
import { View, Text, TextInput, Pressable, ScrollView } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useUiPreferences } from "../../src/providers/UIPreferences";

export default function RouteScreen() {
  const insets = useSafeAreaInsets();
  const { highContrast } = useUiPreferences();
<<<<<<< HEAD
  const [fromValue, setFromValue] = useState("Old Joe, University of Birmingham");
  const [toValue, setToValue] = useState("");
=======
>>>>>>> origin/develop

  const theme = {
    screenBg: highContrast ? "bg-white" : "bg-[#020617]",
    cardBg: highContrast ? "bg-slate-100" : "bg-slate-900/40",
    inputBg: highContrast ? "bg-white" : "bg-slate-900",
    cardBorder: highContrast ? "border-slate-300" : "border-cyan-500/20",
    textPrimary: highContrast ? "text-slate-950" : "text-white",
    textSecondary: highContrast ? "text-slate-500" : "text-slate-400",
    accentCyan: highContrast ? "bg-slate-900" : "bg-cyan-500",
    accentText: highContrast ? "text-white" : "text-slate-950",
  };

<<<<<<< HEAD
  const handleSwap = () => {
    const temp = fromValue;
    setFromValue(toValue);
    setToValue(temp);
  };

=======
>>>>>>> origin/develop
  const steps = [
    { id: 1, road: "University Road West", dist: "400m", status: "Safe", sub: "→ University Rd / Edgbaston Pk Rd jn" },
    { id: 2, road: "Edgbaston Park Road", dist: "550m", status: "Safe", sub: "→ Edgbaston Park Rd / Pritchatts Rd" },
    { id: 3, road: "Edgbaston Park Road", dist: "500m", status: "Safe", sub: "→ Harborne Lane junction" },
    { id: 4, road: "Harborne Lane", dist: "380m", status: "Moderate", sub: "→ Selborne Rd / Bristol Rd jn" },
    { id: 5, road: "Bristol Road South", dist: "420m", status: "Moderate", sub: "→ Pebble Mill Road" },
  ];

  return (
    <View className={`flex-1 ${theme.screenBg}`} style={{ paddingTop: insets.top }}>
      <ScrollView className="px-6" showsVerticalScrollIndicator={false}>
        
        {/* Header */}
        <View className="mt-4 mb-6">
          <Text className={`text-2xl font-bold ${theme.textPrimary}`}>Plan Route</Text>
          <Text className={theme.textSecondary}>Street-level pathfinding with safety avoidance</Text>
        </View>

        {/* Input Section */}
        <View className="mb-6">
          <Text className={`text-xs font-black mb-2 uppercase ${theme.textSecondary}`}>From</Text>
          <View className="flex-row items-center gap-2 mb-4">
            <View className={`flex-1 flex-row items-center p-4 rounded-2xl border ${theme.inputBg} ${theme.cardBorder}`}>
              <View className="w-3 h-3 rounded-full bg-emerald-500 mr-3" />
<<<<<<< HEAD
              <TextInput 
                value={fromValue}
                onChangeText={setFromValue}
                placeholder="Start location"
                placeholderTextColor={highContrast ? "#64748b" : "#94a3b8"}
                className={`flex-1 ${theme.textPrimary}`} 
              />
=======
              <TextInput value="Old Joe, University of Birmingham" className={`flex-1 ${theme.textPrimary}`} />
>>>>>>> origin/develop
            </View>
            <View className={`p-4 rounded-2xl border ${theme.cardBg} ${theme.cardBorder}`}>
              <Ionicons name="location" size={20} color={highContrast ? "#0f172a" : "#22d3ee"} />
            </View>
          </View>

          <Pressable className="mb-4">
            <Text className="text-cyan-500 font-bold underline">Use my current location</Text>
          </Pressable>

<<<<<<< HEAD
          {/* Functional Swap Button */}
          <View className="items-center my-2">
            <Pressable 
              onPress={handleSwap}
              className={`p-2 rounded-full border ${theme.cardBorder} ${theme.cardBg} active:opacity-70`}
            >
              <Ionicons name="swap-vertical" size={20} color={highContrast ? "#0f172a" : "#22d3ee"} />
            </Pressable>
=======
          <View className="items-center my-2">
            <View className={`p-2 rounded-full border ${theme.cardBorder} ${theme.cardBg}`}>
              <Ionicons name="swap-vertical" size={20} color={highContrast ? "#0f172a" : "#22d3ee"} />
            </View>
>>>>>>> origin/develop
          </View>

          <Text className={`text-xs font-black mb-2 uppercase ${theme.textSecondary}`}>To</Text>
          <View className="flex-row items-center gap-2">
            <View className={`flex-1 flex-row items-center p-4 rounded-2xl border ${theme.inputBg} ${theme.cardBorder}`}>
              <View className="w-3 h-3 rounded-md bg-rose-500 mr-3" />
<<<<<<< HEAD
              <TextInput 
                value={toValue}
                onChangeText={setToValue}
                placeholder="Destination"
                placeholderTextColor={highContrast ? "#64748b" : "#94a3b8"}
                className={`flex-1 ${theme.textPrimary}`} 
              />
=======
              <TextInput value="Queen Elizabeth Hospital" className={`flex-1 ${theme.textPrimary}`} />
>>>>>>> origin/develop
            </View>
            <View className={`p-4 rounded-2xl border ${theme.cardBg} ${theme.cardBorder}`}>
              <Ionicons name="pin" size={20} color="#f43f5e" />
            </View>
          </View>
        </View>

        {/* Action Buttons */}
<<<<<<< HEAD
        <Pressable className={`${theme.accentCyan} py-5 rounded-2xl items-center mb-3 shadow-lg active:opacity-90`}>
          <Text className={`font-black text-lg ${theme.accentText}`}>Find Safe Route</Text>
        </Pressable>
        
        <Pressable className={`py-4 rounded-2xl border ${theme.cardBorder} ${theme.cardBg} items-center mb-8 active:opacity-70`}>
          <Text className={`font-bold ${theme.textPrimary}`}>Load Example Route</Text>
=======
        <Pressable className={`${theme.accentCyan} py-5 rounded-2xl items-center mb-3 shadow-lg`}>
          <Text className={`font-black text-lg ${theme.accentText}`}>Find Safe Route</Text>
        </Pressable>
        
        <Pressable className={`py-4 rounded-2xl border ${theme.cardBorder} ${theme.cardBg} items-center mb-8`}>
          <Text className={`font-bold ${theme.textPrimary}`}>Load Example Route (Old Joe → QE Hospital)</Text>
>>>>>>> origin/develop
        </Pressable>

        {/* Results Card */}
        <View className={`p-5 rounded-3xl border ${theme.cardBg} ${theme.cardBorder} mb-10`}>
          <View className="flex-row justify-between mb-4 border-b border-slate-700/20 pb-4">
            <Text className={`font-bold ${theme.textPrimary}`}>3.87 km · ~48 min walk</Text>
            <Text className="text-emerald-500 font-bold">99% safe</Text>
          </View>

          {steps.map((step) => (
            <View key={step.id} className="flex-row mb-6">
              <View className="items-center mr-4">
                <View className="bg-slate-800 w-8 h-8 rounded-full items-center justify-center border border-slate-700">
                  <Text className="text-white font-bold text-xs">{step.id}</Text>
                </View>
                {step.id !== steps.length && <View className="w-[1px] h-10 bg-slate-700 mt-2" />}
              </View>
              <View className="flex-1">
                <View className="flex-row justify-between items-start">
                  <Text className={`font-bold text-base ${theme.textPrimary}`}>{step.road} — {step.dist}</Text>
                  <Text className={`text-xs font-bold ${step.status === "Safe" ? "text-emerald-500" : "text-amber-500"}`}>
                    {step.status}
                  </Text>
                </View>
                <Text className={`text-xs mt-1 ${theme.textSecondary}`}>{step.sub}</Text>
              </View>
            </View>
          ))}
        </View>
        
        <View className="h-20" />
      </ScrollView>
    </View>
  );
}