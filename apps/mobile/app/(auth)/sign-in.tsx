import { useState } from "react";
import { Link, router } from "expo-router";
import { Pressable, SafeAreaView, Text, TextInput, View } from "react-native";
import { useSignIn } from "@clerk/expo";

export default function SignInScreen() {
  const { signIn, setActive, isLoaded } = useSignIn();
  const [emailAddress, setEmailAddress] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const onSignIn = async () => {
    if (!isLoaded) return;

    try {
      setSubmitting(true);
      setErrorMessage(null);

      const result = await signIn.create({
        identifier: emailAddress,
        password,
      });

      if (result.status === "complete") {
        await setActive({ session: result.createdSessionId });
        router.replace("/");
      } else {
        setErrorMessage("Sign-in is not complete yet.");
      }
    } catch (err: any) {
      setErrorMessage(err?.errors?.[0]?.message ?? "Unknown sign-in error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, justifyContent: "center", padding: 24, backgroundColor: "#07111F" }}>
      <View style={{ gap: 12 }}>
        <Text style={{ fontSize: 28, fontWeight: "700", color: "white" }}>Sign in</Text>
        <Text style={{ color: "#cbd5e1", marginBottom: 8 }}>
          Use your account to continue.
        </Text>

        <TextInput
          autoCapitalize="none"
          keyboardType="email-address"
          placeholder="Email"
          placeholderTextColor="#94a3b8"
          value={emailAddress}
          onChangeText={setEmailAddress}
          style={{
            borderWidth: 1,
            borderColor: "#334155",
            borderRadius: 12,
            padding: 12,
            color: "white",
            backgroundColor: "#0f172a",
          }}
        />

        <TextInput
          secureTextEntry
          placeholder="Password"
          placeholderTextColor="#94a3b8"
          value={password}
          onChangeText={setPassword}
          style={{
            borderWidth: 1,
            borderColor: "#334155",
            borderRadius: 12,
            padding: 12,
            color: "white",
            backgroundColor: "#0f172a",
          }}
        />

        {errorMessage ? (
          <Text style={{ color: "#fca5a5" }}>{errorMessage}</Text>
        ) : null}

        <Pressable
          onPress={onSignIn}
          disabled={submitting || !emailAddress || !password}
          style={{
            borderRadius: 12,
            padding: 14,
            backgroundColor: submitting || !emailAddress || !password ? "#155e75" : "#06b6d4",
            alignItems: "center",
            marginTop: 8,
          }}
        >
          <Text style={{ fontWeight: "700", color: "#082f49" }}>
            {submitting ? "Signing in..." : "Sign in"}
          </Text>
        </Pressable>

        <View style={{ flexDirection: "row", marginTop: 8 }}>
          <Text style={{ color: "#cbd5e1" }}>No account yet? </Text>
          <Link href="/sign-up" style={{ color: "#67e8f9", fontWeight: "700" }}>
            Sign up
          </Link>
        </View>
      </View>
    </SafeAreaView>
  );
}