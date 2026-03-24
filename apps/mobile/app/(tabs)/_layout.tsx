import { Tabs } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
<<<<<<< HEAD
import { View, Text } from "react-native";
=======
>>>>>>> origin/develop

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
<<<<<<< HEAD
        tabBarActiveTintColor: "#0891b2", 
        tabBarInactiveTintColor: "#64748b", 
=======
        tabBarActiveTintColor: "#0891b2",
        tabBarInactiveTintColor: "#64748b",
>>>>>>> origin/develop
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
<<<<<<< HEAD
          tabBarIcon: ({ color }) => <Ionicons name="map-outline" size={26} color={color} />,
        }}
      />
      <Tabs.Screen
        name="route"
        options={{
          title: "Route",
          tabBarIcon: ({ color }) => <Ionicons name="git-network-outline" size={26} color={color} />,
=======
          tabBarIcon: ({ color }) => (
            <Ionicons name="map-outline" size={26} color={color} />
          ),
>>>>>>> origin/develop
        }}
      />
      <Tabs.Screen
        name="report"
        options={{
          title: "Report",
<<<<<<< HEAD
          tabBarIcon: ({ color }) => <Ionicons name="warning-outline" size={26} color={color} />,
        }}
      />
      <Tabs.Screen
        name="reports_list"
        options={{
          title: "Report List",
          tabBarIcon: ({ color }) => <Ionicons name="list-sharp" size={26} color={color} />,
        }}
      />
      <Tabs.Screen
        name="services"
        options={{
          title: "Services",
          tabBarIcon: ({ color }) => <Ionicons name="home-outline" size={26} color={color} />,
=======
          tabBarIcon: ({ color }) => (
            <Ionicons name="warning-outline" size={26} color={color} />
          ),
>>>>>>> origin/develop
        }}
      />
    </Tabs>
  );
}