import { Tabs } from "expo-router";
import { Ionicons } from "@expo/vector-icons";

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: "#0891b2",
        tabBarInactiveTintColor: "#64748b",
        tabBarStyle: {
          height: 85,
          backgroundColor: "#f8fafc",
          borderTopWidth: 1,
          borderTopColor: "#e2e8f0",
          paddingBottom: 20,
          paddingTop: 10,
        },
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: "600",
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Map",
          tabBarStyle: { display: "none" },
          tabBarIcon: ({ color }) => (
            <Ionicons name="map-outline" size={26} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="route"
        options={{
          title: "Route",
          tabBarIcon: ({ color }) => (
            <Ionicons name="navigate-outline" size={26} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="report"
        options={{
          title: "Report",
          tabBarIcon: ({ color }) => (
            <Ionicons name="warning-outline" size={26} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="report_list"
        options={{
          title: "Reports",
          tabBarIcon: ({ color }) => (
            <Ionicons name="list-outline" size={26} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="services"
        options={{
          title: "Services",
          tabBarIcon: ({ color }) => (
            <Ionicons name="medkit-outline" size={26} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
