import React, { useState } from "react";
import { View, Text, TextInput, Pressable, ScrollView } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useUiPreferences } from "../../src/providers/UIPreferences"; 

export default function ReportScreen() {
  const insets = useSafeAreaInsets();
  const { highContrast } = useUiPreferences(); 
  const [severity, setSeverity] = useState("Medium");

  const theme = {
    screenBg: highContrast ? "bg-white" : "bg-[#020617]",
    cardBg: highContrast ? "bg-slate-100" : "bg-slate-900/50",
    cardBorder: highContrast ? "border-slate-300" : "border-cyan-500/20",
    textPrimary: highContrast ? "text-slate-950" : "text-white",
    textSecondary: highContrast ? "text-slate-500" : "text-slate-400",
    inputBg: highContrast ? "bg-white" : "bg-slate-900",
    iconColor: highContrast ? "#0f172a" : "#22d3ee", 
    btnText: highContrast ? "text-white" : "text-slate-950",
  };

  return (
    <View className={`flex-1 ${theme.screenBg}`} style={{ paddingTop: insets.top }}>
      <View className={`flex-row items-center justify-between px-6 py-4 border-b ${theme.cardBorder}`}>
        <View className="flex-row items-center">
          <View className={`${highContrast ? "bg-slate-200" : "bg-slate-800"} p-2 rounded-xl mr-3`}>
            <Ionicons name="location" size={18} color={theme.iconColor} />
          </View>
          <View>
            <Text className={`text-xl font-bold ${theme.textPrimary}`}>AfterHours</Text>
            <Text className={`text-[10px] font-bold uppercase tracking-[2px] ${theme.textSecondary}`}>UK Safety Map</Text>
          </View>
        </View>
        
        <View className="flex-row gap-2">
          {["HC", "Aa", "Heat"].map((btn) => (
            <View key={btn} className={`${highContrast ? "bg-slate-200" : "bg-slate-800"} px-3 py-1 rounded-md`}>
              <Text className={`${highContrast ? "text-slate-900" : "text-white"} text-xs font-bold`}>{btn}</Text>
            </View>
          ))}
        </View>
      </View>

      <ScrollView className="px-6 mt-6">
        <Text className={`text-2xl font-bold ${theme.textPrimary}`}>Report an Issue</Text>
        <Text className={`${theme.textSecondary} mb-8`}>Help keep the community informed</Text>

        <Text className={`font-bold text-xs uppercase tracking-widest mb-3 ml-1 ${theme.textSecondary}`}>Description</Text>
        <View className={`p-4 rounded-2xl border ${theme.inputBg} ${theme.cardBorder} mb-6 shadow-sm`}>
          <TextInput
            multiline
            placeholder="Describe what happened..."
            placeholderTextColor={highContrast ? "#94a3b8" : "#475569"}
            className={`text-base ${theme.textPrimary}`}
            style={{ textAlignVertical: "top", minHeight: 100 }}
          />
        </View>

        <Text className={`font-bold text-xs uppercase tracking-widest mb-3 ml-1 ${theme.textSecondary}`}>Address / Area</Text>
        <View className={`p-4 rounded-2xl border ${theme.inputBg} ${theme.cardBorder} mb-6 shadow-sm`}>
          <TextInput
            placeholder="Street or area..."
            placeholderTextColor={highContrast ? "#94a3b8" : "#475569"}
            className={`text-base ${theme.textPrimary}`}
          />
        </View>

        <Text className={`font-bold text-xs uppercase tracking-widest mb-3 ml-1 ${theme.textSecondary}`}>Severity</Text>
        <View className={`flex-row p-1 rounded-2xl border ${theme.cardBg} ${theme.cardBorder} mb-8`}>
          {["Low", "Medium", "High"].map((level) => {
            const isActive = severity === level;
            
            const activeColorClass = highContrast 
              ? "bg-slate-900" 
              : "bg-cyan-500"; 

            return (
              <Pressable
                key={level}
                onPress={() => setSeverity(level)}
                className={`flex-1 py-3 rounded-xl items-center justify-center ${
                  isActive ? activeColorClass : "bg-transparent"
                }`}
              >
                <Text 
                  className={`font-bold ${
                    isActive ? (highContrast ? "text-white" : "text-slate-950") : theme.textSecondary
                  }`}
                >
                  {level}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <Pressable className={`${theme.cardBg} border ${theme.cardBorder} py-4 rounded-2xl items-center mb-6`}>
          <Text className={`font-bold ${theme.textPrimary}`}>Choose on map</Text>
        </Pressable>

        <Pressable 
          className={`${highContrast ? "bg-slate-900" : "bg-cyan-500"} py-5 rounded-2xl items-center shadow-lg active:opacity-90`}
        >
          <Text className={`${highContrast ? "text-white" : "text-slate-950"} font-black text-lg`}>
            Submit Report
          </Text>
        </Pressable>
        
        <View className="h-24" /> 
      </ScrollView>
    </View>
  );
}