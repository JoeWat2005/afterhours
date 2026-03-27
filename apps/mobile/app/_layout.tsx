import "../global.css";
import { useState } from "react";
import { ClerkProvider, useAuth, useSignIn } from "@clerk/expo";
import { tokenCache } from "@clerk/expo/token-cache";
import { Slot, useRouter } from "expo-router";
import { View, Text, TextInput, Pressable, ActivityIndicator, LogBox } from "react-native";
import { AppProviders } from "../src/providers/AppProviders";
import { DemoModeProvider, useDemoMode } from "../src/lib/demoMode";

if (__DEV__) {
  LogBox.ignoreLogs([
    "`new NativeEventEmitter()` was called with a non-null argument without the required `addListener` method.",
    "`new NativeEventEmitter()` was called with a non-null argument without the required `removeListeners` method.",
    "Missing bearer token",
    "Missing Clerk",
    "Clerk:",
  ]);
}

const publishableKey = process.env.EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY!;

function SignInScreen() {
  const { signIn } = useSignIn();
  const router = useRouter();
  const { enableDemo } = useDemoMode();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSignIn() {
    if (!signIn) return;
    if (!email || !password) {
      setError("Please fill in both fields");
      return;
    }
    setLoading(true);
    setError("");

    try {
      await signIn.password({ emailAddress: email, password });

      if (signIn.status === "complete") {
        await signIn.finalize({
          navigate: ({ decorateUrl }: any) => {
            router.replace(decorateUrl("/"));
          },
        });
      } else {
        setError("Something went wrong, please try again");
      }
    } catch (err: any) {
      setError(err?.errors?.[0]?.longMessage || err?.message || "Sign in failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <View className="flex-1 justify-center px-6 bg-white">
      <Text className="text-3xl font-bold text-center mb-1">AfterHours</Text>
      <Text className="text-sm text-slate-500 text-center mb-8">Sign in to continue</Text>

      <TextInput
        className="border border-slate-200 rounded-lg p-3.5 text-base mb-3 bg-slate-50"
        placeholder="Email"
        placeholderTextColor="#94a3b8"
        autoCapitalize="none"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        className="border border-slate-200 rounded-lg p-3.5 text-base mb-3 bg-slate-50"
        placeholder="Password"
        placeholderTextColor="#94a3b8"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />

      {error ? <Text className="text-red-600 text-xs mb-2">{error}</Text> : null}

      <Pressable
        onPress={handleSignIn}
        disabled={loading}
        className={`rounded-lg py-3.5 items-center mt-2 ${loading ? "bg-slate-400" : "bg-slate-900"}`}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text className="text-white font-semibold text-base">Sign in</Text>
        )}
      </Pressable>

      <Pressable
        onPress={enableDemo}
        className="rounded-lg py-3.5 items-center mt-3 border border-slate-200"
      >
        <Text className="text-slate-600 font-semibold text-base">Try demo</Text>
      </Pressable>
      <Text className="text-slate-400 text-[10px] text-center mt-2">
        Skip sign in and explore with limited features
      </Text>
    </View>
  );
}

function RootNavigator() {
  const { demoMode } = useDemoMode();
  const { isSignedIn, isLoaded } = useAuth();

  if (!isLoaded) {
    return (
      <View className="flex-1 justify-center items-center">
        <ActivityIndicator />
      </View>
    );
  }

  if (!isSignedIn && !demoMode) {
    return <SignInScreen />;
  }

  return <Slot />;
}

export default function RootLayout() {
  return (
    <ClerkProvider publishableKey={publishableKey} tokenCache={tokenCache}>
      <DemoModeProvider>
        <AppProviders>
          <RootNavigator />
        </AppProviders>
      </DemoModeProvider>
    </ClerkProvider>
  );
}
