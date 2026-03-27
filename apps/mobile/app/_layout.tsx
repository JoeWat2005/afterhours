import "../global.css";

import { Redirect, Stack, useSegments } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { useAuth } from "@clerk/clerk-expo";

import { AppProviders } from "../src/providers/AppProviders";

function RootNavigator() {
  const { isLoaded, isSignedIn } = useAuth();
  const segments = useSegments();

  if (!isLoaded) {
    return null;
  }

  const inAuthScreen = segments[0] === "sign-in";

  if (!isSignedIn && !inAuthScreen) {
    return <Redirect href="/sign-in" />;
  }

  if (isSignedIn && inAuthScreen) {
    return <Redirect href="/" />;
  }

  return (
    <>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: {
            backgroundColor: "#07111F",
          },
        }}
      />
    </>
  );
}

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <AppProviders>
        <RootNavigator />
      </AppProviders>
    </SafeAreaProvider>
  );
}