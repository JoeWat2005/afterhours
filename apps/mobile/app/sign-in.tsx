import { useState } from "react";
import { Alert, Pressable, SafeAreaView, Text, TextInput, View } from "react-native";
import { useSignIn } from "@clerk/clerk-expo";
import { router } from "expo-router";

export default function SignInScreen() {
  const { signIn, setActive, isLoaded } = useSignIn();
  const [emailAddress, setEmailAddress] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const onSignIn = async () => {
    if (!isLoaded) return;

    try {
      setSubmitting(true);

      const result = await signIn.create({
        identifier: emailAddress,
        password,
      });

      if (result.status === "complete") {
        await setActive({ session: result.createdSessionId });
        router.replace("/");
      } else {
        Alert.alert("Sign-in incomplete", JSON.stringify(result, null, 2));
      }
    } catch (err: any) {
      Alert.alert("Sign-in failed", err?.errors?.[0]?.message ?? "Unknown error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, justifyContent: "center", padding: 24 }}>
      <View style={{ gap: 12 }}>
        <Text style={{ fontSize: 28, fontWeight: "700" }}>Sign in</Text>

        <TextInput
          autoCapitalize="none"
          keyboardType="email-address"
          placeholder="Email"
          value={emailAddress}
          onChangeText={setEmailAddress}
          style={{ borderWidth: 1, borderRadius: 12, padding: 12 }}
        />

        <TextInput
          secureTextEntry
          placeholder="Password"
          value={password}
          onChangeText={setPassword}
          style={{ borderWidth: 1, borderRadius: 12, padding: 12 }}
        />

        <Pressable
          onPress={onSignIn}
          style={{
            borderRadius: 12,
            padding: 14,
            backgroundColor: "#06b6d4",
            alignItems: "center",
          }}
        >
          <Text style={{ fontWeight: "700" }}>
            {submitting ? "Signing in..." : "Sign in"}
          </Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}