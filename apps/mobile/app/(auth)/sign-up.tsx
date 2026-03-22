import { useState } from "react";
import { Link, router } from "expo-router";
import { Pressable, SafeAreaView, Text, TextInput, View } from "react-native";
import { useSignUp } from "@clerk/expo";

export default function SignUpScreen() {
  const { isLoaded, signUp, setActive } = useSignUp();
  const [emailAddress, setEmailAddress] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [pendingVerification, setPendingVerification] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const onSignUpPress = async () => {
    if (!isLoaded) return;

    try {
      setSubmitting(true);
      setErrorMessage(null);

      await signUp.create({
        emailAddress,
        password,
      });

      await signUp.prepareEmailAddressVerification({ strategy: "email_code" });
      setPendingVerification(true);
    } catch (err: any) {
      setErrorMessage(err?.errors?.[0]?.message ?? "Unknown sign-up error");
    } finally {
      setSubmitting(false);
    }
  };

  const onVerifyPress = async () => {
    if (!isLoaded) return;

    try {
      setSubmitting(true);
      setErrorMessage(null);

      const completeSignUp = await signUp.attemptEmailAddressVerification({
        code,
      });

      if (completeSignUp.status === "complete") {
        await setActive({ session: completeSignUp.createdSessionId });
        router.replace("/");
      } else {
        setErrorMessage("Verification is not complete yet.");
      }
    } catch (err: any) {
      setErrorMessage(err?.errors?.[0]?.message ?? "Verification failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, justifyContent: "center", padding: 24, backgroundColor: "#07111F" }}>
      <View style={{ gap: 12 }}>
        <Text style={{ fontSize: 28, fontWeight: "700", color: "white" }}>
          {pendingVerification ? "Verify email" : "Create account"}
        </Text>

        {!pendingVerification ? (
          <>
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

            <Pressable
              onPress={onSignUpPress}
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
                {submitting ? "Creating account..." : "Sign up"}
              </Text>
            </Pressable>

            <View style={{ flexDirection: "row", marginTop: 8 }}>
              <Text style={{ color: "#cbd5e1" }}>Already have an account? </Text>
              <Link href="/sign-in" style={{ color: "#67e8f9", fontWeight: "700" }}>
                Sign in
              </Link>
            </View>
          </>
        ) : (
          <>
            <Text style={{ color: "#cbd5e1" }}>
              Enter the verification code sent to your email.
            </Text>

            <TextInput
              placeholder="Verification code"
              placeholderTextColor="#94a3b8"
              value={code}
              onChangeText={setCode}
              style={{
                borderWidth: 1,
                borderColor: "#334155",
                borderRadius: 12,
                padding: 12,
                color: "white",
                backgroundColor: "#0f172a",
              }}
            />

            <Pressable
              onPress={onVerifyPress}
              disabled={submitting || !code}
              style={{
                borderRadius: 12,
                padding: 14,
                backgroundColor: submitting || !code ? "#155e75" : "#06b6d4",
                alignItems: "center",
                marginTop: 8,
              }}
            >
              <Text style={{ fontWeight: "700", color: "#082f49" }}>
                {submitting ? "Verifying..." : "Verify email"}
              </Text>
            </Pressable>
          </>
        )}

        {errorMessage ? (
          <Text style={{ color: "#fca5a5" }}>{errorMessage}</Text>
        ) : null}
      </View>
    </SafeAreaView>
  );
}