import { useState } from "react";
import { Link, type Href, useRouter } from "expo-router";
import { Pressable, SafeAreaView, Text, TextInput, View } from "react-native";
import { useAuth, useSignUp } from "@clerk/expo";

export default function SignUpScreen() {
  const { signUp, errors, fetchStatus } = useSignUp();
  const { isSignedIn } = useAuth();
  const router = useRouter();

  const [emailAddress, setEmailAddress] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");

  const onSignUp = async () => {
    const { error } = await signUp.password({
      emailAddress,
      password,
    });

    if (error) {
      console.error(JSON.stringify(error, null, 2));
      return;
    }

    await signUp.verifications.sendEmailCode();
  };

  const onVerify = async () => {
    await signUp.verifications.verifyEmailCode({ code });

    if (signUp.status === "complete") {
      await signUp.finalize({
        navigate: ({ session, decorateUrl }) => {
          if (session?.currentTask) {
            console.log(session.currentTask);
            return;
          }

          const url = decorateUrl("/");
          if (url.startsWith("http")) {
            window.location.href = url;
          } else {
            router.push(url as Href);
          }
        },
      });
    } else {
      console.error("Sign-up attempt not complete:", signUp.status);
    }
  };

  if (signUp.status === "complete" || isSignedIn) {
    return null;
  }

  const needsVerification =
    signUp.status === "missing_requirements" &&
    signUp.unverifiedFields.includes("email_address") &&
    signUp.missingFields.length === 0;

  return (
    <SafeAreaView
      style={{
        flex: 1,
        justifyContent: "center",
        padding: 24,
        backgroundColor: "#07111F",
      }}
    >
      <View style={{ gap: 12 }}>
        <Text style={{ fontSize: 28, fontWeight: "700", color: "white" }}>
          {needsVerification ? "Verify email" : "Create account"}
        </Text>

        {needsVerification ? (
          <>
            <Text style={{ color: "#cbd5e1" }}>
              Enter the verification code sent to your email.
            </Text>

            <TextInput
              value={code}
              onChangeText={setCode}
              placeholder="Enter your verification code"
              placeholderTextColor="#94a3b8"
              keyboardType="numeric"
              style={{
                borderWidth: 1,
                borderColor: "#334155",
                borderRadius: 12,
                padding: 12,
                color: "white",
                backgroundColor: "#0f172a",
              }}
            />

            {!!errors?.fields?.code && (
              <Text style={{ color: "#fca5a5" }}>
                {errors.fields.code.message}
              </Text>
            )}

            <Pressable
              onPress={onVerify}
              disabled={fetchStatus === "fetching" || !code}
              style={{
                borderRadius: 12,
                padding: 14,
                backgroundColor:
                  fetchStatus === "fetching" || !code ? "#155e75" : "#06b6d4",
                alignItems: "center",
                marginTop: 8,
              }}
            >
              <Text style={{ fontWeight: "700", color: "#082f49" }}>
                {fetchStatus === "fetching" ? "Verifying..." : "Verify email"}
              </Text>
            </Pressable>

            <Pressable
              onPress={() => signUp.verifications.sendEmailCode()}
              style={{
                borderRadius: 12,
                padding: 14,
                alignItems: "center",
                marginTop: 4,
              }}
            >
              <Text style={{ color: "#67e8f9", fontWeight: "700" }}>
                I need a new code
              </Text>
            </Pressable>
          </>
        ) : (
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
              onPress={onSignUp}
              disabled={!emailAddress || !password || fetchStatus === "fetching"}
              style={{
                borderRadius: 12,
                padding: 14,
                backgroundColor:
                  !emailAddress || !password || fetchStatus === "fetching"
                    ? "#155e75"
                    : "#06b6d4",
                alignItems: "center",
                marginTop: 8,
              }}
            >
              <Text style={{ fontWeight: "700", color: "#082f49" }}>
                {fetchStatus === "fetching" ? "Creating account..." : "Sign up"}
              </Text>
            </Pressable>

            <View style={{ flexDirection: "row", marginTop: 8 }}>
              <Text style={{ color: "#cbd5e1" }}>Already have an account? </Text>
              <Link href="/sign-in" style={{ color: "#67e8f9", fontWeight: "700" }}>
                Sign in
              </Link>
            </View>
          </>
        )}

        {!!errors && (
          <Text style={{ color: "#94a3b8", fontSize: 12 }}>
            {JSON.stringify(errors, null, 2)}
          </Text>
        )}

        <View nativeID="clerk-captcha" />
      </View>
    </SafeAreaView>
  );
}