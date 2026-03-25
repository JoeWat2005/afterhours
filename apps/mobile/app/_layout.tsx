import "../global.css";
import { ClerkProvider, useAuth } from '@clerk/expo';
import { tokenCache } from '@clerk/expo/token-cache';
import { Slot } from 'expo-router';
import { AuthView } from '@clerk/expo/native';
import { View, ActivityIndicator, LogBox } from 'react-native';
import { AppProviders } from '../src/providers/AppProviders';

if (__DEV__) {
  LogBox.ignoreLogs([
    "Codegen didn't run for ClerkAuthView",
    "Codegen didn't run for ClerkUserProfileView",
    "`new NativeEventEmitter()` was called with a non-null argument without the required `addListener` method.",
    "`new NativeEventEmitter()` was called with a non-null argument without the required `removeListeners` method.",
  ]);
}

const publishableKey = process.env.EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY!;

function RootNavigator() {
  const { isSignedIn, isLoaded } = useAuth();

  if (!isLoaded) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator />
      </View>
    );
  }

  if (!isSignedIn) {
    return <AuthView mode="signInOrUp" />;
  }

  return <Slot />;
}

export default function RootLayout() {
  return (
    <ClerkProvider publishableKey={publishableKey} tokenCache={tokenCache}>
      <AppProviders>
        <RootNavigator />
      </AppProviders>
    </ClerkProvider>
  );
}
