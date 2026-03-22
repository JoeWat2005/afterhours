import { useState } from "react";
import { Link, type Href, useRouter } from "expo-router";
import { Pressable, SafeAreaView, Text, TextInput, View } from "react-native";
import { useSignIn } from "@clerk/expo";

export default function SignInScreen() {
  const { signIn, errors, fetchStatus } = useSignIn();
  const router = useRouter();

  const [emailAddress, setEmailAddress] = useState("");
  const [password, setPassword] = useState("");

  const onSignIn = async () => {
    const { error } = await signIn.password({
      emailAddress,
      password,
    });

    if (error) {
      console.error(JSON.stringify(error, null, 2));
      return;
    }

    if (signIn.status === "complete") {
      await signIn.finalize({
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
    } else if (signIn.status === "needs_second_factor") {
      console.log("Second factor required");
    } else if (signIn.status === "needs_client_trust") {
      console.log("Client trust step required");
    } else {
      console.log("Unhandled sign-in status:", signIn.status);
    }
  };

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
          Sign in
        </Text>
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

        {!!errors?.fields?.identifier && (
          <Text style={{ color: "#fca5a5" }}>
            {errors.fields.identifier.message}
          </Text>
        )}

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

        {!!errors?.fields?.password && (
          <Text style={{ color: "#fca5a5" }}>
            {errors.fields.password.message}
          </Text>
        )}

        <Pressable
          onPress={onSignIn}
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
            {fetchStatus === "fetching" ? "Signing in..." : "Sign in"}
          </Text>
        </Pressable>

        {!!errors && (
          <Text style={{ color: "#94a3b8", fontSize: 12 }}>
            {JSON.stringify(errors, null, 2)}
          </Text>
        )}

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